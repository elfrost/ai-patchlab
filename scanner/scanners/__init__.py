"""Scanner registry."""

from collections.abc import Callable
from pathlib import Path

from scanner.models import Finding
from scanner.scanners.ai_review import scan_ai_security_review
from scanner.scanners.dependency_scan import scan_dependencies
from scanner.scanners.gitleaks import scan_gitleaks
from scanner.scanners.semgrep import scan_semgrep
from scanner.scanners.trivy import scan_trivy

Scanner = Callable[[Path, Path], list[Finding]]

SCANNERS: tuple[Scanner, ...] = (
    scan_semgrep,
    scan_gitleaks,
    scan_trivy,
    scan_dependencies,
    scan_ai_security_review,
)
