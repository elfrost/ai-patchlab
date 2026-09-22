Ship a finalized PRP end-to-end — autonomous post-architecture autopilot: $ARGUMENTS

`/ship` automates the painful segment AFTER the architecture is locked:
**implement → verify → retrospective → push/PR**. You no longer approve each
step — phases 1-3 run unattended, with a SINGLE human gate just before push.

## When to use

Run `/ship` once `/kickoff` → `/generate-prp` → architect review are done and
the architect confirmed "go". `/ship` takes the approved PRP from there.

- `$ARGUMENTS` = path to the PRP file (e.g. `PRPs/my-feature.md`)
- `$ARGUMENTS` = `last` or empty → use the most recent `PRPs/*.md` (excluding `PRPs/done/`)

This is the post-PRP counterpart to `/idea-to-pr` (which starts from a raw idea).

## Core principle — fresh context per phase

You (this conversation) are the **orchestrator**. You do NOT write feature code,
verify, or retrospect yourself. You spawn a **separate sub-agent per phase** via
the Agent tool. Each sub-agent gets a clean context window, so the "never review
the implementer's work in the same context that produced it" rule
(`AGENTS.md` → Self-Healing Layer) holds automatically — the verifier and the
retrospective agent never see the implementer's reasoning, only the artifacts
(git diff, files, PRP).

## Autonomy contract

- Phases 0-3 are **AUTONOMOUS**. Sub-agents apply fixes and commit **locally**
  without asking. Do NOT pause between phases. Do NOT ask "should I commit" —
  local commits are part of the contract.
- The **only** interactive gate is Phase 4, just before `git push` / PR creation
  (outward-facing, hard to reverse).
- If any phase **hard-fails**, STOP at that phase and surface it — never push
  broken work.

---

## Phase 0 — Branch guard

1. Resolve the target PRP from `$ARGUMENTS` (see "When to use").
   - If no PRP file is found, STOP and tell the user to run `/generate-prp` first.
2. Check the current branch. If it is `main` or `master`, create and check out a
   feature branch: `feat/<prp-slug>` (slug = PRP filename without extension).
   Never run the phases on the default branch (`AGENTS.md` → Git Workflow).
3. Record the base commit: `git rev-parse HEAD` → call it `BASE`. Used for diffs
   and the final summary.

## Phase 1 — Implement (fresh sub-agent)

Spawn a `general-purpose` sub-agent (opus — this is thinking + coding work):

> Read `.claude/commands/execute-prp.md` and follow it EXACTLY for the PRP file
> `<resolved path>`. Autonomous mode: implement every task, run the full
> validation loop (ruff / black / pytest), do the complete housekeeping section,
> and commit locally after each major task. Do NOT ask for any confirmation.
> Do NOT run a retrospective. End with the handoff summary.

Capture the handoff message. If the sub-agent reports that validation cannot
pass after its retries → **STOP**, surface the failure, do not continue.

## Phase 2 — Verify (fresh sub-agent)

Spawn a **NEW** `general-purpose` sub-agent (opus) — clean context, it must not
see Phase 1's reasoning:

> Fresh-context verification of the feature just implemented on this branch.
> Inspect `git diff <BASE>..HEAD`. Verify the change actually does what the PRP
> asked: run the app and/or `pytest`, exercise the new behavior, and OBSERVE the
> result — do not assume it works. If you find a defect: fix it, re-verify, and
> commit locally with a `fix:` message. Autonomous — do NOT ask for confirmation.
> Report: PASS or FAIL, what you observed, and what you fixed (if anything).

If the sub-agent reports FAIL and cannot fix it → **STOP**, surface it.

## Phase 2.5 — Cross-model adversarial review (Codex, optional, autonomous)

Cross-model review beats same-model fresh context: Codex has different training
blind spots than Claude, so it catches what a fresh Claude context would miss.
This phase is **optional and non-blocking** — it runs only if the Codex CLI is
installed (same graceful-degradation contract as ADR-019 / AgentShield).

1. Detect Codex: run `codex --version`. If it fails (not on PATH), SKIP this
   phase, note "Codex review skipped (CLI not found)", and continue — never fail.
2. Pick the auth home. If `~/.codex-api/` exists, the review runs on the **API
   key** (metered, ~$0.20/review). Otherwise it falls back to the personal
   ChatGPT subscription — allowed, but say so **loudly** in the Phase 4 summary
   so the fallback is never silent. Set up the API home with
   `ez-codex-api-setup.ps1 -ApiKey "sk-proj-..."` (ADR-026).
3. Run the review. **Never pass a custom prompt** — `codex exec review` rejects
   `--base`/`--commit`/`--uncommitted` combined with a `[PROMPT]` argument
   (`exit 2`). Project-specific focus reaches the reviewer through `AGENTS.md`,
   which it reads on its own.
   ```powershell
   cmd /c "git status --porcelain=v1 --ignored --untracked-files=all 2>&1"   # baseline for step 4: keep this output in your context
   $env:CODEX_HOME = "$HOME\.codex-api"   # omit this line to use the subscription
   cmd /c "codex exec review --base <default-branch> -m gpt-5.6-terra -o codex-review.txt 2>&1" | Out-File codex-review.log
   ```
   `cmd` owns the redirect on purpose: Codex writes to stderr, and a bare `2>&1`
   under PS 5.1 wraps every line in an ErrorRecord and fails the step on exit 0.
