"""Semgrep scanner integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scanner.confidence import (
    confidence_for_meta_finding,
    confidence_for_semgrep_finding,
)
from scanner.models import Finding
from scanner.paths import rebase_finding_path
from scanner.recommendations import enrich_findings
from scanner.remediation import apply_patch_suggestions
from scanner.tools.semgrep_runner import run_semgrep

SEMGREP_SEVERITY_MAP = {
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
}

# Cap on how many `rule -> file` pairs a coverage finding lists before it is
# truncated. Keeps the report readable on runs with hundreds of errors.
MAX_COVERAGE_PAIRS = 20


def scan_semgrep(repo_path: Path, reports_dir: Path) -> list[Finding]:
    """Run Semgrep and map JSON findings into the normalized schema."""
    raw_report_path = reports_dir / "raw" / "semgrep.json"
    result = run_semgrep(repo_path=repo_path, raw_report_path=raw_report_path)

    if not result.installed:
        return [
            Finding(
                id="semgrep-not-installed",
                tool="semgrep",
                severity="info",
                title="Semgrep is not installed",
                description="Semgrep was not found on PATH, so static security scanning was skipped.",
                file=str(repo_path),
                line=None,
                recommendation="Install Semgrep and re-run the scan from PowerShell.",
                confidence=confidence_for_meta_finding("not-installed"),
                is_meta=True,
            )
        ]

    raw_text = ""
    if raw_report_path.exists():
        raw_text = raw_report_path.read_text(encoding="utf-8", errors="replace").strip()

    # An empty/0-byte report is never a valid Semgrep result: even a scan with
    # no findings writes `{"results": []}`. An empty file means Semgrep died
    # mid-write (e.g. a UnicodeEncodeError on non-UTF-8 host locales). Treat it
    # as a scan error rather than silently reporting zero findings — a non-zero
    # returncode OR an empty report both indicate the scan did not complete.
    if result.returncode not in {0, 1} or not raw_text:
        return [
            Finding(
                id="semgrep-scan-error",
                tool="semgrep",
                severity="info",
                title="Semgrep scan did not complete successfully",
                description=_format_scan_error(
                    result.stderr
                    or result.stdout
                    or "Semgrep produced an empty report (the scan likely crashed mid-write)."
                ),
                file=str(repo_path),
                line=None,
                recommendation="Review the Semgrep error output, fix the scanner setup, and re-run the scan.",
                confidence=confidence_for_meta_finding("scan-error"),
                is_meta=True,
            )
        ]

    try:
        records = _read_semgrep_records(raw_report_path)
    except json.JSONDecodeError:
        return [
            Finding(
                id="semgrep-json-parse-error",
                tool="semgrep",
                severity="info",
                title="Semgrep JSON output could not be parsed",
                description=f"The raw Semgrep report at {raw_report_path} is not valid JSON.",
                file=str(repo_path),
                line=None,
                recommendation="Re-run Semgrep and inspect the raw JSON report for truncation or invalid output.",
                confidence=confidence_for_meta_finding("json-parse-error"),
                is_meta=True,
            )
        ]

    findings = apply_patch_suggestions(
        enrich_findings([_map_semgrep_finding(record) for record in records])
    )

    coverage = _coverage_finding(_read_semgrep_errors(raw_report_path), repo_path)
    if coverage is not None:
        findings.append(coverage)
    return findings


def _read_semgrep_payload(raw_report_path: Path) -> dict[str, Any]:
    """Read the full Semgrep JSON payload from disk."""
    if not raw_report_path.exists():
        return {}

    raw_text = raw_report_path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw_text:
        return {}

    data = json.loads(raw_text)
    return data if isinstance(data, dict) else {}


def _read_semgrep_records(raw_report_path: Path) -> list[dict[str, Any]]:
    """Read Semgrep JSON records from disk."""
    results = _read_semgrep_payload(raw_report_path).get("results") or []
    if isinstance(results, list):
        return [record for record in results if isinstance(record, dict)]
    return []


def _read_semgrep_errors(raw_report_path: Path) -> list[dict[str, Any]]:
    """Read the Semgrep `errors` array from disk.

    `errors` - not `paths.skipped` - is where a rule that failed to run on a
    file shows up. Across the scan series `paths.skipped` has been empty on
    every run where rules timed out, so reading only `skipped` reports a scan
    with real coverage gaps as a complete one.
    """
    try:
        errors = _read_semgrep_payload(raw_report_path).get("errors") or []
    except json.JSONDecodeError:
        return []
    if isinstance(errors, list):
        return [record for record in errors if isinstance(record, dict)]
    return []


def _coverage_finding(errors: list[dict[str, Any]], repo_path: Path) -> Finding | None:
    """Build a partial-coverage finding when Semgrep reported per-file errors.

    A timeout means the rule never ran on that file. The (rule, file) pair is
    the actionable part: it names exactly which check was not performed where,
    so curation knows what still needs a hand review.
    """
    if not errors:
        return None

    timeouts = [error for error in errors if "timeout" in _error_type(error).lower()]
    other = [error for error in errors if error not in timeouts]

    lines = [
        f"Semgrep reported {len(errors)} error(s) while scanning, "
        f"of which {len(timeouts)} were rule timeouts. "
        "A timed-out rule did not run on that file, so its absence from the "
        "results is not evidence that the file is clean."
    ]
    if timeouts:
        lines.append("")
        lines.append("Rules that did not complete (rule -> file):")
        lines.extend(f"- {pair}" for pair in _summarize_pairs(timeouts, repo_path))
    if other:
        lines.append("")
        lines.append("Other scan errors (type -> file):")
        lines.extend(f"- {pair}" for pair in _summarize_pairs(other, repo_path, use_type=True))

    return Finding(
        id="semgrep-partial-coverage",
        tool="semgrep",
        severity="info",
        title="Semgrep did not cover every file it was pointed at",
        description=_strip_scan_root("\n".join(lines), repo_path),
        file=str(repo_path),
        line=None,
        recommendation=(
            "Hand-review the files listed above for the rules that timed out, or re-run "
            "Semgrep with a higher --timeout so the missing checks actually execute."
        ),
        confidence=confidence_for_meta_finding("partial-coverage"),
        is_meta=True,
    )


def _strip_scan_root(text: str, repo_path: Path) -> str:
    """Remove the scan root from free text, whatever spelling it arrives in.

    Defence in depth, deliberately kept after the per-field rebasing rather
    than instead of it. Semgrep's error payloads have now leaked an absolute
    path twice through two different shapes, so the description is scrubbed
    once more on the way out: this text is published, and it must never carry
    the operator's filesystem layout off the machine.
    """
    root = str(repo_path)
    if not root:
        return text
    variants = {
        root,
        root.replace("\\", "/"),
        root.replace("\\", "\\\\"),
        str(repo_path.resolve()),
        str(repo_path.resolve()).replace("\\", "/"),
        str(repo_path.resolve()).replace("\\", "\\\\"),
    }
    for variant in sorted(variants, key=len, reverse=True):
        if variant:
            text = text.replace(variant + "\\\\", "").replace(variant + "\\", "")
            text = text.replace(variant + "/", "").replace(variant, "")
    return text


def _summarize_pairs(
    errors: list[dict[str, Any]],
    repo_path: Path,
    *,
    use_type: bool = False,
    limit: int = MAX_COVERAGE_PAIRS,
) -> list[str]:
    """Collapse errors into unique `label -> file` strings, capped for length."""
    pairs: list[str] = []
    for error in errors:
        label = _error_type(error) if use_type else _error_rule(error)
        path = _error_path(error, repo_path)
        pair = f"{label} -> {path}"
        if pair not in pairs:
            pairs.append(pair)

    if len(pairs) > limit:
        hidden = len(pairs) - limit
        return [*pairs[:limit], f"... and {hidden} more"]
    return pairs


def _error_type(error: dict[str, Any]) -> str:
    """Return the Semgrep error type name.

    Semgrep does not always give `type` as a plain string. `PartialParsing`
    arrives as `["PartialParsing", [{"path": ..., "start": ...}, ...]]`, and
    stringifying the whole value drags absolute file paths into a description
    that gets published. Only the leading name is ever wanted here; the file is
    reported separately by `_error_path`.
    """
    for key in ("type", "error_type", "level"):
        value = error.get(key)
        while isinstance(value, (list, tuple)) and value:
            value = value[0]
        if value is not None and str(value).strip():
            return str(value)
    return "error"


def _error_rule(error: dict[str, Any]) -> str:
    """Return the rule id an error belongs to."""
    return _get_string(error, "rule_id", "ruleId", "check_id", default="unknown-rule")


def _error_path(error: dict[str, Any], repo_path: Path) -> str:
    """Return the repo-relative file an error applies to.

    Semgrep reports absolute paths, and when the scan target is a temp clone
    those embed the local user directory. This description is published, so the
    path is rebased the same way `Finding.file` is - a report must never carry
    the operator's filesystem layout off the machine.
    """
    path = _get_string(error, "path", "file", default="")
    if not path:
        location = error.get("location")
        if isinstance(location, dict):
            path = _get_string(location, "path", "file", default="")
    if not path:
        return "unknown-file"
    return rebase_finding_path(path, repo_path)


def _map_semgrep_finding(record: dict[str, Any]) -> Finding:
    """Map one Semgrep JSON finding to the AI PatchLab schema."""
    check_id = _get_string(record, "check_id", "checkId", default="semgrep-finding")
    extra = record.get("extra")
    if not isinstance(extra, dict):
        extra = {}

    raw_severity = _get_string(extra, "severity", default="INFO").upper()
    message = _get_string(extra, "message", default="Semgrep detected a security issue.")
    file_path = _get_string(record, "path", default="")
    line = _get_line(record)

    return Finding(
        id=f"semgrep-{check_id}-{file_path}-{line or 0}",
        tool="semgrep",
        severity=SEMGREP_SEVERITY_MAP.get(raw_severity, "low"),
        title=check_id,
        description=message,
        file=file_path,
        line=line,
        recommendation=_get_recommendation(extra),
        confidence=confidence_for_semgrep_finding(check_id),
    )


def _get_recommendation(extra: dict[str, Any]) -> str:
    """Extract Semgrep remediation guidance when available."""
    fix = extra.get("fix")
    if fix is not None and str(fix).strip():
        return str(fix)

    metadata = extra.get("metadata")
    if isinstance(metadata, dict):
        remediation = metadata.get("remediation") or metadata.get("fix")
        if remediation is not None and str(remediation).strip():
            return str(remediation)

    return "Review the Semgrep rule guidance and update the affected code."


def _get_line(record: dict[str, Any]) -> int | None:
    """Return the starting line from a Semgrep result."""
    start = record.get("start")
    if isinstance(start, dict):
        line = start.get("line")
        try:
            return int(line)
        except (TypeError, ValueError):
            return None
    return None


def _get_string(record: dict[str, Any], *keys: str, default: str) -> str:
    """Return the first non-empty string value for the given keys."""
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return default


def _format_scan_error(output: str) -> str:
    """Keep scanner error text short enough for the report."""
    output = output.strip()
    if not output:
        return "Semgrep returned an error without additional output."
    return output[:500]
