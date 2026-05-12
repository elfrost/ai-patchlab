"""AI security review placeholder scanner."""

from pathlib import Path

from scanner.models import Finding
from scanner.scanners.common import placeholder_finding


def scan_ai_security_review(repo_path: Path, reports_dir: Path) -> list[Finding]:
    """Return a normalized placeholder for future local AI review logic."""
    _ = reports_dir
    return [
        placeholder_finding(
            tool="ai-security-review",
            finding_id="ai-review-placeholder",
            title="AI security review placeholder",
            description="AI-assisted review is not implemented yet and no paid API is called.",
            repo_path=repo_path,
        )
    ]
