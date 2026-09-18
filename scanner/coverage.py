"""Scan coverage derived from scanner-infrastructure findings.

A finding count only means something next to a statement of what was examined.
Every scanner adapter already emits `is_meta=True` findings when it cannot run,
when it crashes, or when it covered only part of what it was pointed at
(ADR-013). Those signals are rendered at `info` severity among the findings,
where a reader has to notice one row among dozens to learn that Semgrep never
ran.

This module reconciles them into one row per registered scanner so that
"nothing was looked at" can never render identically to "nothing was found"
(ADR-015).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scanner.models import Finding

COVERAGE_STATUSES = ("ran", "partial", "error", "not_run")
"""Coverage states ordered best to worst - later entries win a tie."""

EXPECTED_TOOLS = (
    "semgrep",
    "gitleaks",
    "trivy",
    "dependency-scan",
    "ai-security-review",
)
"""`Finding.tool` value of every scanner in `scanner.scanners.SCANNERS`.

Declared rather than derived from the findings: a scanner that ran cleanly
emits nothing at all, and its absence from the report is exactly the signal
this module exists to prevent. `tests/test_coverage.py` fails if this drifts
from the registry.
"""

EXPECTED_OFF_FINDING_IDS = frozenset({"ai-review-disabled"})
"""Meta findings that report an opt-in feature being off, not a coverage gap.

AI review is disabled by default and stays that way unless explicitly
configured (ADR-010). Counting it as a gap would make every ordinary scan
announce itself as incomplete, and a banner that fires every time is a banner
nobody reads.
"""

_NOT_RUN_SUFFIXES = ("-not-installed", "-disabled")
_ERROR_SUFFIXES = ("-scan-error", "-json-parse-error", "-command-error")
_PARTIAL_SUFFIXES = ("-partial-coverage", "-no-supported-manifest")

_STATUS_RANK = {status: index for index, status in enumerate(COVERAGE_STATUSES)}

_RAN_DETAIL = "Ran without reporting a coverage problem."


@dataclass(frozen=True)
class ToolCoverage:
    """What one scanner actually managed to examine during a scan."""

    tool: str
    status: str
    detail: str
    meta_finding_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the normalized status early."""
        if self.status not in COVERAGE_STATUSES:
            raise ValueError(f"Unsupported coverage status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable coverage row."""
        return {
            "tool": self.tool,
            "status": self.status,
            "detail": self.detail,
            "meta_finding_ids": list(self.meta_finding_ids),
        }


def status_for_meta_finding(finding_id: str) -> str:
    """Map a meta finding id to the coverage state it implies.

    Args:
        finding_id: Normalized `Finding.id`, e.g. `"semgrep-not-installed"`.

    Returns:
        One of `COVERAGE_STATUSES`. An unrecognized meta finding falls back to
        `"partial"`: by definition it describes the state of the scan rather
        than a defect in the scanned code, and defaulting it to `"ran"` would
        reintroduce the silence this module removes.
    """
    if finding_id.endswith(_NOT_RUN_SUFFIXES):
        return "not_run"
    if finding_id.endswith(_ERROR_SUFFIXES):
        return "error"
    if finding_id.endswith(_PARTIAL_SUFFIXES):
        return "partial"
    return "partial"


def build_coverage(findings: list[Finding]) -> tuple[ToolCoverage, ...]:
    """Derive one coverage row per registered scanner.

    Call this on the raw output of `collect_findings`, before `apply_ignore`:
    `--ignore-file` does not yet exempt meta findings, so a path pattern
    matching the repository root can otherwise suppress the very finding that
    says a tool never ran.

    Args:
        findings: Normalized findings from every scanner, unfiltered.

    Returns:
        One row per entry in `EXPECTED_TOOLS`, in registry order. The worst
        state a tool reported wins; findings from unknown tools are ignored
        rather than raising.
    """
    by_tool: dict[str, list[Finding]] = {tool: [] for tool in EXPECTED_TOOLS}
    for finding in findings:
        if finding.is_meta and finding.tool in by_tool:
            by_tool[finding.tool].append(finding)

    rows: list[ToolCoverage] = []
    for tool in EXPECTED_TOOLS:
        metas = by_tool[tool]
        if not metas:
            rows.append(ToolCoverage(tool=tool, status="ran", detail=_RAN_DETAIL))
            continue
        worst = max(metas, key=lambda finding: _STATUS_RANK[status_for_meta_finding(finding.id)])
        rows.append(
            ToolCoverage(
                tool=tool,
                status=status_for_meta_finding(worst.id),
                detail=worst.title,
                meta_finding_ids=tuple(finding.id for finding in metas),
            )
        )
    return tuple(rows)


def _counts_as_covered(row: ToolCoverage) -> bool:
    """Return true when a row does not represent a gap in what was examined."""
    if row.status == "ran":
        return True
    return set(row.meta_finding_ids).issubset(EXPECTED_OFF_FINDING_IDS)


def incomplete_tools(coverage: tuple[ToolCoverage, ...]) -> tuple[ToolCoverage, ...]:
    """Return the rows that represent a real gap in what was examined."""
    return tuple(row for row in coverage if not _counts_as_covered(row))


def is_complete(coverage: tuple[ToolCoverage, ...]) -> bool:
    """Return true when every scanner examined what it was pointed at."""
    return not incomplete_tools(coverage)


def coverage_payload(coverage: tuple[ToolCoverage, ...]) -> dict[str, Any]:
    """Return the JSON-serializable coverage block embedded in reports."""
    return {
        "complete": is_complete(coverage),
        "incomplete_tool_count": len(incomplete_tools(coverage)),
        "tool_count": len(coverage),
        "tools": [row.to_dict() for row in coverage],
    }
