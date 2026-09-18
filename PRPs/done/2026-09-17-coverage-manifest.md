# PRP: Coverage manifest — report what the scan did not look at

## Overview

Promote scan coverage from an `info`-severity finding buried in the list to a first-class
report artifact: `reports/coverage.json` plus a `## Scan Coverage` section in
`security_report.md`, with an explicit `complete` flag and a banner when the scan is
incomplete.

Every ingredient already exists — each adapter emits `is_meta=True` findings for
not-installed, disabled, scan-error, parse-error, partial-coverage and no-manifest states
(ADR-013). What is missing is the reconciliation: today a reader must notice one `info` row
among dozens to learn that Semgrep never ran. This PRP makes that impossible to miss.

Implements the first half of ADR-015 (option C). The second half — deterministic rejection
records — is a separate PRP and is explicitly **out of scope** here.

## Dependencies

- None new. Standard library only (`dataclasses`, `json`, `pathlib`).
- Requires ADR-013 (`Finding.is_meta`) — already shipped.

## Context & References

### MUST READ — Load these into your context

- `DECISIONS.md` → **ADR-015** (this decision), ADR-013 (meta findings), ADR-014 (confidence tiers)
- `scanner/models.py` → `Finding`, `FINDING_FIELDS`, the `is_meta` docstring
- `scanner/scanners/__init__.py` → `SCANNERS` registry (5 entries)
- `scanner/run_scan.py:26-55` → `collect_findings`, then `apply_ignore` (line 52), then `filter_by_min_severity` (line 53), then `write_reports` (line 54)
- `scanner/report.py` → `build_report`, `write_markdown_report`, `write_reports`, `select_top_findings`
- `scanner/confidence.py` → `confidence_for_meta_finding`

### Critical Gotchas

1. **Build coverage from the raw `collect_findings` output — before `apply_ignore`.**
   `--ignore-file` does not yet exempt meta findings (known gotcha, logged in ROADMAP).
   A path pattern matching the repo root can currently suppress a `semgrep-not-installed`
   finding. Deriving coverage upstream of line 52 closes that hole for coverage without
   touching `apply_ignore` itself.
2. **A tool that emits nothing at all must still appear as a row.** That is the entire
   point — "no findings" and "never ran" must not render identically. Absence of a meta
   finding is the positive signal (`ran`), so the tool list cannot be derived from the
   findings alone; it comes from a declared constant guarded by a registry test.
3. **Tool identifiers are not scanner function names and not finding-id prefixes.**
   The five `Finding.tool` values are `semgrep`, `gitleaks`, `trivy`, `dependency-scan`,
   `ai-security-review`. Note that `dependency-scan` emits ids prefixed `pip-audit-*`.
   Key on `Finding.tool`, never on the id prefix.
4. **`ai-review-disabled` is the default state, not a failure.** AI review is
   disabled-by-default by ADR-010. Its status is `not_run`, but it must not on its own
   make every ordinary report read as broken — see the `complete` definition below.
5. Files stay under 300 lines. Put derivation logic in `scanner/coverage.py`, not in the
   report writer; check `scanner/report.py` length before adding to it.

## Architecture

### New Files

- `scanner/coverage.py` — `ToolCoverage` frozen dataclass, `COVERAGE_STATUSES`,
  `EXPECTED_TOOLS`, `build_coverage()`, `is_complete()`. Pure functions over a finding
  list; no I/O, no subprocess.
- `tests/test_coverage.py` — derivation, precedence, registry drift, ignore-immunity,
  and report-rendering tests.

### Modified Files

- `scanner/report.py` — `build_report` accepts and embeds coverage; `write_markdown_report`
  renders the banner and table; `write_reports` writes `coverage.json` and returns its path.
- `scanner/run_scan.py` — build coverage right after `collect_findings`, thread it to
  `write_reports`, print the coverage path.
- `CLAUDE.md` / `AGENTS.md` / `ROADMAP.md` — housekeeping (Task 6).

### Data contract

```python
COVERAGE_STATUSES = ("ran", "partial", "error", "not_run")  # best -> worst


@dataclass(frozen=True)
class ToolCoverage:
    tool: str
    status: str            # one of COVERAGE_STATUSES
    detail: str            # human sentence derived from the meta findings
    meta_finding_ids: tuple[str, ...]
```

Status derivation per tool, **worst status wins** (iterate `COVERAGE_STATUSES` in reverse):

| Meta finding id suffix | Status |
|---|---|
| `-not-installed`, `-disabled` | `not_run` |
| `-scan-error`, `-json-parse-error`, `-command-error` | `error` |
| `-partial-coverage`, `-no-supported-manifest` | `partial` |
| *(no meta finding for this tool)* | `ran` |

`reports/coverage.json`:

