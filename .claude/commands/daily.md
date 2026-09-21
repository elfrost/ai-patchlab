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
6. **Manual-disclosure backlog is a blocking warning.** Count the `pending_private_disclosure*` entries in the state file. If any has been pending **more than 7 days**, print a loud banner at the top of the run naming each one (repo, severity, days waiting) before doing anything else. If any is **High or Critical and pending more than 14 days**, do not start a new scan — run status-only and tell the user the queue needs clearing first. Rationale: on 2026-08-21 six reports were found sitting unsent, the oldest 22 days, including an unauthenticated-admin finding. Nothing in the pipeline had surfaced them, because every phase only looked forward at the next scan. A report that is written but never sent is worse than one never written: the maintainer does not know, and the series has already published that something was found. **If the report genuinely cannot be delivered by any channel, do not sit on the block — apply guardrail 8 (`unreachable`) instead of losing a scan every day.**
7. **Always the venv interpreter, never bare `python`.** The project ran three months off the shared user-site and an unrelated `pip install` downgraded pydantic to 1.x, after which `import scanner` raised ImportError. A bare `python` here silently scans with a broken interpreter or not at all.
8. **`unreachable` is the only way to clear an undeliverable report.** A `pending_private_disclosure*`
   entry may be closed WITHOUT delivery only when every channel is provably absent. All four pieces of
   evidence are required, and all four go in the state entry:
   - `gh api repos/{o}/{r}/private-vulnerability-reporting` → `{"enabled":false}`, checked on **two
     separate days** (a maintainer may switch it on after a nudge);
   - no email in `SECURITY.md` (root, `.github/`, `docs/`, published docs site), `README`,
     `FUNDING.yml`, the maintainer's profile, or the org profile — commit `noreply` aliases do not count;
   - a public issue is forbidden by the project's own SECURITY.md, **or** would itself disclose the finding;
   - any remaining contact sits on a platform the operator does not use, **and the operator has said so**.
     Never assume this — ask, and record the answer.

   Then re-key the entry to `unreachable_disclosure_<slug>` (guardrail 6 stops counting it) and add one
   honest line to the public post: *"Reported channel unavailable — the maintainer's stated private
   channel is disabled and no other private contact could be found. Detail remains withheld."*

   **Keep the detail withheld.** Do not publish a High with no fix and no maintainer aware of it; that
   serves attackers before users. `unreachable` records a failed delivery, it is not a licence to
   disclose. If a channel opens later, re-key it back and send.

9. **Kill switch.** If `.daily-paused` exists in the repo root, abort immediately with a one-line note. (Create/remove it to pause/resume without code changes.)

## State & rate-limit
- State file: `reports/.daily_state.json` (under gitignored `reports/`).
- Scalar keys: `last_run` (`YYYY-MM-DD`), `last_slug`, `scans_count`, `clean_scans_count`, `resolved_count`, `acknowledged_count`, `filed_open_count`.
- Run history lives in **`runs_recent`** (a rolling list of the last ~15 runs). The `runs` key is a vestigial empty list from an earlier shape — read `runs_recent`, and do not start writing to `runs` again.
- Ad-hoc keys follow four families; a new entry must join one rather than invent a fifth:
  - `pending_private_disclosure*` — a report drafted but not yet delivered (**this is what guardrail 6 counts**). **A post published with its finding withheld while the private send is still pending is THIS family, even if no email/channel is reachable yet — key it `pending_private_disclosure_*`, never `withheld_finding_*`.** On 2026-09-16 a 31-day-old undelivered High (liaohch3/claude-tap) was found mis-filed under `withheld_finding_*` and had silently evaded this banner for ~20 runs. If a channel is genuinely user-only (no PVR, no email — e.g. Twitter-DM-only), it is still pending; stage the most actionable artifact you can (a paste-ready DM in `reports/disclosures/`) and surface it, and remember there is no Gmail-Sent evidence source for a DM, so ask the user whether they've already reached out rather than assuming.
  - `withheld_finding_*` — a report **already delivered privately** (e.g. via GHSA/PVR), detail withheld from the public post. NOT for a report still awaiting its first delivery — that is `pending_private_disclosure_*` above.
  - `excluded_repos` / `excluded_note` — targets deliberately never to be scanned again
  - `*_note` — a durable lesson worth carrying into later runs
