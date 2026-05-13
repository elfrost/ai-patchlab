# PRP: Trivy Filesystem Scanner Integration

## Overview
Replace the current Trivy placeholder with a real local Trivy CLI integration. The scanner must run Trivy against the requested repository path, save the raw JSON report under `reports/raw/trivy.json`, parse vulnerability and misconfiguration findings, normalize them into `scanner.models.Finding`, and preserve the existing partial-report behavior when Trivy is missing or fails.

The implementation should stay local-first and PowerShell-friendly. Do not bundle Trivy, do not add paid APIs, and do not introduce a web app or database persistence.

## Dependencies
- Requires: Semgrep and Gitleaks scanner integration patterns already present in the repo.
- Blocks: Dependency scan execution can reuse parts of the Trivy parser later, but is not required for this PRP.

## Context & References

### MUST READ - Load these into your context
- file: `AGENTS.md` - why: Codex workflow, roadmap/doc sync, and scanner directory conventions.
- file: `CLAUDE.md` - why: runtime parity and Python coding standards.
- file: `ROADMAP.md` - why: Phase 2 has the open item `Add Trivy execution and result parsing`.
- file: `DECISIONS.md` - why: ADR-003, ADR-004, and ADR-005 define the scanner adapter pattern and CLI integration approach.
- file: `INITIAL.md` - why: normalized finding schema, CLI constraints, and no-paid-API MVP boundary.
- file: `README.md` - why: scanner setup docs must be updated with Trivy usage and raw report output.
- file: `scanner/scanners/trivy.py` - why: placeholder to replace.
- file: `scanner/scanners/semgrep.py` - why: reference for missing-tool, raw JSON parse, severity mapping, and scan-error findings.
- file: `scanner/scanners/gitleaks.py` - why: reference for CLI result parsing, fallback info finding, and JSON reader tolerance.
- file: `scanner/tools/semgrep_runner.py` - why: reference for process runner dataclass and Windows PATH handling.
- file: `scanner/tools/gitleaks_runner.py` - why: reference for process runner command capture and fallback executable lookup.
- file: `scanner/scanners/__init__.py` - why: scanner registry already includes `scan_trivy`.
- file: `scanner/models.py` - why: `Finding` schema, severity values, and confidence values.
- file: `scanner/report.py` - why: generated report structure and normalized field rendering.
- file: `tests/test_semgrep_scanner.py` - why: test style for scanner adapter and process runner.
- file: `tests/test_gitleaks_scanner.py` - why: test style for external CLI command construction.
- file: `examples/service_pattern.py` - why: local service pattern guidance; keep the runner/adapter responsibilities separated.
- url: `https://trivy.dev/docs/latest/target/filesystem/` - why: official Trivy filesystem target docs; `trivy fs` scans local projects and can scan vulnerabilities, misconfigurations, secrets, and licenses.
- url: `https://trivy.dev/docs/latest/references/configuration/cli/trivy_filesystem/` - why: official CLI flags for `trivy filesystem`, including `--format`, `--output`, `--scanners`, `--severity`, and `--no-progress`.
- url: `https://trivy.dev/docs/latest/configuration/reporting/` - why: official JSON report shape with `Results[].Vulnerabilities[]`, `Target`, `Class`, and `Type`.
- url: `https://trivy.dev/docs/latest/configuration/others/` - why: official scanner selection and exit-code behavior.

### Critical Gotchas
- CRITICAL: Use the local Trivy executable only. Do not add a Python package dependency for Trivy and do not download binaries in code.
- CRITICAL: Run Trivy in filesystem mode: `trivy fs`, not image mode.
- CRITICAL: Use `--scanners vuln,misconfig` for the first integration. Gitleaks already owns secret scanning, and license scanning is out of scope for this PRP.
- CRITICAL: Do not pass `--exit-code 1`; by default Trivy exits `0` even when findings exist, which is better for report generation.
- CRITICAL: Trivy can update vulnerability databases on first run and may need network access. Tests must mock `subprocess.run`; do not require Trivy to be installed in unit tests.
- CRITICAL: The current top-level scanner orchestration does not catch arbitrary scanner exceptions. Keep Trivy adapter errors converted into `info` findings rather than raising.
- CRITICAL: Keep raw report parsing tolerant. Trivy JSON can contain top-level `Results`, and each result may have `Vulnerabilities`, `Misconfigurations`, `Secrets`, or `Licenses`; this PRP should only normalize vulnerabilities and misconfigurations.
- CRITICAL: Preserve normalized schema fields: `id`, `tool`, `severity`, `title`, `description`, `file`, `line`, `recommendation`, `confidence`, `patch_before`, `patch_after`, `remediation_explanation`.

## Architecture

