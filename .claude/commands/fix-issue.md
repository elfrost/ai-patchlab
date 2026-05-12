# /fix-issue — End-to-End Bug Fix

Diagnose, fix, test, review, and commit a bug fix in one command.
Shortcut for `/pipeline bugfix` with a streamlined single-command UX.

## Argument
`$ARGUMENTS` — Bug description, error message, or issue reference.

## Process

### Phase 1: Understand the Issue
1. Read `$ARGUMENTS` — parse the bug description
2. If a GitHub issue URL is provided, fetch issue details:
   ```bash
   gh issue view <number> --json title,body,comments 2>&1
   ```
3. Read CLAUDE.md + ROADMAP.md for project context
4. Create TodoWrite tracking with steps: Diagnose -> Fix -> Test -> Review -> Commit

### Phase 2: Diagnose
1. Spawn **debugger** agent with the bug description:
   - Include the full bug context from Phase 1
   - Include relevant file paths if mentioned in the error
   - The debugger will: search codebase, check logs/, reproduce, trace root cause, apply fix, verify
2. Capture the diagnosis + fix output
3. If the debugger cannot reproduce or find root cause after 2 attempts:
   - STOP and ask user for more context
   - Show what was investigated

### Phase 3: Test
1. Spawn **tester** agent:
   - Verify existing tests still pass
   - Write a regression test for this specific bug
   - Run coverage analysis on affected files
2. If tests fail:
   - Spawn debugger again with test failure details
   - Re-run tests after fix
   - Max 2 iterations

### Phase 4: Review
1. Spawn **code-reviewer** agent (multi-reviewer mode):
   - Review the fix changes
   - Check for regressions and similar patterns elsewhere
   - Verify root cause is addressed, not just symptom
2. If CRITICAL issues found:
   - Fix them before proceeding
   - Re-run review

### Phase 5: Validate
1. Run full validation:
   ```bash
   ruff check src/ tests/
   black --check src/ tests/
   pytest tests/ -v
   ```
2. Loop-until-passing (max 3 retries):
   - If ruff fails: run `ruff check src/ tests/ --fix` then re-check
   - If black fails: run `black src/ tests/` then re-check
   - If pytest fails: spawn debugger to fix test failures

### Phase 6: Commit
1. Show the full diff to user:
   ```bash
   git diff
   git diff --cached
   ```
2. Generate commit message: `fix: [description of what was fixed]`
3. Stage all changed files (specific files, not `git add -A`)
4. Show commit message to user for approval
5. Commit on approval

## Rules
- ALWAYS diagnose before fixing — understand the root cause
- ALWAYS write a regression test — the same bug should never come back
- ALWAYS review the fix — even small fixes can introduce regressions
- If diagnosis takes more than 2 attempts, stop and ask user for more context
- Do NOT push — only commit locally. User decides when to push
- Do NOT modify files unrelated to the bug fix
- Keep the fix minimal — address the root cause, don't refactor surrounding code
