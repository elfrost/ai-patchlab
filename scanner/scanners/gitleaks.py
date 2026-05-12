"""Gitleaks scanner integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scanner.models import Finding
from scanner.recommendations import enrich_findings
from scanner.remediation import apply_patch_suggestions
from scanner.tools.gitleaks_runner import run_gitleaks


def scan_gitleaks(repo_path: Path, reports_dir: Path) -> list[Finding]:
    """Run Gitleaks and map JSON findings into the normalized schema."""
    raw_report_path = reports_dir / "raw" / "gitleaks.json"
    result = run_gitleaks(repo_path=repo_path, raw_report_path=raw_report_path)

    if not result.installed:
        return [
            Finding(
                id="gitleaks-not-installed",
                tool="gitleaks",
                severity="info",
                title="Gitleaks is not installed",
                description="Gitleaks was not found on PATH, so secret scanning was skipped.",
                file=str(repo_path),
                line=None,
                recommendation="Install Gitleaks and re-run the scan from PowerShell.",
                confidence="high",
            )
        ]

    if result.returncode not in {0, 1}:
        return [
            Finding(
                id="gitleaks-scan-error",
                tool="gitleaks",
                severity="info",
                title="Gitleaks scan did not complete successfully",
                description=_format_scan_error(result.stderr or result.stdout),
                file=str(repo_path),
                line=None,
                recommendation="Review the Gitleaks error output, fix the scanner setup, and re-run the scan.",
                confidence="medium",
            )
        ]

    try:
        records = _read_gitleaks_records(raw_report_path)
    except json.JSONDecodeError:
        return [
            Finding(
                id="gitleaks-json-parse-error",
                tool="gitleaks",
                severity="info",
                title="Gitleaks JSON output could not be parsed",
                description=f"The raw Gitleaks report at {raw_report_path} is not valid JSON.",
                file=str(repo_path),
                line=None,
                recommendation="Re-run Gitleaks and inspect the raw JSON report for truncation or invalid output.",
                confidence="medium",
            )
        ]

    return apply_patch_suggestions(
        enrich_findings([_map_gitleaks_finding(record) for record in records])
    )


def _read_gitleaks_records(raw_report_path: Path) -> list[dict[str, Any]]:
    """Read Gitleaks JSON records from disk."""
    if not raw_report_path.exists():
        return []

    raw_text = raw_report_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return []

    data = json.loads(raw_text)
    if isinstance(data, list):
        return [record for record in data if isinstance(record, dict)]
    if isinstance(data, dict):
        findings = data.get("findings") or data.get("Findings") or data.get("results") or []
        if isinstance(findings, list):
            return [record for record in findings if isinstance(record, dict)]
    return []


def _map_gitleaks_finding(record: dict[str, Any]) -> Finding:
    """Map one Gitleaks JSON finding to the AI PatchLab schema."""
    rule_id = _get_string(record, "RuleID", "RuleId", "rule_id", default="secret")
    file_path = _get_string(record, "File", "file", default="")
    line = _get_int(record, "StartLine", "Line", "line")
    fingerprint = _get_string(record, "Fingerprint", "fingerprint", default="")
    finding_id = fingerprint or f"gitleaks-{rule_id}-{file_path}-{line or 0}"
    description = _get_string(
        record,
        "Description",
        "description",
        default="Gitleaks detected a potential secret.",
    )

    return Finding(
        id=finding_id,
        tool="gitleaks",
        severity="high",
        title=f"Potential secret detected: {rule_id}",
        description=description,
        file=file_path,
        line=line,
        recommendation="Rotate the exposed secret, remove it from the repository, and rewrite git history if the secret was committed.",
        confidence="high",
    )


def _get_string(record: dict[str, Any], *keys: str, default: str) -> str:
    """Return the first non-empty string value for the given keys."""
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return default


def _get_int(record: dict[str, Any], *keys: str) -> int | None:
    """Return the first integer value for the given keys."""
    for key in keys:
        value = record.get(key)
        if value in {None, ""}:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _format_scan_error(output: str) -> str:
    """Keep scanner error text short enough for the report."""
    output = output.strip()
    if not output:
        return "Gitleaks returned an error without additional output."
    return output[:500]
