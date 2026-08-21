"""Normalized scanner findings."""

from dataclasses import asdict, dataclass
from typing import Any

SEVERITIES = ("critical", "high", "medium", "low", "info")
CONFIDENCES = ("high", "medium", "low")
FINDING_FIELDS = (
    "id",
    "tool",
    "severity",
    "title",
    "description",
    "file",
    "line",
    "recommendation",
    "confidence",
    "patch_before",
    "patch_after",
    "remediation_explanation",
    "is_meta",
)


@dataclass(frozen=True)
class Finding:
    """Security finding normalized across scanner tools."""

    id: str
    tool: str
    severity: str
    title: str
    description: str
    file: str
    line: int | None
    recommendation: str
    confidence: str
    patch_before: str = ""
    patch_after: str = ""
    remediation_explanation: str = ""
    is_meta: bool = False
    """True for scanner-infrastructure findings (tool missing, crashed, timed
    out, partial coverage) rather than defects in the scanned code.

    Meta findings are exempt from `--min-severity` filtering: they are emitted
    at `info` severity, and dropping them makes "the scanner crashed" render
    identically to "the scanner found nothing"."""

    def __post_init__(self) -> None:
        """Validate normalized values early."""
        if self.severity not in SEVERITIES:
            raise ValueError(f"Unsupported severity: {self.severity}")
        if self.confidence not in CONFIDENCES:
            raise ValueError(f"Unsupported confidence: {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable finding."""
        return asdict(self)
