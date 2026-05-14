# PRP: Phase 3 AI Review Behavior

## Overview
Replace the current AI security review placeholder with a safe, disabled-by-default implementation boundary. The first implementation must not make paid API calls, must not contact a remote AI service by default, and must only run AI review behavior when the user explicitly configures it.

For the MVP, implement a local command provider boundary:

- Default behavior: AI review is disabled and returns one normalized `info` finding explaining how to opt in.
- Configured behavior: a user-provided local command can emit AI review findings as JSON, which AI PatchLab validates and normalizes into the existing `scanner.models.Finding` schema.
- Failure behavior: local command failures, missing output, invalid JSON, or invalid finding records become normalized `info` findings so the full report still completes.

Do not add a default remote provider in this PRP. If a future remote or paid provider is added, it must require explicit configuration, a new ADR, and tests proving no network call happens unless enabled.

## Dependencies
- Requires: Phase 1 scanner foundation and normalized finding schema.
- Requires: Phase 2 external scanner adapter patterns for local command execution and fallback findings.
- Blocks: Future GPT-backed remediation or AI-assisted patch generation should reuse this explicit opt-in boundary.

## Context & References

### MUST READ - Load these into your context
- file: `AGENTS.md` - why: Codex workflow, roadmap/doc sync, PowerShell command conventions, and runtime parity requirements.
- file: `CLAUDE.md` - why: sibling runtime instructions, coding standards, and config/secrets rules that must stay aligned with AGENTS.
- file: `ROADMAP.md` - why: Phase 3 includes `Keep AI review local or explicitly user-configured`.
- file: `DECISIONS.md` - why: ADR-002, ADR-003, ADR-006, ADR-007, ADR-008, and ADR-009 establish local-first scanner behavior, no paid APIs by default, and fallback findings for scanner failures.
- file: `INITIAL.md` - why: MVP constraints, normalized finding shape, and explicit no-paid-API boundary.
- file: `README.md` - why: setup/configuration docs must clearly explain disabled/default behavior and opt-in local command usage.
- file: `scanner/scanners/ai_review.py` - why: current placeholder to replace.
- file: `scanner/scanners/__init__.py` - why: scanner registry already includes `scan_ai_security_review`.
- file: `scanner/scanners/common.py` - why: current placeholder helper and normalized info finding style.
- file: `scanner/scanners/dependency_scan.py` - why: reference for failure-to-info behavior, raw JSON parsing, normalization, and enrichment.
- file: `scanner/tools/pip_audit_runner.py` - why: reference for local command runner dataclass, subprocess handling, and missing-tool handling.
- file: `scanner/run_scan.py` - why: scanner orchestration currently expects each scanner to preserve partial-report behavior internally.
- file: `scanner/models.py` - why: authoritative `Finding` fields, severities, confidences, and validation rules.
- file: `scanner/report.py` - why: JSON and Markdown reports render normalized findings without scanner-specific branches.
- file: `scanner/recommendations.py` - why: AI review findings should continue through deterministic recommendation enrichment.
- file: `scanner/remediation/patch_suggestions.py` - why: AI review findings should continue through deterministic patch suggestions when matched.
- file: `tests/test_scanner_foundation.py` - why: current full-scan expectations include the AI review placeholder and normalized schema assertions.
- file: `tests/test_dependency_scan.py` - why: test style for missing config/input, scanner failures, invalid JSON, and normalized vulnerability records.
- file: `examples/config_pattern.py` - why: use Pydantic settings, `.env`, and explicit defaults for configuration.
- file: `examples/service_pattern.py` - why: keep business logic and external process concerns separated.

### Critical Gotchas
- CRITICAL: No paid API calls by default. Default configuration must not call `httpx`, OpenAI, OpenRouter, hosted LLMs, or any network endpoint.
- CRITICAL: AI review must be disabled unless `AI_PATCHLAB_AI_REVIEW_ENABLED=true` and a supported provider is fully configured.
- CRITICAL: Do not add a default API endpoint, default model, default token variable, or implicit hosted provider.
- CRITICAL: Keep the first provider local-first: a user-controlled local command that receives a repo path and returns JSON findings.
- CRITICAL: Use `subprocess.run(..., shell=False)` with a list command. Do not execute a user config string through the shell.
- CRITICAL: The local command contract must be PowerShell-friendly. Prefer one configured executable or wrapper script path that AI PatchLab invokes with documented arguments.
- CRITICAL: Preserve normalized schema fields exactly: `id`, `tool`, `severity`, `title`, `description`, `file`, `line`, `recommendation`, `confidence`, `patch_before`, `patch_after`, `remediation_explanation`.
- CRITICAL: Treat local command output as untrusted. Validate severity, confidence, paths, and field types before creating `Finding` objects.
- CRITICAL: Preserve partial-report behavior. AI review errors must return a normalized `info` finding instead of raising out of `run_scan`.
- CRITICAL: Keep MVP simple. Do not introduce databases, queues, background jobs, web UI, streaming responses, or complex prompt orchestration.

