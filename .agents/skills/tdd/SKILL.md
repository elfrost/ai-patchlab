---
name: tdd
description: Implement a feature or bugfix following strict Red-Green-Refactor discipline. Use when the user asks for test-driven development, requests TDD on a critical function, asks to reproduce a bug with a failing test first, or wants to lock an API surface before implementing.
---

# TDD - Test-Driven Implementation

Run a strict Red-Green-Refactor cycle. Production code may not exist without a preceding observed-failing test.

## When to use
- Critical functions (calculations, money, auth, data integrity)
- Bugfixes (write the failing reproduction first)
- API design where the surface should be locked before implementing
- Non-trivial behavior that is precisely specifiable

Skip for prototypes, config files, generated code, doc-only changes.

## Iron Law

Production code must never exist without a preceding observed-failing test. If implementation exists without one, DELETE and reimplement from the test. No exceptions for "keep as reference" or "tests after".

## The Cycle

For each unit of behavior:

1. **RED** - Write one minimal failing test. Real code, avoid mocks unless external. Names describe intent. "and" in a name means split it.
2. **Verify RED** - Run the test. It must FAIL (not error from syntax/imports) for the expected missing-behavior reason. If it passes on first run, the behavior already exists somewhere - stop and investigate.
3. **GREEN** - Write the simplest code that satisfies the test. No unrelated features. YAGNI ruthlessly.
4. **Verify GREEN** - All tests pass (new + pre-existing). Output is clean.
5. **REFACTOR** - Only after green. Remove duplication, improve names, extract helpers. Re-run tests after each refactor step.

## Workflow
1. Read `AGENTS.md`, `CLAUDE.md` if present, `examples/`, `tests/conftest.py`.
2. Decompose the work into a list of behaviors. Each behavior = one cycle. Start with the simplest happy path, then edges, then errors.
3. Run one cycle at a time. Do NOT batch behaviors into one test.
4. After all behaviors are green:
   ```bash
   ruff check src/ tests/
   black --check src/ tests/
   pytest tests/ -v --cov=src/ --cov-report=term-missing
   ```
5. Report tests written, coverage delta, refactorings applied.

## Anti-rationalizations

| Thought | Counter |
|---------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30s. |
| "Tests after work equally" | Post-hoc tests pass by construction - prove nothing. |
| "Already manually tested" | Manual is unsystematic and unreproducible. |
| "Deleting working code is waste" | Sunk cost. Unverified code is debt. |

## Red flags - restart the cycle if

- Implemented before writing the test
- Test passed on first run (behavior already existed)
- Cannot articulate why the test failed
- Postponed test creation
- Kept code "as reference" while writing tests

## Output

```
TDD Report
Feature/Bug: [name]
Cycles run: [count]

Behaviors covered:
- [x] test_name_1
- [x] test_name_2

Verification:
- Each test was observed to FAIL before implementation: yes/no
- Coverage delta: +X%
- All tests pass: yes/no
- Lint/format clean: yes/no

Refactorings applied:
- [Description, tests still green]
```

## Rules
- One behavior = one test = one cycle. No batching.
- Production code without a preceding observed-failing test means delete and restart.
- Mocks only for external dependencies (DB, network, time, randomness).
- Do not skip "Verify RED" - if you cannot say why the test failed, you did not observe red.
- This skill does not replace `execute-prp`. Use TDD when discipline matters more than speed.