4. **Verify the review actually saw the diff before trusting it.** A sandbox that
   blocks command execution makes Codex return
   `No actionable findings identified` with **exit 0** — a clean bill of health
   from a reviewer that read nothing. The review is valid only if the log shows
   an `exec` block whose command runs `git diff`, followed by its ` succeeded in`
   line. Never judge by grepping an error string (`blocked by policy`,
   `error=exec_command failed`): any diff or file the reviewer reads can quote it —
   this very step does.
   ```powershell
   $log = @(Get-Content codex-review.log -Encoding UTF8); $sawDiff = $false
   for ($i = 0; $i -lt $log.Count; $i++) {
     if ($log[$i] -ne 'exec') { continue }
     $j = $i + 1   # the command may span several lines; its status line ends the block
     while ($j -lt $log.Count -and $j -le $i + 200 -and $log[$j] -ne 'exec' -and
            $log[$j] -notmatch '^ (succeeded in|exited -?\d+ in) ') { $j++ }
     if ($j -gt $i + 1 -and $j -lt $log.Count -and $log[$j] -match '^ succeeded in ' -and
         ($log[($i + 1)..($j - 1)] -match '\bgit\b.*\bdiff\b')) { $sawDiff = $true; break }
   }
   ```
   If `$sawDiff` is false, the review is INVALID: treat it as skipped, note
   "Codex review invalid — sandbox blocked execution (run ez-codex-api-setup.ps1)",
   and never report it as a pass.
   Then check the tree — a review is read-only (the **Reviewer conduct** rule of
   AGENTS.md). Run the same `git status` command as the step 3 baseline and compare
   the two outputs. In the Phase 4 summary, report every new entry other than
   `codex-review.txt` / `codex-review.log`, and every `could not open directory`
   warning: an unreadable folder is how a sandbox-owned leftover shows up, with no
   porcelain line of its own. **Change nothing**: do not delete, restore or re-own
   any path, and do not elevate — a new path may be the user's (an OneDrive conflict
   copy, say), and a sandbox-owned one needs an elevated clean-up that the user runs
   by hand after checking it holds no links.
5. Capture Codex's findings from `codex-review.txt`, and the token usage from the
   last `token_count` event in the newest
   `$CODEX_HOME/sessions/**/rollout-*.jsonl` — `--json`'s `turn.completed.usage`
   reports zeros and cannot be used for the cost line.
6. Spawn a **NEW** `general-purpose` sub-agent (opus, fresh context) to TRIAGE —
   Codex's one-shot review lacks repo context, so Claude is the arbiter:
   > Adversarial review findings from Codex (a different model) on this branch:
   > <Codex output>. For each finding, inspect the code and confirm whether it is
   > real. Fix every confirmed defect, re-verify, and commit locally with a `fix:`
   > message. List false positives you dismissed and why. Autonomous — do NOT ask
   > for confirmation. Report: confirmed / fixed / dismissed.
7. If the triage agent confirms a defect it cannot fix → **STOP**, surface it.

Codex findings are advisory input, not gospel — the Claude triage agent decides.

## Phase 3 — Retrospective (fresh sub-agent)

Spawn a **NEW** `general-purpose` sub-agent — clean context:

> Read `.claude/commands/retrospective.md` and follow it with the argument
> `last`. Produce the proposed AI-layer changes (AGENTS.md / CLAUDE.md /
> .claude/rules / examples / skills / agents). **PROPOSE ONLY — do NOT apply or
> edit any file.** Return the full proposal verbatim.

Capture the proposal. The AI layer is never edited unattended — applying it is
part of the Phase 4 gate.

## Phase 4 — THE GATE, then ship

Present ONE consolidated summary to the user:

```
🚢 /ship — <prp-slug>  (branch: <branch>)

✅ Implemented   — <Phase 1 handoff, condensed>
✅ Verified      — <Phase 2 PASS + key observations>
🤖 Codex review  — <Phase 2.5 confirmed/fixed/dismissed, or "skipped — CLI not found">
🔧 Retrospective — <Phase 3 proposal, or "clean — no AI-layer changes">

Commits on <branch> (not yet pushed):
<git log --oneline BASE..HEAD>
```

Then ask via **AskUserQuestion** — the single gate of the whole flow:

- **Ship + apply retro** — apply exactly the AI-layer edits the proposal listed,
  commit them as `chore: AI-layer improvements from /ship retrospective`, then
  push and open the PR.
- **Ship only** — skip the retro changes, push and open the PR.
- **Hold** — do nothing; leave all commits local. Stop here.

On either Ship choice:

1. (If "apply retro") make the proposed edits, then commit them.
2. `git push -u origin <branch>`
3. `gh pr create --fill` — title/body derived from the PRP. If `gh` is missing or
   there is no remote, report that the branch is pushed (or still local) and stop
   gracefully — do not fail the whole run.
4. Output the final summary with the PR URL (or branch name if no PR).

---

## Rules

- NEVER write feature code, verify, or retrospect in the orchestrator context —
  always delegate to a sub-agent.
- Each phase = a **separate** Agent invocation = a fresh context. Never reuse a
  sub-agent across phases.
- Phases 0-3 never pause for the user. One gate only (Phase 4).
- If a phase hard-fails, STOP there and surface it — do not push broken work.
- Never operate on `main` / `master` — Phase 0 guarantees a feature branch.
- The retrospective output is propose-only; it is applied only if the user picks
  "Ship + apply retro" at the gate.
- Codex/OpenAI: the `/ship` orchestrator itself is Claude-only — it depends on
  the sub-agent fresh-context primitive, so there is no Codex skill mirror (see
  `AGENTS.md`). But Phase 2.5 *uses* Codex as a cross-model adversarial reviewer
  when the `codex` CLI is present (graceful skip otherwise). This is the
  builder/reviewer split of the Dual-AI doctrine in `AGENTS.md` (ADR-021).
