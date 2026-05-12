"""Trivy placeholder scanner."""

from pathlib import Path

from scanner.models import Finding
from scanner.scanners.common import placeholder_finding


def scan_trivy(repo_path: Path, reports_dir: Path) -> list[Finding]:
    """Return a normalized placeholder for future Trivy integration."""
    _ = reports_dir
    return [
        placeholder_finding(
            tool="trivy",
            finding_id="trivy-placeholder",
            title="Trivy placeholder",
            description="Filesystem, container, or IaC scanning through Trivy is not implemented yet.",
            repo_path=repo_path,
        )
    ]