- At start: read it. If `last_run == today`, treat as rate-limited → `--status-only` behavior.
- At end of a successful scan: write `last_run = today`, append the slug to `runs_recent`.
- Drafted disclosure emails live in `reports/disclosures/` (gitignored). When one is sent, replace its `pending_private_disclosure*` entry with a `sent` record carrying the date and channel, so the backlog count drops and Phase 1 starts polling it.

---

## Phase 0 — Preconditions
1. If `.daily-paused` exists → print `daily: paused (.daily-paused present)` and STOP.
2. **Interpreter preflight.** Run `.venv/Scripts/python.exe -c "import scanner.run_scan"`. If it fails, STOP and report it — do not fall back to bare `python`, and do not scan. A broken interpreter must abort the run, not silently produce an empty report.
3. **Tool preflight.** Run `semgrep --version`, `gitleaks version` and `trivy --version`. Any tool that cannot report a version WILL produce an empty raw report that reads as "no findings" — name it in the run summary and in the published post, and treat the scan as partial coverage. **Semgrep is a Python program installed on the user-site interpreter**, so it breaks whenever that interpreter does, independently of this project's venv (2026-08-20 to 2026-08-24: a pydantic downgrade killed semgrep — 52% of the series' historical output — and nothing surfaced it because no scan ran in that window).
4. Read `reports/.daily_state.json` (create with empty defaults if missing).
5. Compute `today` (local date). If `last_run == today` and mode is not `--status-only`, downgrade to status-only and note it.

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
5. **Channel-viability pre-check — adaptive.** Before committing to a candidate, resolve how a
   finding would actually reach the maintainer, and weigh that against the current manual queue
   depth (count the `pending_private_disclosure*` entries in the state file):

   ```
   gh api repos/{owner}/{repo}/private-vulnerability-reporting --jq .enabled
   ```

   plus an email in `SECURITY.md` (root, `.github/`, `docs/`, published docs site), `README`,
   `FUNDING.yml`, the maintainer's profile, or the org profile. Commit `noreply` aliases do not count.

   | Manual queue depth | Rule |
   |---|---|
   | 0–2 | Any channel is acceptable, including email-only. |
   | 3 or more | **Require an autonomous channel** — PVR enabled, or a finding that can honestly go in a public issue. Skip email-only candidates and record why in the run summary. |
   | any | **Never pick a candidate with no channel at all** — PVR disabled *and* no email anywhere *and* a SECURITY.md forbidding public issues. That exact combination produced the only permanent deadlock in the series. |

   *Measured 2026-09-18:* 14 disclosures went through an autonomous channel, 12 needed a human send.
   **Every pipeline stoppage came from the human-gated half** — the six-report backlog (25 days, 4
   scans lost) and claude-tap (33 days, 3 scans lost). The autonomous half has never stopped a run.
   This is a structural mismatch, not bad luck: roughly half of all targets land on a channel the
   pipeline cannot use, and they accumulate until one crosses guardrail 6.

   **The preference is adaptive on purpose, never absolute.** PVR-enabled repos skew mature and
   commercially backed; a permanent preference would bias the series toward that profile and quietly
   drop the small projects that most need the review. When the queue is clear, a PVR-off project is a
   fair target — that is precisely what the tiering protects.

6. Pick exactly ONE best candidate. Record why (stars, activity, focus, norm mode, channel).

