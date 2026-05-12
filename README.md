# AI PatchLab

AI PatchLab is an AI-assisted security remediation toolkit. The MVP starts with a
local repository scanner foundation that normalizes security findings and writes
actionable JSON and Markdown reports.

## Quick Start

```powershell
# Setup
cd C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\ai-patchlab
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"

# Run a scan against a local repository
python scanner/run_scan.py --repo "C:\path\to\repo"

# Run this repository against itself
python scanner/run_scan.py --repo "."

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

## Current Scanner Foundation

The v0.1 foundation includes:

- Real Gitleaks execution through the local `gitleaks` CLI
- Real Semgrep execution through the local `semgrep` CLI
- Trivy placeholder
- Dependency scan placeholder
- AI security review placeholder

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

## Project Structure

```text
ai-patchlab/
|-- scanner/             # Scanner CLI, finding model, recommendations, reports
|-- scanner/remediation/ # Deterministic patch suggestion engine
|-- scanner/scanners/    # Semgrep and Gitleaks adapters plus remaining placeholders
|-- scanner/tools/       # External scanner process runners
|-- reports/             # Generated security reports
|-- src/                 # Legacy scaffold entry point
|-- tests/               # pytest tests
|-- examples/            # Reference implementation patterns
|-- PRPs/                # Product Requirements Prompts
|-- docs/                # Technical documentation
|-- .claude/             # Claude commands and agents
|-- .agents/             # Codex skills
|-- AGENTS.md            # Codex/OpenAI runtime instructions
|-- CLAUDE.md            # Claude runtime instructions
`-- pyproject.toml       # Dependencies and tool config
```

## Notes

- No web app is included in v0.1.
- No external paid APIs are called.
- Placeholder scanners are intentionally simple and ready to be replaced by real
  tool integrations.
