"""Dependency scan placeholder module."""

from pathlib import Path

from scanner.models import Finding
from scanner.scanners.common import placeholder_finding


def scan_dependencies(repo_path: Path, reports_dir: Path) -> list[Finding]:
    """Return a normalized placeholder for dependency scanning."""
    _ = reports_dir
    return [
        placeholder_finding(
            tool="dependency-scan",
            finding_id="dependency-scan-placeholder",
            title="Dependency scan placeholder",
            description="Dependency vulnerability scanning is not implemented yet.",
            repo_path=repo_path,
        )
    ]