## Phase 3 — Scan
```bash
.venv/Scripts/python.exe scanner/run_scan.py --from-git-url "<url>" --reports-dir reports/<slug> --min-severity medium
```
Use `--ignore-file` if the repo has obvious sample/example/demo subtrees (until those are shipped as defaults).

Then read `reports/<slug>/coverage.json`. It is the authoritative record of what the scan examined, written on every run from the scanners' own meta findings and derived **before** `--ignore-file` suppression, so no pattern can hide it. If `complete` is `false`, the finding count is not a clean bill of health: carry the rows verbatim into the post's **Scan coverage** section and say in one sentence what was not examined. This replaces transcribing the Phase 1 preflight by hand — the preflight still runs, because catching a broken Semgrep *before* burning a scan is worth more than reporting it afterwards.

## Phase 4 — Curate
1. Group findings by rule family. Auto-flag `tests/`, `sample/`, `examples/`, `demos/`, fixtures, placeholders as candidate-FP.
2. Inspect the top 5 real candidates in the actual repo via `gh api repos/<owner>/<name>/contents/<path>` — read the call site, confirm the threat path.
3. Write per-finding verdicts (real / by-design / FP, with the *why*), then **append them to `reports/<slug>/verdicts.json`** as `source: "curation"` rows — one row per rule family with its count, not one per finding. The scanner has already written its own deterministic rows there (what `--ignore-file` and `--min-severity` removed); add yours beside them.
   `reason_code` comes from the closed vocabulary in `scanner/verdicts.py:CURATION_REASON_CODES` — `sql-identifier-fp`, `test-or-fixture-path`, `sample-or-demo`, `vendored-code`, `not-reachable`, `mitigated-in-app`, `by-design`, `product-surface`, `domain-noun-collision`, `placeholder-secret`, `active-harm-fp`, `credited-defense`, `confirmed-real`. Reuse a code or add one to the module; never invent one inline, because a long tail of one-off codes counts to one and the corpus stops being countable.
   This is the file ADR-014 had to reconstruct by hand from 87 archived reports. Writing it as you go is what turns "13th appearance of this FP" into a number that justifies mechanizing the rule.
4. **Evaluate the quality gate:** is there ≥1 real, exploitability-shaped, high-confidence item? Record the boolean — it decides Phase 5 filing.

## Phase 5 — Publish (gated)
1. **Always:** write `docs/scans/<slug>.md` from `docs/templates/scan-post.md` — including the **Scan coverage** block, copied from `reports/<slug>/coverage.json` and never hand-written; prepend a new row to the Scans table in `docs/index.md` **and** a new bullet to `docs/scan-log.md` (the full prose archive), and bump the scan counts in both headers. Three files, every time — on 2026-09-06 the log was found eight entries behind the index because this step only named `index.md`.
2. **If quality gate TRUE and repo not strict-norm:** file a focused courtesy issue on the target (de-branded, with code-path note + concrete fix). If a finding has a clean one-line/one-file fix, also fork → branch → PR referencing the issue.
3. **If repo strict-norm:** post-only, or one issue per critical finding — no grouped issue.
4. **If quality gate FALSE:** post-only (clean-scan write-up). File nothing upstream.
5. Open the `docs:` PR on `elfrost/ai-patchlab`, merge it, then verify publication with **two** checks, in this order:
   - `gh run list --workflow=pages-build-deployment --limit 1` → `success` for the merge commit. This repo publishes through GitHub Actions (`dynamic` source), so this is the authoritative signal.
   - `curl -s -o /dev/null -w '%{http_code}'` on the new post → `200`, and confirm the page actually serves the new text.
   **Do NOT gate on `gh api .../pages/builds/latest`.** On an Actions-published site that legacy endpoint reports the old build API and returns `errored` with `duration: 0` even when the deployment succeeded — observed 2026-08-26, where it said `errored` six polls running while the workflow was green and the page was serving the new content. Treat it as advisory at most; a red status there with a green workflow and a 200 is not an incident.

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
