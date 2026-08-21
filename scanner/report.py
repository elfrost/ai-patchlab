"""Report generation for AI PatchLab scans."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scanner.models import CONFIDENCES, FINDING_FIELDS, SEVERITIES, Finding

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


def build_report(repo_path: Path, findings: list[Finding]) -> dict[str, Any]:
    """Build the complete JSON report payload."""
    grouped = group_findings_by_severity(findings)
    summary = {severity: len(grouped[severity]) for severity in SEVERITIES}
    top = [finding.to_dict() for finding in select_top_findings(findings)]

    return {
        "repository": str(repo_path.resolve()),
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "top_findings": top,
        "findings_by_severity": grouped,
    }


def write_json_report(report: dict[str, Any], report_path: Path) -> None:
    """Write the JSON report."""
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def write_markdown_report(report: dict[str, Any], report_path: Path) -> None:
    """Write a human-readable Markdown report."""
    lines = [
        "# AI PatchLab Security Report",
        "",
        f"Repository: `{report['repository']}`",
        f"Generated at: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        "| Severity | Findings |",
        "| --- | ---: |",
    ]

    for severity in SEVERITIES:
        lines.append(f"| {severity.title()} | {report['summary'][severity]} |")

    lines.extend(["", "## Top Findings", ""])
    top_findings = report.get("top_findings", [])
    if not top_findings:
        lines.extend(["No findings of interest.", ""])
    else:
        for index, finding in enumerate(top_findings, start=1):
            line_value = finding["line"] if finding["line"] is not None else "N/A"
            lines.extend(
                [
                    f"{index}. **{finding['title']}**",
                    f"   - Severity: `{finding['severity']}`  Confidence: `{finding['confidence']}`  Tool: `{finding['tool']}`",
                    f"   - File: `{finding['file']}:{line_value}`",
                    f"   - {finding['recommendation']}",
                    "",
                ]
            )

    lines.extend(["## Findings", ""])

    for severity in SEVERITIES:
        lines.extend([f"### {severity.title()}", ""])
        findings = report["findings_by_severity"][severity]
        if not findings:
            lines.extend(["No findings.", ""])
            continue

        for finding in findings:
            line = finding["line"] if finding["line"] is not None else "N/A"
            lines.extend(
                [
                    f"#### {finding['title']}",
                    "",
                    f"- ID: `{finding['id']}`",
                    f"- Tool: `{finding['tool']}`",
                    f"- File: `{finding['file']}`",
                    f"- Line: `{line}`",
                    f"- Confidence: `{finding['confidence']}`",
                    f"- Description: {finding['description']}",
                    f"- Recommendation: {finding['recommendation']}",
                ]
            )
            if _has_patch_suggestion(finding):
                lines.extend(
                    [
                        "- Patch suggestion:",
                        "",
                        "  Before:",
                        "",
                        "  ```text",
                        _indent_code_block(finding["patch_before"]),
                        "  ```",
                        "",
                        "  After:",
                        "",
                        "  ```text",
                        _indent_code_block(finding["patch_after"]),
                        "  ```",
                        "",
                        f"- Remediation explanation: {finding['remediation_explanation']}",
                    ]
                )
            lines.append("")

    lines.extend(
        [
            "## Normalized Finding Fields",
            "",
            ", ".join(f"`{field}`" for field in FINDING_FIELDS),
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _has_patch_suggestion(finding: dict[str, Any]) -> bool:
    """Return true when a finding includes deterministic patch guidance."""
    return bool(
        finding.get("patch_before")
        or finding.get("patch_after")
        or finding.get("remediation_explanation")
    )


def _indent_code_block(value: str) -> str:
    """Indent multi-line patch examples inside Markdown list code fences."""
    return "\n".join(f"  {line}" for line in value.splitlines())


def write_reports(repo_path: Path, findings: list[Finding], reports_dir: Path) -> dict[str, Path]:
    """Create the reports directory and write JSON plus Markdown reports."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(repo_path=repo_path, findings=findings)

    json_path = reports_dir / "security_report.json"
    markdown_path = reports_dir / "security_report.md"
    write_json_report(report, json_path)
    write_markdown_report(report, markdown_path)

    return {"json": json_path, "markdown": markdown_path}
