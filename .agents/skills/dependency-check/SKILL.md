---
name: dependency-check
description: Audit project dependencies for vulnerabilities, outdated packages, and compatibility issues. Optionally apply safe updates with test validation. Use periodically or before release.
---

# Dependency Check

## Phase 1: Read state
1. Read `pyproject.toml` for declared dependencies
2. Read `CLAUDE.md` / `AGENTS.md` for tech stack context
3. Check that `pip-audit` is installed (suggest `pip install pip-audit` otherwise)

## Phase 2: Analyze
Run in this order:
1. `pip-audit 2>&1` — vulnerability scan
2. `pip list --outdated 2>&1` — outdated packages
3. Compatibility check — for each outdated package, look at its changelog for breaking changes since the current pinned version

## Phase 3: Report
Produce a structured report:
- CRITICAL vulnerabilities (require immediate action)
- HIGH vulnerabilities
- Updates available — organized by risk:
  - SAFE: patch-level only (1.2.3 -> 1.2.4)
  - MODERATE: minor (1.2.x -> 1.3.x)
  - RISKY: major (1.x -> 2.x)

## Phase 4: Optionally apply (if user passes `--fix` or approves)
1. Apply SAFE updates only — patch versions to pyproject.toml
2. Run `pip install -e ".[dev]"`
3. Run the test suite: `pytest tests/ -v`
4. If tests fail, revert that update and flag it
5. Report what was updated and what was skipped

For CRITICAL vulnerabilities without a safe fix:
- Explain the risk
- Propose a workaround or migration plan
- Ask the user for the call

## Rules
- Always check `pip-audit` is installed before scanning
- Always run tests after each update
- Never update a major version without user approval
- Revert updates that break tests — leave the project in a working state
- Pin exact versions in pyproject.toml (no ranges for prod deps)
