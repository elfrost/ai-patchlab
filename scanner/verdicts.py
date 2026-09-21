"""Dismissal records: what a scan removed, and why.

A scan reports the one finding that mattered and silently discards the rest.
The discarded majority is where the expensive work lives - the argument that a
rule family is a false positive gets made once, compressed into a paragraph of
prose, and lost, so the next repository is triaged from zero.

ADR-014 showed what the recorded version is worth: counting an informal vote
("13th appearance of the SQL-identifier FP") across 87 archived reports turned
it into 1,802 hits over 26 repositories and justified mechanizing the rule. The
findings were archived; the verdicts were not.

This module records verdicts as counted rule families, from two producers
sharing one schema (ADR-016):

* `scanner` rows are deterministic - the diff across each suppression step.
* `curation` rows are judgement, appended by `/daily` Phase 4.

Rows are grouped by `(tool, rule)` with a count, never one row per finding: a
severity floor can drop hundreds of findings at once, and the curation workflow
already reasons in rule families.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from scanner.models import Finding

VERDICT_SOURCES = ("scanner", "curation")

SCANNER_REASON_CODES = ("ignore-pattern", "below-min-severity")
"""Reason codes the scanner itself can emit, deterministically."""

CURATION_REASON_CODES = (
    "sql-identifier-fp",
    "test-or-fixture-path",
    "sample-or-demo",
    "vendored-code",
    "not-reachable",
    "mitigated-in-app",
    "by-design",
    "product-surface",
    "domain-noun-collision",
    "placeholder-secret",
    "active-harm-fp",
    "credited-defense",
    "confirmed-real",
)
"""Closed vocabulary for judgement rows.

Closed on purpose. The corpus is only worth keeping if it can be counted, and a
long tail of one-off codes counts to one. Each code here is a curation pattern
the scan series has hit repeatedly; adding one is cheap, inventing one per scan
defeats the file.
"""

REASON_CODES = SCANNER_REASON_CODES + CURATION_REASON_CODES

VERDICTS = ("false-positive", "by-design", "not-applicable", "hardening", "real")

_UNKNOWN_RULE = "(unlabelled)"


@dataclass(frozen=True)
class VerdictRecord:
    """One rule family that a scan removed or triaged, with a count and a why."""

    source: str
    reason_code: str
    tool: str
    rule: str
    count: int
    verdict: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        """Validate the closed vocabularies early."""
        if self.source not in VERDICT_SOURCES:
            raise ValueError(f"Unsupported verdict source: {self.source}")
        if self.reason_code not in REASON_CODES:
            raise ValueError(f"Unsupported reason code: {self.reason_code}")
        if self.verdict and self.verdict not in VERDICTS:
            raise ValueError(f"Unsupported verdict: {self.verdict}")
        if self.count < 1:
            raise ValueError(f"A verdict record counts at least one finding: {self.count}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable verdict row."""
        return {
            "source": self.source,
            "reason_code": self.reason_code,
            "tool": self.tool,
            "rule": self.rule,
            "count": self.count,
            "verdict": self.verdict,
            "detail": self.detail,
        }


def _family(finding: Finding) -> tuple[str, str]:
    """Return the `(tool, rule)` family key a finding belongs to.

    `Finding.title` carries the rule identity across every adapter - the
    Semgrep check id, the Gitleaks rule name, the Trivy advisory - while
    `Finding.id` embeds the path and so differs per occurrence.
    """
    return (finding.tool, finding.title or _UNKNOWN_RULE)


def summarize_removed(
    before: list[Finding],
    after: list[Finding],
    reason_code: str,
    detail: str = "",
) -> tuple[VerdictRecord, ...]:
    """Record what a suppression step removed, grouped by rule family.

    Args:
        before: Findings entering the step.
        after: Findings surviving the step.
        reason_code: Why they were removed; must be a `SCANNER_REASON_CODES` entry.
        detail: Optional human sentence naming the concrete cause.

    Returns:
        One row per `(tool, rule)` family that lost at least one finding,
        sorted by descending count then family, so the output is stable.
    """
    if reason_code not in SCANNER_REASON_CODES:
        raise ValueError(f"Not a scanner reason code: {reason_code}")

    removed = Counter(_family(finding) for finding in before)
    removed.subtract(Counter(_family(finding) for finding in after))

    rows = [
        VerdictRecord(
            source="scanner",
            reason_code=reason_code,
            tool=tool,
            rule=rule,
            count=count,
            detail=detail,
        )
        for (tool, rule), count in removed.items()
        if count > 0
    ]
    rows.sort(key=lambda row: (-row.count, row.tool, row.rule))
    return tuple(rows)


def total_dismissed(records: tuple[VerdictRecord, ...]) -> int:
    """Return how many individual findings the records account for."""
    return sum(record.count for record in records)


def count_by_reason(records: tuple[VerdictRecord, ...]) -> dict[str, int]:
    """Return findings dismissed per reason code, highest first.

    This is the measurement ADR-014 had to reconstruct by hand. Kept
    deliberately small: a loader and a counter, not a query language.
    """
    totals: Counter[str] = Counter()
    for record in records:
        totals[record.reason_code] += record.count
    return dict(sorted(totals.items(), key=lambda item: (-item[1], item[0])))


def verdicts_payload(records: tuple[VerdictRecord, ...]) -> dict[str, Any]:
    """Return the JSON-serializable dismissal block embedded in reports."""
    return {
        "total_dismissed": total_dismissed(records),
        "by_reason": count_by_reason(records),
        "records": [record.to_dict() for record in records],
    }


def load_records(payload: dict[str, Any]) -> tuple[VerdictRecord, ...]:
    """Rebuild records from a `verdicts.json` payload.

    Unknown rows are rejected rather than skipped: a corpus that silently drops
    what it cannot parse reports a smaller count than the truth, which is the
    failure mode this whole module exists to prevent.
    """
    return tuple(
        VerdictRecord(
            source=row["source"],
            reason_code=row["reason_code"],
            tool=row["tool"],
            rule=row["rule"],
            count=int(row["count"]),
            verdict=row.get("verdict", ""),
            detail=row.get("detail", ""),
        )
        for row in payload.get("records", [])
    )
