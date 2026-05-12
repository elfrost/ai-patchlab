# /dependency-check — Dependency Audit

Run a comprehensive dependency audit: vulnerabilities, outdated packages, compatibility.

## Argument
`$ARGUMENTS` — Optional flags: `--fix` to auto-apply safe updates.

## Process

1. **Read project context:**
   - Read `pyproject.toml` for declared dependencies
   - Read CLAUDE.md for tech stack info

2. **Spawn dependency-manager agent** to analyze all project dependencies:
   - Vulnerability scan (pip-audit)
   - Outdated package analysis
   - Compatibility matrix
   - Update plan with risk levels

3. **Review findings:**
   - Display the structured dependency report
   - Highlight CRITICAL vulnerabilities (require immediate action)
   - Show update plan organized by risk level

4. **If `--fix` flag is present OR user approves:**
   - Apply safe updates (patch versions only) to pyproject.toml
   - Run `pip install -e ".[dev]"` to install updates
   - Run full test suite after each update:
     ```bash
     pytest tests/ -v
     ```
   - Revert any update that breaks tests
   - Report what was updated and what was skipped

5. **For CRITICAL vulnerabilities without safe fix:**
   - Explain the risk
   - Propose workaround or migration plan
   - Ask user for decision

## Usage
```
/dependency-check              — Full audit (report only)
/dependency-check --fix        — Audit + auto-apply safe updates
```

## Rules
- ALWAYS check pip-audit is installed before running
- ALWAYS run tests after each dependency update
- NEVER update a major version without user approval
- Revert updates that break tests — leave the project in a working state
- Report even if everything is up to date (confirmation is valuable)
- Pin exact versions in pyproject.toml (no ranges for production deps)