## Architecture

### New Files
| File | Purpose |
|------|---------|
| `scanner/config.py` | Load AI PatchLab scanner configuration from `.env`/environment with disabled-by-default AI review settings. |
| `scanner/tools/ai_review_runner.py` | Execute a user-configured local AI review command, capture output, write/read `reports/raw/ai-review.json`, and return a typed result object. |
| `tests/test_ai_review.py` | Unit tests for disabled/default behavior, configured local command behavior, invalid output, command failure fallback, and schema normalization. |

### Modified Files
| File | Changes |
|------|---------|
| `scanner/scanners/ai_review.py` | Replace placeholder with config-driven disabled/default behavior, local command provider handling, JSON parsing, validation, enrichment, patch suggestion application, and fallback `info` findings. |
| `scanner/scanners/__init__.py` | Keep `scan_ai_security_review` in the registry; no registry opt-in should be required because the scanner itself handles disabled state safely. |
| `scanner/run_scan.py` | Avoid broad orchestration changes unless tests reveal a necessary narrow adjustment. AI review should preserve partial reports inside its own adapter. |
| `tests/test_scanner_foundation.py` | Update expected default findings and assertions for the disabled AI review finding. |
| `README.md` | Document AI review default disabled behavior, local command opt-in, `.env`/PowerShell examples, JSON output contract, raw report location, and failure fallback. |
| `ROADMAP.md` | Mark `Keep AI review local or explicitly user-configured` complete with `2026/05/13` after implementation and validation pass. |
| `DECISIONS.md` | Add an ADR for disabled-by-default local AI review boundary. |
| `AGENTS.md` | Update scanner directory descriptions and gotchas to say AI review is disabled by default and opt-in/local-first, not a placeholder. |
| `CLAUDE.md` | Mirror AGENTS scanner/configuration wording for runtime parity. |

### Database Changes
None.

### Configuration Contract
Add `scanner/config.py` with a Pydantic settings model following `examples/config_pattern.py`.

Required defaults:

```python
ai_review_enabled: bool = False
ai_review_provider: str = "disabled"
ai_review_command: str = ""
ai_review_timeout_seconds: int = 120
```

Recommended environment variable names:

```powershell
$env:AI_PATCHLAB_AI_REVIEW_ENABLED = "true"
$env:AI_PATCHLAB_AI_REVIEW_PROVIDER = "local_command"
$env:AI_PATCHLAB_AI_REVIEW_COMMAND = "C:\tools\ai-review-wrapper.cmd"
$env:AI_PATCHLAB_AI_REVIEW_TIMEOUT_SECONDS = "120"
```

Use `env_prefix="AI_PATCHLAB_"` if it keeps names clean and testable. Ensure tests can instantiate settings directly without depending on the developer machine `.env`.

### Local Command Contract
When configured with provider `local_command`, AI PatchLab should call:

```powershell
C:\tools\ai-review-wrapper.cmd --repo "C:\path\to\repo" --output "reports\raw\ai-review.json"
```