### New Files
| File | Purpose |
|------|---------|
| `scanner/tools/trivy_runner.py` | Locate and execute the local Trivy CLI, write raw JSON to `reports/raw/trivy.json`, and return a typed result object. |
| `tests/test_trivy_scanner.py` | Unit tests for missing Trivy, command construction, JSON parsing, invalid JSON handling, vulnerability mapping, and misconfiguration mapping. |

### Modified Files
| File | Changes |
|------|---------|
| `scanner/scanners/trivy.py` | Replace placeholder with real Trivy adapter and mapping helpers. |
| `README.md` | Add Trivy setup, command, raw report output, and normalized severity behavior. |
| `ROADMAP.md` | Mark `Add Trivy execution and result parsing` done with `2026/05/12` after implementation passes validation. |
| `DECISIONS.md` | Add a new ADR for Trivy CLI integration if the final design follows the external-CLI adapter pattern. |
| `AGENTS.md` | Update scanner directory description if Trivy is no longer a placeholder. |
| `CLAUDE.md` | Mirror the same structural scanner description update for runtime parity. |

### Database Changes
None.

## Implementation Plan

### Task 1: Add Trivy CLI Runner
**Goal:** Execute local Trivy with JSON output while keeping command construction testable.
**Files:** `scanner/tools/trivy_runner.py`, `tests/test_trivy_scanner.py`
**Pattern:** Follow `scanner/tools/gitleaks_runner.py` and `scanner/tools/semgrep_runner.py`.
**Details:**
- Create a frozen dataclass `TrivyResult` with fields: `installed`, `raw_report_path`, `returncode`, `stdout`, `stderr`.
- Add a `completed` property matching the existing runner pattern.
- Add `find_trivy_executable()` that checks `shutil.which("trivy")` first.
- Optionally add a conservative Windows fallback path only if it is stable and testable; otherwise keep PATH-only lookup for MVP.
- Add `run_trivy(repo_path: Path, raw_report_path: Path) -> TrivyResult`.
- Ensure `raw_report_path.parent.mkdir(parents=True, exist_ok=True)`.
- Use this command shape:

```powershell
trivy fs --format json --output "reports\raw\trivy.json" --scanners vuln,misconfig --no-progress --skip-version-check "C:\path\to\repo"
```

- Use `capture_output=True`, `text=True`, `encoding="utf-8"`, `errors="replace"`, and `check=False`.
- If `subprocess.run` raises `OSError`, write a minimal empty JSON report and return `returncode=127` with the exception text in `stderr`.
- If Trivy completes but does not create the raw report, write a minimal empty JSON object: `{"Results": []}`.

**Validation:**
```bash
python -m pytest tests/test_trivy_scanner.py -v -k "runner"
```

### Task 2: Replace Trivy Placeholder With Adapter
**Goal:** Convert Trivy runner output into normalized findings.
**Files:** `scanner/scanners/trivy.py`, `tests/test_trivy_scanner.py`
**Pattern:** Follow `scanner/scanners/semgrep.py` for error handling and JSON reader structure.
**Details:**
- Import `run_trivy` and `TrivyResult` from `scanner.tools.trivy_runner`.
- Set `raw_report_path = reports_dir / "raw" / "trivy.json"`.
- If Trivy is missing, return one `info` finding:
  - `id="trivy-not-installed"`
  - `tool="trivy"`
  - `severity="info"`
  - `title="Trivy is not installed"`
  - `confidence="high"`
  - recommendation asks the user to install Trivy and re-run from PowerShell.
- If return code is non-zero and raw JSON cannot be parsed into findings, return one `info` scanner-error finding.
- If raw JSON parses successfully, normalize supported findings even if `returncode` is non-zero.
- Implement `_read_trivy_results(raw_report_path: Path) -> list[dict[str, Any]]`.
- Catch `json.JSONDecodeError` and return one `trivy-json-parse-error` finding.

**Validation:**
```bash
python -m pytest tests/test_trivy_scanner.py -v -k "missing or parse or error"
```

### Task 3: Map Trivy Vulnerabilities
**Goal:** Normalize `Results[].Vulnerabilities[]` records.
**Files:** `scanner/scanners/trivy.py`, `tests/test_trivy_scanner.py`
**Details:**
- Map Trivy severity values:
  - `CRITICAL` -> `critical`
  - `HIGH` -> `high`
  - `MEDIUM` -> `medium`
  - `LOW` -> `low`
  - `UNKNOWN` or missing -> `info`
- For each vulnerability, build a `Finding`:
  - `id`: stable string from `VulnerabilityID`, package name, target, and installed version.
  - `tool`: `trivy`
  - `title`: prefer `Title`, fallback to `VulnerabilityID`.
  - `description`: prefer `Description`, fallback to package/version summary.
  - `file`: use parent result `Target`.
  - `line`: `None`.
  - `recommendation`: include fixed version when present, otherwise say to review the advisory and upgrade/remove/mitigate the affected package.
  - `confidence`: `high` for CVE vulnerabilities with `VulnerabilityID`, otherwise `medium`.
