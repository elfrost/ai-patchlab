# /tdd — Test-Driven Implementation

Implement a feature or bugfix following strict Red-Green-Refactor discipline.

Description: $ARGUMENTS

## When to use this command

Use `/tdd` instead of going straight to `/execute-prp` or freeform implementation when:
- The behavior is precisely specifiable but the implementation is non-trivial
- The function is critical (calculations, money, auth, data integrity)
- You're fixing a bug — write the failing test that reproduces it FIRST
- You want to lock the API surface before implementing

Skip TDD for: throwaway prototypes, configuration files, generated code, pure docs.

## The Iron Law

> Production code must never exist without a preceding **observed failing test**.

If implementation already exists without a test that was seen to fail, DELETE it and reimplement from the test. No "keep as reference". No "I'll write tests after". Sunk cost is not a reason.

## The Cycle

For each unit of behavior:

### 1. RED — Write one failing test

Write a single minimal test for one behavior. Use real code, avoid mocks unless unavoidable. Test names describe intent: `test_calculate_ev_returns_positive_for_good_edge`. If the name contains "and", split into two tests.

### 2. Verify RED

Run the test. Confirm:
- It **fails** (not errors out from a syntax issue)
- The failure message reflects **missing behavior** (not missing import / typo)
- The failure occurs for the **expected reason**

If the test passes on first run, the behavior already exists somewhere — investigate before continuing.

### 3. GREEN — Write minimal code

Implement only the simplest code that satisfies the test. No unrelated features. No refactoring of other components. No "while I'm here". YAGNI ruthlessly.

### 4. Verify GREEN

Run all tests. Confirm:
- The new test passes
- No pre-existing test broke
- Output is clean (no warnings, no errors)

### 5. REFACTOR (only if green)

Once green, remove duplication, improve names, extract helpers — without changing behavior. Re-run tests after each refactor step.

## Process for this command

1. **Read the project rules** (`CLAUDE.md`, `examples/`, `tests/conftest.py` for fixtures).
2. **Decompose the work**: list behaviors as a TDD checklist (each is one Red-Green-Refactor cycle). Use TodoWrite to track them.
3. **Pick the first behavior** — start with the simplest happy path, then edge cases, then errors.
4. **Run the cycle** for each behavior in order. Do NOT batch multiple behaviors into one test.
5. **After all behaviors are green**, run the full validation loop:
   ```bash
   ruff check src/ tests/
   black --check src/ tests/
   pytest tests/ -v --cov=src/ --cov-report=term-missing
   ```
6. **Report**: list of tests written, coverage delta, refactorings applied.

## Anti-rationalization table

| You'll think | Counter |
|--------------|---------|
| "Too simple to test" | Simple code breaks. The test takes 30 seconds. |
| "I'll add tests after" | Post-hoc tests prove nothing about correctness — they pass by construction. |
| "Already manually tested" | Manual = unsystematic + unreproducible. |
| "Deleting working code is wasteful" | Sunk cost fallacy. Unverified code is technical debt. |
| "TDD is dogmatic" | TDD finds bugs in 30s instead of 30min in production. |

## Red flags requiring restart

If any of these happen, stop, delete uncommitted code, restart the cycle:
- Implemented before writing the test
- Tests passing on first run
- Cannot articulate WHY the test failed
- Postponed test creation "just for this one"
- Kept code "as reference" while writing the test

## Delegation

For the actual test writing and validation execution, delegate to the `tester` agent in TDD mode — pass it the behavior list and the Iron Law. The agent must observe each test fail before implementing.

## Output

```
## TDD Report
**Feature/Bug:** [name]
**Cycles run:** [count]

### Behaviors covered
- [x] test_X_happy_path
- [x] test_X_empty_input
- [x] test_X_invalid_value_raises

### Verification
- Each test was observed to FAIL before implementation: yes/no
- Coverage delta: +X%
- All tests pass: yes/no
- Lint/format clean: yes/no

### Refactorings applied
- [Description of each refactor + tests still green after]
```

## Rules
- One behavior = one test = one Red-Green-Refactor cycle. No batching.
- Production code WITHOUT a preceding observed-failing test = delete and restart.
- If you cannot articulate why a test failed, you didn't observe RED — restart.
- Mocks only when external (DB, network, time, randomness). Never to mock the unit under test.
- The cycle is not optional. Do not skip "Verify RED".