```json
{
  "repository": "...",
  "generated_at": "UTC ISO-8601",
  "complete": false,
  "tools": [
    {
      "tool": "semgrep",
      "status": "partial",
      "detail": "...",
      "meta_finding_ids": ["semgrep-partial-coverage"]
    }
  ]
}
```

`complete` is `True` only when every tool is `ran`, **except** that a tool whose sole meta
finding is `ai-review-disabled` does not by itself set `complete: false` — an opt-in
feature left off is a configuration state, not a coverage gap. Record that carve-out in a
comment next to the rule; it is the one judgement call in this module.

## Implementation Plan

### Task 1: `scanner/coverage.py`

Write `ToolCoverage`, `COVERAGE_STATUSES`, `EXPECTED_TOOLS`, and
`build_coverage(findings: list[Finding]) -> tuple[ToolCoverage, ...]`. One row per entry in
`EXPECTED_TOOLS`, in registry order. Google-style docstrings, full type hints.
`build_coverage` must be total: an unknown `Finding.tool` is ignored rather than raising.

### Task 2: Registry drift test

In `tests/test_coverage.py`, assert `EXPECTED_TOOLS` equals the set of `Finding.tool`
values reachable from `SCANNERS`. Run each scanner against an empty temp repo with no
external tools on PATH and collect the tool names from the meta findings they emit. This
test is the guardrail that makes a new scanner adapter fail loudly until it is added to
coverage.

### Task 3: Report integration

- `build_report(repo_path, findings, coverage=None)` → add a `"coverage"` key
  (`{"complete": bool, "tools": [...]}`), omitted entirely when `coverage is None` so
  existing callers and tests are unaffected.
- `write_markdown_report`: when coverage is present and `complete` is `False`, emit a
  one-line blockquote banner immediately after the header —
  `> **Incomplete scan.** 2 of 5 tools did not run fully. See Scan Coverage below.`
  Then Top Findings (unchanged), then a `## Scan Coverage` table before the grouped
  findings.
- `write_reports(..., coverage=None)` → write `reports/coverage.json` when coverage is
  present, and add `"coverage"` to the returned path dict.

### Task 4: Wire `run_scan.py`

Build coverage from the output of `collect_findings` **before** `apply_ignore`. Pass it to
`write_reports`. Print `Coverage report: <path>` alongside the existing two lines.

### Task 5: Tests

`tests/test_coverage.py` covers:

1. Each status derivation from a synthetic finding list.
2. Worst-status-wins when a tool emits two meta findings of different classes.
3. A tool with zero findings renders `ran`, not missing.
4. `complete` is `False` when Semgrep is not installed; `True` when the only meta finding
   is `ai-review-disabled`.
5. **Ignore-immunity:** an ignore pattern matching the repo root does not remove the
   `semgrep-not-installed` row from coverage.
6. Markdown contains the banner when incomplete and does not when complete.
7. `coverage.json` is written, parses, and its keys match the contract.

### Task 6: Housekeeping

Update `ROADMAP.md` (mark the item done with date), the Key Directories and Scanner
adapter contract sections of `CLAUDE.md`, and the matching sections of `AGENTS.md`. Flip
ADR-015 `Status:` from `proposed` to `accepted`. Move this PRP to `PRPs/done/`.

## Final Validation Loop

```bash
# 1. Lint
.venv/Scripts/ruff.exe check scanner src/ tests/ fingerprint/

# 2. Format check
.venv/Scripts/python.exe -m black --check scanner src/ tests/ fingerprint/

# 3. Tests
.venv/Scripts/python.exe -m pytest tests/ -v

# 4. Smoke test — self-scan, then confirm the artifact exists and is honest
.venv/Scripts/python.exe scanner/run_scan.py --repo "." --reports-dir reports
cat reports/coverage.json
```

## Success Criteria

- [ ] `reports/coverage.json` is written on every scan, with one row per registered scanner
- [ ] A scan where Semgrep is missing renders a banner and `"complete": false`
- [ ] A scan where every tool ran renders no banner and `"complete": true`
- [ ] An `--ignore-file` pattern cannot remove a row from coverage
- [ ] Adding a scanner to `SCANNERS` without updating `EXPECTED_TOOLS` fails a test
- [ ] `scanner/report.py` and `scanner/coverage.py` are both under 300 lines
- [ ] Full lint + format + test suite green on Python 3.11 and 3.13
- [ ] No new dependency added

## PRP Quality Checklist

- [x] Decision recorded in an ADR before implementation (ADR-015)
- [x] Known gotchas named with the field incident behind each
- [x] Scope explicitly bounded (rejection records deferred to a second PRP)
- [x] Every new behaviour has a matching test in the plan
- [x] Housekeeping task included

## Confidence Score: 8/10

The derivation is mechanical and the raw material already exists, which is why this is
high. The point deducted is the `complete` carve-out for `ai-review-disabled` — it is a
judgement call, and if the report ends up reading as "incomplete" on every ordinary scan
the flag will be ignored within a week. Validate that on the self-scan before accepting.