- Include package context in description or recommendation: `PkgName`, `InstalledVersion`, `FixedVersion`, `PrimaryURL` when present.
- Run results through `enrich_findings()` and `apply_patch_suggestions()` to preserve existing enrichment behavior.

**Validation:**
```bash
python -m pytest tests/test_trivy_scanner.py -v -k "vulnerability"
```

### Task 4: Map Trivy Misconfigurations
**Goal:** Normalize `Results[].Misconfigurations[]` records.
**Files:** `scanner/scanners/trivy.py`, `tests/test_trivy_scanner.py`
**Details:**
- Parse `Misconfigurations` arrays from each result.
- Map severity using the same Trivy severity map as vulnerabilities.
- For each misconfiguration, build a `Finding`:
  - `id`: stable string from `ID` or `AVDID`, target, and line number.
  - `tool`: `trivy`
  - `title`: prefer `Title`, fallback to `ID` or `AVDID`.
  - `description`: prefer `Description`, fallback to `Message`.
  - `file`: prefer `CauseMetadata.Resource` if path-like and meaningful; fallback to parent `Target`.
  - `line`: prefer `CauseMetadata.StartLine`, fallback to `CauseMetadata.EndLine`, else `None`.
  - `recommendation`: prefer `Resolution`, fallback to `Message`, else generic IaC/Dockerfile remediation guidance.
  - `confidence`: `medium` by default.
- Keep the mapper resilient to missing nested `CauseMetadata`.

**Validation:**
```bash
python -m pytest tests/test_trivy_scanner.py -v -k "misconfiguration"
```

### Task 5: Update Docs and Shared Project State
**Goal:** Keep runtime docs and roadmap aligned after implementation.
**Files:** `README.md`, `ROADMAP.md`, `DECISIONS.md`, `AGENTS.md`, `CLAUDE.md`
**Details:**
- README:
  - Add `reports/raw/trivy.json` to generated outputs.
  - Add a `Trivy Setup` section with install/verify guidance and the exact command AI PatchLab runs.
  - Update `Current Scanner Foundation` to say Trivy is real, not placeholder.
- ROADMAP:
  - Mark `Add Trivy execution and result parsing` as `[x] ... (2026/05/12)`.
- DECISIONS:
  - Add ADR-008 for Trivy CLI filesystem integration if no equivalent ADR already exists.
- AGENTS.md and CLAUDE.md:
  - Update `scanner/scanners/` and `scanner/tools/` descriptions to mention Trivy alongside Semgrep and Gitleaks.

**Validation:**
```bash
rg "Trivy" README.md ROADMAP.md DECISIONS.md AGENTS.md CLAUDE.md
```

### Task 6: Full Validation
**Goal:** Verify the complete scanner still behaves consistently.
**Files:** all changed files.
**Details:**
- Run formatter if needed.
- Run the full validation loop below.
- Optionally run a smoke scan against `.` if Trivy is installed locally; if not installed, verify the report contains `trivy-not-installed` and still completes.

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
- [x] `scanner/tools/trivy_runner.py` executes local Trivy with JSON output to `reports/raw/trivy.json`.
- [x] Missing Trivy returns a normalized `info` finding and does not fail the full scan.
- [x] Trivy vulnerabilities from `Results[].Vulnerabilities[]` normalize into the project `Finding` schema.
- [x] Trivy misconfigurations from `Results[].Misconfigurations[]` normalize into the project `Finding` schema.
- [x] Invalid or missing Trivy JSON returns a clear normalized scanner-error finding.
- [x] The main scanner continues to generate `reports/security_report.json` and `reports/security_report.md`.
- [x] Unit tests cover runner command construction, missing executable behavior, vulnerability parsing, misconfiguration parsing, invalid JSON, and scan error behavior.
- [x] README documents Trivy setup and raw report output.
- [x] ROADMAP.md marks the Trivy integration item complete with `2026-05-12`.
- [x] DECISIONS.md records the Trivy CLI integration decision if implemented.
- [x] AGENTS.md and CLAUDE.md remain aligned for scanner directories and tool integration descriptions.
- [x] No database changes are introduced.
- [x] All tests pass.
- [x] No lint or format errors.

## PRP Quality Checklist
- [x] All referenced local files exist in the project.
- [x] Each task has a validation command.
- [x] Database changes are explicitly marked none.
- [x] Dependencies section filled.
- [x] External docs are official Trivy documentation URLs.
- [x] Confidence score >= 7.

## Confidence Score: 9/10
