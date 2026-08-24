# /daily — Autonomous daily scan-and-disclose pipeline

Runs the full AI PatchLab public-scan workflow end-to-end, once per day, without requiring the user to drive it. This is the automation the user explicitly opted into on 2026-05-28 ("full auto, publication incluse"), tempered by the guardrails below so it never degrades into the "looks like a bot / advertising" failure mode (the dstack #3908 rejection lesson).

## Argument
`$ARGUMENTS` — Optional mode flag:
- (default) — **autonomous**: run every phase including public actions (issues, PRs, posts).
- `--dry-run` — do everything EXCEPT irreversible public actions; write the post + dossier locally, print what *would* be filed, file nothing, push nothing.
- `--status-only` — run Phase 1 (status sweep + resolution updates) and stop. No new scan.

## Non-negotiable guardrails (apply in every phase)
1. **One scan per day.** If a scan already ran today (see state file), skip Phase 2-5 and do status-only.
2. **Quality gate on filing.** Always publish the write-up post. Only file a courtesy issue / open a fix PR when curation found ≥1 *real, exploitability-shaped, high-confidence* item. Otherwise the post stands alone as a clean-scan write-up (an honest, established format — 3 already exist in the series).
3. **Strict-norm repo detection.** If the target has a real SECURITY.md (beyond GitHub's default), commercial backing, or a visible security team → post-only, or one-vuln-per-issue. Never a grouped "review" issue.
4. **De-branded issue text.** No "scanned by [tool]" header. A single public-write-up link in a footer line at most. Lead with the finding and where the affected API is actually called in the repo.
5. **Never rescan.** Dedup every candidate against existing slugs in `docs/scans/`.
6. **Manual-disclosure backlog is a blocking warning.** Count the `pending_private_disclosure*` entries in the state file. If any has been pending **more than 7 days**, print a loud banner at the top of the run naming each one (repo, severity, days waiting) before doing anything else. If any is **High or Critical and pending more than 14 days**, do not start a new scan — run status-only and tell the user the queue needs clearing first. Rationale: on 2026-08-21 six reports were found sitting unsent, the oldest 22 days, including an unauthenticated-admin finding. Nothing in the pipeline had surfaced them, because every phase only looked forward at the next scan. A report that is written but never sent is worse than one never written: the maintainer does not know, and the series has already published that something was found.
7. **Always the venv interpreter, never bare `python`.** The project ran three months off the shared user-site and an unrelated `pip install` downgraded pydantic to 1.x, after which `import scanner` raised ImportError. A bare `python` here silently scans with a broken interpreter or not at all.
8. **Kill switch.** If `.daily-paused` exists in the repo root, abort immediately with a one-line note. (Create/remove it to pause/resume without code changes.)

## State & rate-limit
- State file: `reports/.daily_state.json` (under gitignored `reports/`).
- Scalar keys: `last_run` (`YYYY-MM-DD`), `last_slug`, `scans_count`, `clean_scans_count`, `resolved_count`, `acknowledged_count`, `filed_open_count`.
- Run history lives in **`runs_recent`** (a rolling list of the last ~15 runs). The `runs` key is a vestigial empty list from an earlier shape — read `runs_recent`, and do not start writing to `runs` again.
- Ad-hoc keys follow four families; a new entry must join one rather than invent a fifth:
  - `pending_private_disclosure*` — a report drafted but not yet delivered (**this is what guardrail 6 counts**)
  - `withheld_finding_*` — filed privately, detail withheld from the public post
  - `excluded_repos` / `excluded_note` — targets deliberately never to be scanned again
  - `*_note` — a durable lesson worth carrying into later runs
- At start: read it. If `last_run == today`, treat as rate-limited → `--status-only` behavior.
- At end of a successful scan: write `last_run = today`, append the slug to `runs_recent`.
- Drafted disclosure emails live in `reports/disclosures/` (gitignored). When one is sent, replace its `pending_private_disclosure*` entry with a `sent` record carrying the date and channel, so the backlog count drops and Phase 1 starts polling it.

---

## Phase 0 — Preconditions
1. If `.daily-paused` exists → print `daily: paused (.daily-paused present)` and STOP.
2. **Interpreter preflight.** Run `.venv/Scripts/python.exe -c "import scanner.run_scan"`. If it fails, STOP and report it — do not fall back to bare `python`, and do not scan. A broken interpreter must abort the run, not silently produce an empty report.
3. Read `reports/.daily_state.json` (create with empty defaults if missing).
4. Compute `today` (local date). If `last_run == today` and mode is not `--status-only`, downgrade to status-only and note it.

## Phase 1 — Status sweep (always runs)
1. `gh search prs --author=elfrost --json repository,number,title,state,url,updatedAt` and `gh search issues --author=elfrost --json repository,number,title,state,url,updatedAt` (filter out `elfrost/ai-patchlab`).
2. For each open disclosure updated since `last_run`: read its latest comments (`gh issue view`/`gh pr view --json comments,reviews`).
3. Act on movement:
   - **Maintainer asks for a PR** → open the fix PR (fork → branch → single-purpose change → PR referencing the issue). Commit author MUST be `5491654+elfrost@users.noreply.github.com`.
   - **Issue/PR merged or closed-as-fixed** → update `docs/scans/<slug>.md` (add a resolution line to the disclosure timeline) and the matching `docs/index.md` line (✅ badge). Update memory `project_first_resolved_disclosure.md`.
   - **Maintainer pushback / rejection** → keep the honest record: add the quoted response to the post, ❌/note badge on index. Do NOT delete the post.
   - **No actionable movement** → no-op.
4. Commit any doc/badge updates on ai-patchlab (`docs:` commit) — but only push after the convention check: **update a scan post's outcome only once the upstream PR/issue is actually merged/closed, never merely opened.**

If mode is `--status-only`, STOP here after pushing doc updates.

## Phase 2 — Candidate discovery + pre-check
1. `gh search repos --language=python --stars=1500..6000 --sort=updated --json fullName,stargazersCount,description,pushedAt,license,url` and filter descriptions matching the AI/agent/LLM/RAG/inference space.
2. Drop any repo whose slug already exists in `docs/scans/` (`<owner>-<name>.md`).
3. Responsiveness pre-check on the top few: recent *closed* issues + *merged* PRs from ≥2 distinct contributors in the last ~60 days → signals a maintainer who answers. Skip ghost repos.
4. Strict-norm detection: check for `SECURITY.md`, commercial backing in README, named security reviewers. Record the publication mode this implies.
5. Pick exactly ONE best candidate. Record why (stars, activity, focus, norm mode).

## Phase 3 — Scan
```bash
.venv/Scripts/python.exe scanner/run_scan.py --from-git-url "<url>" --reports-dir reports/<slug> --min-severity medium
```
Use `--ignore-file` if the repo has obvious sample/example/demo subtrees (until those are shipped as defaults).

## Phase 4 — Curate
1. Group findings by rule family. Auto-flag `tests/`, `sample/`, `examples/`, `demos/`, fixtures, placeholders as candidate-FP.
2. Inspect the top 5 real candidates in the actual repo via `gh api repos/<owner>/<name>/contents/<path>` — read the call site, confirm the threat path.
3. Write per-finding verdicts (real / by-design / FP, with the *why*).
4. **Evaluate the quality gate:** is there ≥1 real, exploitability-shaped, high-confidence item? Record the boolean — it decides Phase 5 filing.

## Phase 5 — Publish (gated)
1. **Always:** write `docs/scans/<slug>.md` from `docs/templates/scan-post.md`; prepend a new line to the Scans list in `docs/index.md`.
2. **If quality gate TRUE and repo not strict-norm:** file a focused courtesy issue on the target (de-branded, with code-path note + concrete fix). If a finding has a clean one-line/one-file fix, also fork → branch → PR referencing the issue.
3. **If repo strict-norm:** post-only, or one issue per critical finding — no grouped issue.
4. **If quality gate FALSE:** post-only (clean-scan write-up). File nothing upstream.
5. Open the `docs:` PR on `elfrost/ai-patchlab`, merge it, verify the Pages build succeeds (`gh api repos/elfrost/ai-patchlab/pages/builds/latest --jq .status` → `built`) and the new post returns HTTP 200.

## Phase 6 — Record
1. Update `reports/.daily_state.json` (`last_run`, append slug).
2. Update memory if a disclosure resolved or a new methodology lesson emerged.
3. Print a 3-line summary: what was swept, what was scanned, what was filed (or why not).

## Rules
- NEVER rescan a repo already in `docs/scans/`.
- NEVER file an issue/PR when the quality gate is false — post-only instead.
- NEVER skip the strict-norm check before filing a grouped issue.
- ALWAYS use the noreply commit email; NEVER expose a personal email.
- ALWAYS keep an honest record of rejections (document, don't delete).
- In `--dry-run`, take ZERO irreversible public actions.
- Respect the convention: a scan post's *outcome* is updated only after the upstream PR/issue is merged/closed, not when opened.
