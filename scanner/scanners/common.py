"""Shared helpers for scanner placeholder modules."""

from pathlib import Path

from scanner.models import Finding


def placeholder_finding(
    *,
    tool: str,
    finding_id: str,
    title: str,
    description: str,
    repo_path: Path,
) -> Finding:
    """Create a normalized info-level placeholder finding."""
    return Finding(
        id=finding_id,
        tool=tool,
        severity="info",
        title=title,
        description=description,
        file=str(repo_path),
        line=None,
        recommendation="Wire this placeholder to the real scanner and map results into the normalized finding schema.",
        confidence="low",
    )
