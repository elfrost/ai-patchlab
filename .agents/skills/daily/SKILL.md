---
name: daily
description: Autonomous daily scan-and-disclose pipeline — status sweep of open disclosures, candidate discovery + responsiveness/strict-norm pre-check, one scan, curation, and gated publication (post always; issue/PR only when the quality gate passes). Full-auto per the user's 2026-05-28 decision, with guardrails that prevent the "looks like a bot / advertising" failure mode.
---

# Daily Pipeline

Runs the full public-scan workflow once per day without the user driving it. Mode via `$ARGUMENTS`: default = autonomous (public actions included); `--dry-run` = no irreversible public actions; `--status-only` = Phase 1 only.

## Non-negotiable guardrails
1. **One scan/day** — if a scan already ran today (state file), do status-only.
2. **Quality gate on filing** — always publish the write-up post; file a courtesy issue / open a PR ONLY when curation found ≥1 real, exploitability-shaped, high-confidence item. Else post-only (clean-scan format).
3. **Strict-norm detection** — real SECURITY.md / commercial backing / security team → post-only or one-vuln-per-issue, never a grouped issue (dstack #3908 lesson).
4. **De-branded issue text** — finding-first, code-path note, one footer link max.
5. **Never rescan** — dedup candidates against `docs/scans/` slugs.
6. **Kill switch** — if `.daily-paused` exists at repo root, abort.
7. **Manual-disclosure backlog is a blocking warning.** Count the `pending_private_disclosure*` entries in `reports/.daily_state.json`. Any entry pending more than 7 days gets a loud banner at the top of the run (repo, severity, days waiting). Any High/Critical entry pending more than 14 days blocks a new scan entirely — run status-only and tell the user to clear the queue. On 2026-08-21 six drafted reports were found unsent, the oldest 22 days, including an unauthenticated-admin finding; nothing surfaced them because every phase only looked forward at the next scan.
8. **State shape.** Run history lives in `runs_recent`; the `runs` key is a vestigial empty list — do not write to it. Ad-hoc keys join one of four families: `pending_private_disclosure*`, `withheld_finding_*`, `excluded_repos`/`excluded_note`, `*_note`. Drafted disclosure emails live in `reports/disclosures/` (gitignored); when one is sent, swap its pending entry for a `sent` record with date and channel.

## State
`reports/.daily_state.json` (gitignored): `{"last_run":"YYYY-MM-DD","last_slug":"...","runs":[...]}`. If `last_run == today`, rate-limit to status-only.

## Phase 0 — Preconditions
Abort if `.daily-paused`. Read state. If already ran today → status-only.

## Phase 1 — Status sweep (always)
`gh search prs/issues --author=elfrost` (exclude `elfrost/ai-patchlab`). For each open disclosure updated since `last_run`, read latest comments/reviews and act:
- maintainer asks for a PR → fork → branch → single-purpose fix → PR referencing the issue (commit author `5491654+elfrost@users.noreply.github.com`).
- merged/closed-as-fixed → update `docs/scans/<slug>.md` timeline + `docs/index.md` ✅ badge + memory `project_first_resolved_disclosure.md`.
- rejection → keep honest record (quote response in post, note badge, do not delete).
Update outcomes ONLY after upstream merge/close, never on open. Stop here if `--status-only`.

## Phase 2 — Candidate discovery + pre-check
`gh search repos --language=python --stars=1500..6000 --sort=updated` filtered to AI/agent/LLM/RAG/inference. Drop already-scanned slugs. Responsiveness check (recent closed issues + merged PRs from ≥2 contributors). Strict-norm detection → publication mode. Pick ONE; record why.

## Phase 3 — Scan
`.venv/Scripts/python.exe scanner/run_scan.py --from-git-url "<url>" --reports-dir reports/<slug> --min-severity medium` (`--ignore-file` for obvious sample/demo subtrees).

## Phase 4 — Curate
Group by rule family; auto-flag tests/sample/examples/demos/fixtures as candidate-FP. Inspect top 5 real candidates in-repo via `gh api .../contents/<path>`. Write per-finding verdicts. Evaluate the quality gate boolean.

## Phase 5 — Publish (gated)
Always: write `docs/scans/<slug>.md` + prepend `docs/index.md`. If gate TRUE and not strict-norm: file focused de-branded courtesy issue (+ PR for clean one-line fixes). If strict-norm: post-only or one-issue-per-critical. If gate FALSE: post-only. Open `docs:` PR on `elfrost/ai-patchlab`, merge, verify publication via `gh run list --workflow=pages-build-deployment --limit 1` = `success` AND the post returns 200 serving the new text. Do NOT gate on `pages/builds/latest` — on this Actions-published site it reports `errored` even when the deploy succeeded (2026-08-26).

## Phase 6 — Record
Update `reports/.daily_state.json`; update memory on resolutions/lessons; print a 3-line summary.

## Rules
Never rescan a covered repo. Never file when the gate is false. Never skip the strict-norm check before a grouped issue. Always use the noreply commit email. Keep honest records of rejections. In `--dry-run`, zero irreversible public actions.
