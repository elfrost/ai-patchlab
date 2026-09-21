"""Report generation for AI PatchLab scans."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scanner.coverage import ToolCoverage, coverage_payload
from scanner.models import CONFIDENCES, SEVERITIES, Finding
from scanner.report_markdown import write_markdown_report
from scanner.verdicts import VerdictRecord, verdicts_payload

DEFAULT_TOP_FINDINGS_LIMIT = 5

_SEVERITY_RANK = {severity: index for index, severity in enumerate(SEVERITIES)}
_CONFIDENCE_RANK = {confidence: index for index, confidence in enumerate(CONFIDENCES)}


def filter_by_min_severity(findings: list[Finding], min_severity: str) -> list[Finding]:
    """Drop findings strictly less severe than `min_severity`.

    Severity order (most to least severe): critical, high, medium, low, info.
    Passing `"info"` keeps everything.

    Findings flagged `is_meta` are always kept regardless of the floor. They
    describe the state of the scan itself (tool missing, crash, timeout,
    partial coverage) and are emitted at `info` severity, so any floor above
    `info` would silently turn a failed scan into a clean-looking report.
    They are still excluded from `select_top_findings`.
    """
    if min_severity not in _SEVERITY_RANK:
        raise ValueError(f"Unsupported severity: {min_severity}")
    threshold = _SEVERITY_RANK[min_severity]
    return [
        finding
        for finding in findings
        if finding.is_meta or _SEVERITY_RANK[finding.severity] <= threshold
    ]


def select_top_findings(
    findings: list[Finding],
    limit: int = DEFAULT_TOP_FINDINGS_LIMIT,
) -> list[Finding]:
    """Return up to `limit` findings ranked by severity then confidence.

    Info-level findings are excluded - they are infrastructure signals
    (tool not installed, AI review disabled, etc.) rather than security
    issues worth highlighting at the top of a report.
    """
    interesting = [finding for finding in findings if finding.severity != "info"]
    interesting.sort(
        key=lambda f: (
            _SEVERITY_RANK[f.severity],
            _CONFIDENCE_RANK[f.confidence],
            f.tool,
            f.id,
        )
    )
    return interesting[:limit]


def group_findings_by_severity(findings: list[Finding]) -> dict[str, list[dict[str, Any]]]:
    """Group normalized findings by severity."""
    grouped: dict[str, list[dict[str, Any]]] = {severity: [] for severity in SEVERITIES}
    for finding in findings:
        grouped[finding.severity].append(finding.to_dict())
    return grouped


def build_report(
    repo_path: Path,
    findings: list[Finding],
    coverage: tuple[ToolCoverage, ...] | None = None,
    verdicts: tuple[VerdictRecord, ...] | None = None,
) -> dict[str, Any]:
    """Build the complete JSON report payload.

    Args:
        repo_path: Scanned repository root.
        findings: Findings to report, already filtered.
        coverage: Per-scanner coverage rows from `scanner.coverage`. Omitted
            entirely from the payload when `None`, so callers that do not
            supply it keep their previous output.
        verdicts: Dismissal rows from `scanner.verdicts`. Omitted from the
            payload when `None` or empty.
    """
    grouped = group_findings_by_severity(findings)
    summary = {severity: len(grouped[severity]) for severity in SEVERITIES}
    top = [finding.to_dict() for finding in select_top_findings(findings)]

    report: dict[str, Any] = {
        "repository": str(repo_path.resolve()),
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "top_findings": top,
        "findings_by_severity": grouped,
    }
    if coverage is not None:
        report["coverage"] = coverage_payload(coverage)
    if verdicts:
        report["dismissed"] = verdicts_payload(verdicts)
    return report


def write_json_report(report: dict[str, Any], report_path: Path) -> None:
    """Write the JSON report."""
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def write_reports(
    repo_path: Path,
    findings: list[Finding],
    reports_dir: Path,
    coverage: tuple[ToolCoverage, ...] | None = None,
    verdicts: tuple[VerdictRecord, ...] | None = None,
) -> dict[str, Path]:
    """Create the reports directory and write the JSON, Markdown and coverage reports.

    Args:
        repo_path: Scanned repository root.
        findings: Findings to report, already filtered.
        reports_dir: Directory the reports are written to.
        coverage: Per-scanner coverage rows. When supplied, `coverage.json` is
            written beside the reports and returned under the `"coverage"` key.
        verdicts: Dismissal rows. When non-empty, `verdicts.json` is written
            beside the reports and returned under the `"verdicts"` key.

    Returns:
        Mapping of report kind to written path.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(
        repo_path=repo_path,
        findings=findings,
        coverage=coverage,
        verdicts=verdicts,
    )

    json_path = reports_dir / "security_report.json"
    markdown_path = reports_dir / "security_report.md"
    write_json_report(report, json_path)
    write_markdown_report(report, markdown_path)
    paths = {"json": json_path, "markdown": markdown_path}

    if coverage is not None:
        coverage_path = reports_dir / "coverage.json"
        write_json_report(
            {
                "repository": report["repository"],
                "generated_at": report["generated_at"],
                **report["coverage"],
            },
            coverage_path,
        )
        paths["coverage"] = coverage_path

    if verdicts:
        verdicts_path = reports_dir / "verdicts.json"
        write_json_report(
            {
                "repository": report["repository"],
                "generated_at": report["generated_at"],
                **report["dismissed"],
            },
            verdicts_path,
        )
        paths["verdicts"] = verdicts_path

    return paths


__all__ = [
    "build_report",
    "filter_by_min_severity",
    "group_findings_by_severity",
    "select_top_findings",
    "write_json_report",
    "write_markdown_report",
    "write_reports",
]