The command may either write JSON to the output path or print JSON to stdout. If stdout is used and the output file is missing, AI PatchLab should write stdout to `reports/raw/ai-review.json` for traceability.

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
    "recommendation": "Review whether the execution path can be replaced with an allowlisted dispatcher.",
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
      "recommendation": "Review whether the execution path can be replaced with an allowlisted dispatcher.",
      "confidence": "medium"
    }
  ]
}
```

The parser must set `tool="ai-security-review"` regardless of user output unless there is a strong reason to preserve a sub-tool in a future field. Optional patch fields may be accepted, but missing patch fields must default to empty strings.

## Implementation Plan

### Task 1: Add Disabled-by-Default AI Review Configuration
**Goal:** Centralize AI review settings with safe defaults.
**Files:** `scanner/config.py`, `tests/test_ai_review.py`
**Pattern:** Follow `examples/config_pattern.py`.
**Details:**
- Create a `ScannerConfig` or `AiReviewConfig` Pydantic settings model.
- Default `ai_review_enabled=False`.
- Default `ai_review_provider="disabled"`.
- Default `ai_review_command=""`.
- Default timeout should be finite and PowerShell-friendly, for example `120` seconds.
- Add `get_config()` only if needed. Prefer dependency injection in tests where practical so environment state does not leak between tests.
- Validate provider values. Supported values for this PRP: `disabled`, `local_command`.
- If `ai_review_enabled=True` but provider/command is incomplete, the scanner should return a configuration `info` finding rather than raising.

**Validation:**
```bash
python -m pytest tests/test_ai_review.py -v -k "config or disabled"
```

### Task 2: Add Local Command Runner
**Goal:** Execute only explicitly configured local commands and preserve raw output.
**Files:** `scanner/tools/ai_review_runner.py`, `tests/test_ai_review.py`
**Pattern:** Follow `scanner/tools/pip_audit_runner.py`.
**Details:**
- Create a frozen dataclass `AiReviewResult` with fields:
  - `configured: bool`
  - `raw_report_path: Path`
  - `returncode: int | None = None`
  - `stdout: str = ""`
  - `stderr: str = ""`
  - `command: tuple[str, ...] = ()`
- Add a `completed` property equivalent to other runners.
- Implement `run_ai_review_command(repo_path: Path, reports_dir: Path, config: AiReviewConfig) -> AiReviewResult`.
- If disabled or not configured, do not call subprocess.
- Build the command as a list:

```python
[
    config.ai_review_command,
    "--repo",
    str(repo_path),
    "--output",
    str(raw_report_path),
]
```

- Use `capture_output=True`, `text=True`, `encoding="utf-8"`, `errors="replace"`, `check=False`, and `timeout=config.ai_review_timeout_seconds`.
- Catch `OSError` and `subprocess.TimeoutExpired`; write `[]` to the raw report path when needed and return a result with non-zero `returncode`.
- If command succeeds or fails but stdout contains JSON and the output file is missing, write stdout to `reports/raw/ai-review.json`.
- Do not use `shell=True`.
- Do not import or call `httpx` in this runner.

**Validation:**
```bash
python -m pytest tests/test_ai_review.py -v -k "runner or command"
```

### Task 3: Replace AI Review Placeholder With Safe Adapter
**Goal:** Convert disabled/configured AI review states into normalized findings.
**Files:** `scanner/scanners/ai_review.py`, `tests/test_ai_review.py`
**Pattern:** Follow `scanner/scanners/dependency_scan.py`.
**Details:**
- Remove use of `placeholder_finding` for AI review.
- If AI review is disabled, return one normalized `info` finding:
  - `id="ai-review-disabled"`
  - `tool="ai-security-review"`
  - `severity="info"`
  - `title="AI security review is disabled"`
  - `description` states no AI review provider was run and no paid API was called.
  - `file=str(repo_path)`
  - `line=None`
  - `recommendation` explains the local command opt-in at a high level.
  - `confidence="high"`
- If enabled but provider/command is invalid, return one normalized `info` finding:
  - `id="ai-review-not-configured"`
  - `title="AI security review is not fully configured"`
- If the local command returns non-zero and no valid findings can be parsed, return one normalized `info` finding:
  - `id="ai-review-command-error"`
  - `title="AI security review command did not complete successfully"`
  - Include a short, capped stderr/stdout message.
- If JSON cannot be parsed, return one normalized `info` finding:
  - `id="ai-review-json-parse-error"`
  - `title="AI security review JSON output could not be parsed"`
- If findings parse successfully, map each record into `Finding`, force `tool="ai-security-review"`, and then apply `enrich_findings()` and `apply_patch_suggestions()`.
- Keep helper functions private and small: `_read_ai_review_records`, `_map_ai_review_record`, `_fallback_finding`, `_format_scan_error`, `_stable_id`.

**Validation:**
```bash
python -m pytest tests/test_ai_review.py -v -k "disabled or configured or fallback or schema"
```

### Task 4: Preserve Full Scan and Report Behavior
**Goal:** Ensure `run_scan` still emits JSON/Markdown reports in all AI review states.
**Files:** `tests/test_scanner_foundation.py`, `tests/test_ai_review.py`, `scanner/run_scan.py` only if necessary.
**Details:**
- Update `test_run_scan_creates_json_and_markdown_reports` to expect an `ai-security-review` info finding whose ID is `ai-review-disabled` by default.
- Add or update tests proving:
  - default scan creates both reports without configuring AI review;
  - default scan does not invoke `subprocess.run` for AI review;
  - configured local command finding appears in `reports/security_report.json`;
  - command failure still allows `reports/security_report.json` and `reports/security_report.md` to be written.
- Avoid broad exception swallowing in `collect_findings` unless the existing scanner pattern is deliberately changed and covered by tests.

**Validation:**
```bash
python -m pytest tests/test_scanner_foundation.py tests/test_ai_review.py -v
```

### Task 5: Document Setup and Runtime Boundaries
**Goal:** Make default behavior and opt-in configuration clear.
**Files:** `README.md`, `AGENTS.md`, `CLAUDE.md`
**Details:**
- README:
  - Replace "AI security review placeholder" with "AI security review disabled by default".
  - Add `reports/raw/ai-review.json` to generated outputs only when configured and executed.
  - Add an `AI Review Setup` section.
  - Show PowerShell env var examples.
  - Document the local command JSON contract.
  - State clearly that no AI provider, remote endpoint, or paid API is called unless the user explicitly configures one in a future implementation.
  - Document failure fallback: errors become `info` findings and the report still completes.
- AGENTS.md and CLAUDE.md:
  - Update `scanner/scanners/` descriptions to remove "placeholder AI review".
  - Add a known gotcha or important rule: AI review must remain disabled by default and local/explicitly configured.
  - Keep both runtime docs aligned.

**Validation:**
```bash
rg "AI security review|AI review|ai-review|AI_PATCHLAB_AI_REVIEW" README.md AGENTS.md CLAUDE.md
```

### Task 6: Record Roadmap and Architecture Decision
**Goal:** Keep shared project state aligned with the implemented behavior.
**Files:** `ROADMAP.md`, `DECISIONS.md`
**Details:**
- ROADMAP:
  - Mark `Keep AI review local or explicitly user-configured` as `[x] ... (2026/05/13)` after tests pass.
- DECISIONS:
  - Add a new ADR at the top of the decisions list, for example `ADR-010: Disabled-by-default local AI review boundary`.
  - Decision should state:
    - AI review is disabled by default.
    - The MVP supports a local command provider boundary.
    - No remote or paid provider is called by default.
    - Failures are represented as normalized `info` findings to preserve partial reports.

**Validation:**
```bash
rg "AI review|ADR-010|2026/05/13" ROADMAP.md DECISIONS.md
```

### Task 7: Full Validation
**Goal:** Verify the complete implementation and docs.
**Files:** all changed files.
**Details:**
- Run formatter if needed.
- Run lint, format check, and all tests.
- Run a smoke scan against the repository itself. The smoke scan should complete even when AI review is not configured.

**Validation:**
```bash
ruff check scanner src tests
python -m black --check scanner src tests
python -m pytest tests/ -v
python scanner/run_scan.py --repo "."
```

## Final Validation Loop

After ALL tasks complete, run in order:

```bash
# 1. Lint
ruff check scanner src tests

