"""Markdown rendering for AI PatchLab scan reports.

Split out of `scanner.report` to keep both modules under the project's
300-line ceiling. `scanner.report` owns filtering, the JSON payload and the
write entry point; this module owns how that payload reads on a page.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scanner.models import FINDING_FIELDS, SEVERITIES


def write_markdown_report(report: dict[str, Any], report_path: Path) -> None:
    """Write a human-readable Markdown report."""
    lines = [
        "# AI PatchLab Security Report",
        "",
        f"Repository: `{report['repository']}`",
        f"Generated at: `{report['generated_at']}`",
        "",
    ]

    coverage = report.get("coverage")
    if coverage and not coverage["complete"]:
        lines.extend(
            [
                f"> **Incomplete scan.** {coverage['incomplete_tool_count']} of "
                f"{coverage['tool_count']} tools did not examine what they were pointed at. "
                "A low finding count below does not mean this repository is clean - "
                "see Scan Coverage.",
                "",
            ]
        )

    lines.extend(
        [
            "## Summary",
            "",
            "| Severity | Findings |",
            "| --- | ---: |",
        ]
    )

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

    if coverage:
        lines.extend(
            [
                "## Scan Coverage",
                "",
                "One row per configured scanner. A tool that did not run reports "
                "nothing, which is indistinguishable from a clean result unless it "
                "is stated here.",
                "",
                "| Tool | Status | Detail |",
                "| --- | --- | --- |",
            ]
        )
        for row in coverage["tools"]:
            lines.append(f"| `{row['tool']}` | `{row['status']}` | {row['detail']} |")
        lines.append("")

    dismissed = report.get("dismissed")
    if dismissed:
        by_reason = ", ".join(
            f"{reason} ({count})" for reason, count in dismissed["by_reason"].items()
        )
        lines.extend(
            [
                "## Dismissed",
                "",
                f"{dismissed['total_dismissed']} findings were removed before this report: "
                f"{by_reason}. They are listed by rule family so a suppression cannot "
                "quietly shrink the numbers above.",
                "",
                "| Source | Reason | Tool | Rule | Count |",
                "| --- | --- | --- | --- | ---: |",
            ]
        )
        for row in dismissed["records"]:
            lines.append(
                f"| `{row['source']}` | `{row['reason_code']}` | `{row['tool']}` "
                f"| {row['rule']} | {row['count']} |"
            )
        lines.append("")

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
