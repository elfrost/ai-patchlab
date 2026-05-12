---
name: fix-issue
description: Diagnose, fix, test, review, and commit a bug fix end-to-end. Use when the user reports a bug, error message, or GitHub issue that needs to go from "broken" to "fixed and committed" in one flow.
---

# Fix Issue

End-to-end bug fix. Codex executes the full sequence inline (Claude has subagents for each step; Codex does them sequentially in one model run).

## Phase 1: Understand
1. Parse the bug description from the user input
2. If a GitHub issue URL: `gh issue view <number> --json title,body,comments`
3. Read CLAUDE.md / AGENTS.md / ROADMAP.md for project context
4. Track progress with a Diagnose -> Fix -> Test -> Review -> Commit checklist

## Phase 2: Diagnose
1. Search the codebase for the error message or related symbols
2. Read recent logs if `logs/` exists
3. Trace the root cause (not just the symptom)
4. If you cannot reproduce or find the root cause after 2 attempts, STOP and ask the user for more context

## Phase 3: Fix
1. Apply the minimal change that addresses the root cause
2. Do NOT modify unrelated files
3. Do NOT refactor surrounding code

## Phase 4: Test
1. Verify existing tests still pass: `pytest tests/ -v`
2. Write a regression test that fails without the fix and passes with it
3. Run coverage on affected files

## Phase 5: Review
1. Read the diff and check for: regressions, similar bug patterns elsewhere, root cause vs symptom
2. If CRITICAL issues are found, fix them and re-review

## Phase 6: Validate
Run the full validation loop (max 3 retries):
```
ruff check src/ tests/
black --check src/ tests/
pytest tests/ -v
```
Auto-fix lint/format with `--fix` and `black`. Re-run until all pass.

## Phase 7: Commit
1. Show the user the full diff
2. Propose a commit message: `fix: <description of what was fixed>`
3. Stage specific files (not `git add -A`)
4. Commit only after user approval

## Rules
- Always diagnose before fixing — understand the root cause
- Always write a regression test — the same bug should never come back
- Stop after 2 failed diagnosis attempts and ask for more context
- Do NOT push — commit locally and let the user decide when to push
- Keep the fix minimal
