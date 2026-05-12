---
name: refactor
description: Analyze code for smells, complexity, and pattern violations, then optionally execute selected refactorings with validation after each change. Use when the user wants to clean up a file, module, or directory without changing behavior.
---

# Refactor

Targeted refactoring with diff preview and per-change validation. Default scope is `src/`; user may pass a path.

## Phase 1: Analyze
1. Read CLAUDE.md for thresholds (file size, function length, complexity)
2. Detect smells in scope:
   - Files > 300 lines (per project standard)
   - Functions > 50 lines
   - Cyclomatic complexity > 10
   - Duplicated blocks
   - Naming violations (per CLAUDE.md conventions)
   - Missing type hints (required per CLAUDE.md)

## Phase 2: Propose
Produce a numbered refactoring report:
- R-001: <smell> in <file:line> -> <proposed fix> (impact: low / med / high)
- R-002: ...

For each proposal, include the exact change (diff preview), why it improves the code, and the risk level.

## Phase 3: Approve
Ask the user which refactorings to execute:
- "all" — execute all
- "R-001, R-003" — execute selected
- "none" — report only

## Phase 4: Execute (atomic per change)
For each approved refactoring:
1. Apply the change
2. Run validation:
   ```
   ruff check src/
   black --check src/
   pytest tests/ -v --tb=short
   ```
3. If validation fails, REVERT the change and flag it
4. Continue with the next refactoring

## Phase 5: Final validation + commit
1. Run the full validation loop after all changes
2. Show the cumulative diff
3. Ask the user to approve the commit
4. Commit message: `refactor: <description>`

## Rules
- Never refactor without showing the plan first
- Always run tests after each refactoring
- If tests break, revert and flag — don't try to "fix forward"
- Keep refactorings atomic — one change at a time
- Preserve behavior — refactoring is not a feature change
