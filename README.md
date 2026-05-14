# AI PatchLab

AI PatchLab is an AI-assisted security remediation toolkit. The MVP starts with a
local repository scanner foundation that normalizes security findings and writes
actionable JSON and Markdown reports.

Public scan write-ups: [elfrost.github.io/ai-patchlab](https://elfrost.github.io/ai-patchlab/).

## Quick Start

```powershell
# Setup
cd path\to\ai-patchlab
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"

# Run a scan against a local repository
python scanner/run_scan.py --repo "C:\path\to\repo"

# Run this repository against itself
python scanner/run_scan.py --repo "."

# Scan a public repository by URL (shallow clone into a temp dir, then deleted)
python scanner/run_scan.py --from-git-url "https://github.com/owner/repo" --reports-dir "reports\owner-repo"

# Filter low-noise findings out of public reports (default keeps everything)
python scanner/run_scan.py --from-git-url "https://github.com/owner/repo" --reports-dir "reports\owner-repo" --min-severity medium

# Tests
python -m pytest tests/ -v

# Lint and format
ruff check scanner src/ tests/
python -m black scanner src/ tests/
```

The scanner creates the `reports/` directory when missing and writes:

- `reports/security_report.json`
- `reports/security_report.md`
- `reports/raw/semgrep.json` when Semgrep is installed and executed
- `reports/raw/gitleaks.json` when Gitleaks is installed and executed
- `reports/raw/trivy.json` when Trivy is installed and executed
- `reports/raw/pip-audit.json` when pip-audit is installed and executed
- `reports/raw/ai-review.json` only when AI review is enabled and the configured
  local command is executed

## Current Scanner Foundation

The v0.1 foundation includes:

- Real Gitleaks execution through the local `gitleaks` CLI
- Real Semgrep execution through the local `semgrep` CLI
- Real Trivy filesystem execution through the local `trivy` CLI
- Real Python dependency auditing through local `pip-audit`
- AI security review disabled by default, with explicit opt-in for a local
  command provider

Each scanner returns findings normalized to:

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

Findings are grouped by severity: `critical`, `high`, `medium`, `low`, and
`info`.

## Recommendation Enrichment

AI PatchLab enriches normalized finding recommendations with a deterministic
rule-based layer in `scanner/recommendations.py`. The enrichment matches finding
rule IDs, titles, tools, and descriptions for known security patterns, then
updates only the normalized `recommendation` field. Raw scanner output remains
unchanged.

Current enriched patterns:

- Stripe/API keys and other exposed secrets
- GitHub personal access tokens
- SQL injection and raw SQL findings
- `subprocess` calls using `shell=True`
- Wildcard CORS origins
- Credential, password, secret, or token logging
- Missing Subresource Integrity on external frontend assets
- Python non-literal dynamic imports
- JavaScript unsafe format string logging

No paid APIs are used for recommendation enrichment.

## Patch Suggestions

AI PatchLab also adds deterministic patch suggestions through
`scanner/remediation/patch_suggestions.py`. The engine matches normalized
findings by title, tool, and security keywords, then fills concise patch fields
for known vulnerability patterns:

- `patch_before` - a short vulnerable-code example
- `patch_after` - a short safer-code example
- `remediation_explanation` - why the change addresses the issue

Current patch suggestion patterns cover wildcard CORS, `subprocess` with
`shell=True`, SQL injection, hardcoded secrets, credential logging, missing
Subresource Integrity, Python non-literal imports, and JavaScript unsafe format
strings. The Markdown report includes these patch suggestions when a
deterministic rule matches. The module uses a small rule contract so a future
GPT-backed provider can be added without changing the report schema.

## Semgrep Setup

AI PatchLab calls the local `semgrep` executable. It does not bundle Semgrep.

Install Semgrep, add it to `PATH`, then verify it from PowerShell:

```powershell
semgrep --version
```

AI PatchLab runs Semgrep with JSON output:

```powershell
semgrep scan --config auto --json --output "reports\raw\semgrep.json" "C:\path\to\repo"
```

If Semgrep is not installed, the full scan still completes and the report
includes one `info` finding explaining that Semgrep was skipped.

Semgrep severities are normalized as `ERROR` -> `high`, `WARNING` -> `medium`,
and `INFO` -> `low`.

## Gitleaks Setup

AI PatchLab calls the local `gitleaks` executable. It does not bundle Gitleaks.

Install Gitleaks for Windows, add it to `PATH`, then verify it from PowerShell:

```powershell
gitleaks version
```

AI PatchLab runs Gitleaks with JSON output:

```powershell
gitleaks detect --source "C:\path\to\repo" --report-format json --report-path "reports\raw\gitleaks.json" --no-git
```

If Gitleaks is not installed, the full scan still completes and the report
includes one `info` finding explaining that Gitleaks was skipped.

Confirmed Gitleaks secret findings are normalized as `high` severity with
`high` confidence.

## Trivy Setup

AI PatchLab calls the local `trivy` executable. It does not bundle Trivy.

Install Trivy for Windows, add it to `PATH`, then verify it from PowerShell:

```powershell
trivy --version
```

AI PatchLab runs Trivy in filesystem mode with JSON output:

```powershell
trivy fs --format json --output "reports\raw\trivy.json" --scanners vuln,misconfig --no-progress --skip-version-check "C:\path\to\repo"
```

If Trivy is not installed, the full scan still completes and the report
includes one `info` finding explaining that Trivy was skipped.

Trivy severities are normalized as `CRITICAL` -> `critical`, `HIGH` -> `high`,
`MEDIUM` -> `medium`, `LOW` -> `low`, and `UNKNOWN` or missing values -> `info`.
The first Trivy integration normalizes vulnerabilities and misconfigurations;
secret scanning remains owned by Gitleaks.

## Dependency Scan Setup

AI PatchLab calls local `pip-audit` for Python dependency vulnerability scanning.
It does not bundle pip-audit.

Install pip-audit, then verify it from PowerShell:

```powershell
python -m pip install pip-audit
pip-audit --version
```

AI PatchLab writes pip-audit JSON output to `reports/raw/pip-audit.json`.
For requirements files, it runs pip-audit with one or more `--requirement`
inputs:

```powershell
pip-audit --format json --output "reports\raw\pip-audit.json" --progress-spinner off --requirement "C:\path\to\repo\requirements.txt"
```

If no root requirements file is found, AI PatchLab can audit a local Python
project with `pyproject.toml` or `pylock.*.toml`:

```powershell
pip-audit --format json --output "reports\raw\pip-audit.json" --progress-spinner off "C:\path\to\repo"
```

pip-audit exit code `0` means no known vulnerabilities were found, and exit code
`1` means one or more known vulnerabilities were found. Both are handled as
successful scanner executions. Other failures become `info` findings so the full
AI PatchLab report still completes.

## AI Review Setup

AI security review is **disabled by default**. The default scan calls no AI
provider, no hosted model, and no remote or paid API. Reports include one
`info` finding (`ai-review-disabled`) explaining the opt-in.

To enable AI review, the user must configure a local command wrapper. AI
PatchLab executes that wrapper directly with `subprocess.run(..., shell=False)`,
captures its JSON output, and normalizes the findings into the shared schema.

Configure with PowerShell environment variables before running a scan:

```powershell
$env:AI_PATCHLAB_AI_REVIEW_ENABLED = "true"
$env:AI_PATCHLAB_AI_REVIEW_PROVIDER = "local_command"
$env:AI_PATCHLAB_AI_REVIEW_COMMAND = "C:\tools\ai-review-wrapper.cmd"
$env:AI_PATCHLAB_AI_REVIEW_TIMEOUT_SECONDS = "120"
```

You can also store the same `AI_PATCHLAB_AI_REVIEW_*` keys in a project `.env`
file at the repository root.

Supported provider values for v0.1: `disabled`, `local_command`. No default
remote provider, endpoint, model, or token variable is shipped. Adding any
future remote provider requires explicit configuration and a new ADR.

AI PatchLab calls the configured wrapper with:

```powershell
C:\tools\ai-review-wrapper.cmd --repo "C:\path\to\repo" --output "reports\raw\ai-review.json"
```

The wrapper must either write JSON to the `--output` path or print JSON to
stdout. When stdout is used and the output file is missing, AI PatchLab writes
the captured stdout to `reports/raw/ai-review.json` for traceability.

Accepted JSON shapes:

```json
[
  {
    "id": "ai-review-example",
    "severity": "medium",
    "title": "Potential unsafe dynamic execution",
    "description": "A local AI reviewer flagged a risky execution pattern.",
    "file": "src/example.py",
    "line": 42,
    "recommendation": "Replace with an allowlisted dispatcher.",
    "confidence": "medium"
  }
]
```

```json
{
  "findings": [
    {
      "id": "ai-review-example",
      "severity": "medium",
      "title": "Potential unsafe dynamic execution",
      "description": "A local AI reviewer flagged a risky execution pattern.",
      "file": "src/example.py",
      "line": 42,
      "recommendation": "Replace with an allowlisted dispatcher.",
      "confidence": "medium"
    }
  ]
}
```

Each record is normalized to the AI PatchLab finding schema, the `tool` field
is forced to `ai-security-review`, and missing patch fields default to empty
strings. Invalid severity or confidence values fall back to safe defaults.

Failure fallback: if AI review is enabled but the configured command is
missing, times out, exits non-zero with no findings, or emits unparseable JSON,
AI PatchLab emits one normalized `info` finding (`ai-review-command-error`,
`ai-review-json-parse-error`, `ai-review-no-findings`, or
`ai-review-not-configured`) and the full report still completes.

## Project Structure

```text
ai-patchlab/
|-- scanner/             # Scanner CLI, finding model, recommendations, reports
|-- scanner/remediation/ # Deterministic patch suggestion engine
|-- scanner/scanners/    # Semgrep, Gitleaks, Trivy, and dependency adapters
|-- scanner/tools/       # External scanner process runners
|-- reports/             # Generated security reports
|-- src/                 # Legacy scaffold entry point
|-- tests/               # pytest tests
|-- examples/            # Reference implementation patterns
|-- PRPs/                # Product Requirements Prompts
|-- docs/                # GitHub Pages site (public scan write-ups)
|-- .claude/             # Claude commands and agents
|-- .agents/             # Codex skills
|-- AGENTS.md            # Codex/OpenAI runtime instructions
|-- CLAUDE.md            # Claude runtime instructions
`-- pyproject.toml       # Dependencies and tool config
```

## Notes

- No web app is included in v0.1.
- No external paid APIs are called.
- AI security review is disabled by default and must remain local or
  explicitly user-configured. No remote provider or paid API is contacted
  unless the user opts in to a future explicitly configured provider.