# 2. Format check
python -m black --check scanner src tests

# 3. Tests
python -m pytest tests/ -v

# 4. Smoke test
python scanner/run_scan.py --repo "."
```

Fix ANY failures. Re-run until ALL pass.

## Success Criteria
- [ ] AI review is disabled by default.
- [ ] Default scan makes no paid API calls, no hosted AI calls, and no network calls for AI review.
- [ ] Default scan returns a normalized `info` finding explaining AI review is disabled.
- [ ] User-configured local command provider can emit JSON findings that normalize into `scanner.models.Finding`.
- [ ] AI review parser accepts both JSON list and `{ "findings": [...] }` shapes.
- [ ] AI review records preserve the existing normalized finding schema and default missing patch fields to empty strings.
- [ ] Invalid AI review configuration returns a normalized `info` finding and does not fail the scan.
- [ ] Local command failure returns a normalized `info` finding and does not fail the scan.
- [ ] Invalid or missing AI review JSON returns a normalized `info` finding and does not fail the scan.
- [ ] `reports/security_report.json` and `reports/security_report.md` are still generated for disabled, configured, and failed AI review states.
- [ ] Tests cover disabled/default behavior, configured behavior, and failure fallback.
- [ ] README documents setup, PowerShell env vars, local command contract, defaults, and failure fallback.
- [ ] ROADMAP.md marks the Phase 3 AI review boundary item complete with `2026/05/13`.
- [ ] DECISIONS.md records the disabled-by-default local AI review boundary ADR.
- [ ] AGENTS.md and CLAUDE.md remain aligned.
- [ ] No database changes are introduced.
- [ ] No default remote AI provider, endpoint, token, or paid API dependency is introduced.
- [ ] All tests pass.
- [ ] No lint or format errors.

## PRP Quality Checklist
- [x] All referenced local files exist in the project.
- [x] Each task has a validation command.
- [x] Database changes are explicitly marked none.
- [x] Dependencies section filled.
- [x] No unstable external provider docs are required because this PRP defines a provider-agnostic local command boundary.
- [x] Confidence score >= 7.

## Confidence Score: 9/10
