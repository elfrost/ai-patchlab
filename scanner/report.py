"""Report generation for AI PatchLab scans."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scanner.models import FINDING_FIELDS, SEVERITIES, Finding


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

    return {
        "repository": str(repo_path.resolve()),
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
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

    lines.extend(["", "## Findings", ""])

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
