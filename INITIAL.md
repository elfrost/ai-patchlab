# Feature Request: AI PatchLab MVP v0.1 - Scanner Foundation

## FEATURE

AI PatchLab is an AI-assisted security remediation toolkit. The goal is not only
to detect vulnerabilities, but to produce actionable remediation plans and
eventually patch-ready outputs.

The immediate MVP objective is to create the initial local scanner foundation.
It must accept a local repository path, run modular placeholder scanners, and
write normalized security reports in JSON and Markdown.

Suggested command:

```powershell
python scanner/run_scan.py --repo "C:\path\to\repo"
```

## EXAMPLES

- `examples/config_pattern.py` - Configuration pattern
- `examples/service_pattern.py` - Modular service pattern
- `scanner/run_scan.py` - CLI entry point for scanner orchestration
- `scanner/scanners/` - Placeholder scanner modules

## DOCUMENTATION

- Semgrep: https://semgrep.dev/docs/
- Gitleaks: https://github.com/gitleaks/gitleaks
- Trivy: https://trivy.dev/latest/docs/

## TECH STACK

- Python 3.11+
- Data stack selected for local repository analysis and report generation
- pytest for tests
- ruff and black for linting and formatting
- No web app in v0.1
- No external paid APIs in v0.1

## DATA FLOW

```text
Local repository path
    -> scanner/run_scan.py
    -> scanner modules
       - Semgrep placeholder
       - Gitleaks placeholder
       - Trivy placeholder
       - dependency scan placeholder
       - AI security review placeholder
    -> normalized findings
    -> severity grouping
    -> reports/security_report.json
    -> reports/security_report.md
```

## NORMALIZED FINDING SHAPE

Every scanner finding must include:

- `id`
- `tool`
- `severity`
- `title`
- `description`
- `file`
- `line`
- `recommendation`
- `confidence`
- `patch_before`
- `patch_after`
- `remediation_explanation`

Findings are grouped by:

- `critical`
- `high`
- `medium`
- `low`
- `info`

## CONSTRAINTS

- Keep the project simple and modular.
- Use Python.
- Accept a local repository path as input.
- Create `reports/` if missing.
- Generate both `reports/security_report.json` and `reports/security_report.md`.
- Make it runnable from PowerShell.
- Do not add a web app yet.
- Do not add external paid APIs yet.
- Do not over-engineer.

## MVP SCOPE

1. CLI entry point at `scanner/run_scan.py`.
2. Placeholder scanner modules for Semgrep, Gitleaks, Trivy, dependency scan, and
   AI security review.
3. Normalized finding model.
4. Severity grouping.
5. JSON report output.
6. Markdown report output.
7. README usage instructions.
8. Tests for report generation and CLI error handling.

## OUT OF SCOPE

- Real Semgrep execution.
- Real Gitleaks execution.
- Real Trivy execution.
- Real dependency vulnerability database integration.
- Paid AI API calls.
- Web UI.
- Database persistence.
- Patch generation.

## SUCCESS CRITERIA

- [x] `python scanner/run_scan.py --repo "C:\path\to\repo"` runs from PowerShell.
- [x] Missing `reports/` directory is created automatically.
- [x] `reports/security_report.json` is generated.
- [x] `reports/security_report.md` is generated.
- [x] Placeholder scanners exist for all requested tool categories.
- [x] Findings use the normalized schema.
- [x] Findings are grouped by severity.
- [x] README includes clear usage instructions.
