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
from scanner.recommendations import enrich_findings
from scanner.remediation import apply_patch_suggestions
from scanner.tools.semgrep_runner import run_semgrep

SEMGREP_SEVERITY_MAP = {
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
}


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
            )
        ]

    if result.returncode not in {0, 1}:
        return [
            Finding(
                id="semgrep-scan-error",
                tool="semgrep",
                severity="info",
                title="Semgrep scan did not complete successfully",
                description=_format_scan_error(result.stderr or result.stdout),
                file=str(repo_path),
                line=None,
                recommendation="Review the Semgrep error output, fix the scanner setup, and re-run the scan.",
                confidence=confidence_for_meta_finding("scan-error"),
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
            )
        ]

    return apply_patch_suggestions(
        enrich_findings([_map_semgrep_finding(record) for record in records])
    )


def _read_semgrep_records(raw_report_path: Path) -> list[dict[str, Any]]:
    """Read Semgrep JSON records from disk."""
    if not raw_report_path.exists():
        return []

    raw_text = raw_report_path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw_text:
        return []

    data = json.loads(raw_text)
    if isinstance(data, dict):
        results = data.get("results") or []
        if isinstance(results, list):
            return [record for record in results if isinstance(record, dict)]
    return []


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
        confidence=confidence_for_semgrep_finding(),
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
