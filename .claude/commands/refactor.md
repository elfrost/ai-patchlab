# /refactor — Targeted Refactoring

Analyze code for smells, complexity, and pattern violations, then optionally execute refactoring.

## Argument
`$ARGUMENTS` — Target path (file or directory). If empty, scan `src/`.

## Process

1. **Spawn refactorer agent** targeting `$ARGUMENTS` (or `src/` if empty)
2. **Review the refactoring report**
3. **Ask user** which refactorings to execute (all, select, or none)
4. **Execute selected refactorings** with validation after each
5. **Run full validation loop** after all changes
6. **Commit** if user approves

## Usage
- `/refactor` — Analyze entire src/
- `/refactor src/services/calculator.py` — Analyze specific file
- `/refactor src/models/` — Analyze specific directory

## Instructions

1. Read CLAUDE.md for project standards and thresholds
2. Determine the target scope:
   - If `$ARGUMENTS` is provided, analyze that path
   - If empty, analyze `src/`
3. Use the refactorer agent (Agent tool) to perform analysis
4. Present the refactoring report to the user
5. Ask the user which refactorings to execute:
   - "all" — execute all proposed refactorings
   - Specific numbers — execute only selected ones (e.g., "R-001, R-003")
   - "none" — report only, no changes
6. For each approved refactoring:
   a. Apply the change
   b. Run validation: `ruff check src/ && black --check src/ && pytest tests/ -v --tb=short`
   c. If validation fails, revert and flag
7. After all changes, run full validation loop
8. Ask user if they want to commit the changes

## Rules
- NEVER refactor without showing the plan first
- ALWAYS run tests after each refactoring
- If tests break, REVERT the change and flag it
- Keep refactorings atomic — one change at a time
- Preserve all existing behavior (refactoring != feature change)
