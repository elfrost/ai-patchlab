"""Run a user-configured local AI security review command.

This runner never calls a remote endpoint, paid API, or hosted model. It only
invokes the executable explicitly configured by the user and captures the
output for normalization by `scanner.scanners.ai_review`.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from scanner.config import AiReviewConfig


@dataclass(frozen=True)
class AiReviewResult:
    """Result of a local AI review command invocation."""

    configured: bool
    raw_report_path: Path
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    command: tuple[str, ...] = field(default_factory=tuple)

    @property
    def completed(self) -> bool:
        """Whether the AI review command was configured and executed."""
        return self.configured and self.returncode is not None


def run_ai_review_command(
    repo_path: Path,
    reports_dir: Path,
    config: AiReviewConfig,
) -> AiReviewResult:
    """Execute the configured local AI review command.

    If AI review is disabled or not fully configured, no subprocess is started
    and a non-configured result is returned. Failures (missing executable,
    timeout, non-zero exit codes) are captured and reported so the calling
    scanner can emit a normalized info finding instead of raising.
    """
    raw_report_path = reports_dir / "raw" / "ai-review.json"

    if not config.is_local_command_ready:
        return AiReviewResult(
            configured=False,
            raw_report_path=raw_report_path,
        )

    raw_report_path.parent.mkdir(parents=True, exist_ok=True)
    command: tuple[str, ...] = (
        config.ai_review_command,
        "--repo",
        str(repo_path),
        "--output",
        str(raw_report_path),
    )

    try:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=config.ai_review_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        if not raw_report_path.exists():
            raw_report_path.write_text("[]", encoding="utf-8")
        return AiReviewResult(
            configured=True,
            raw_report_path=raw_report_path,
            returncode=124,
            stderr=f"AI review command timed out after {exc.timeout} seconds.",
            command=command,
        )
    except OSError as exc:
        if not raw_report_path.exists():
            raw_report_path.write_text("[]", encoding="utf-8")
        return AiReviewResult(
            configured=True,
            raw_report_path=raw_report_path,
            returncode=127,
            stderr=str(exc),
            command=command,
        )

    if not raw_report_path.exists():
        stdout_text = completed.stdout or ""
        if stdout_text.strip():
            raw_report_path.write_text(stdout_text, encoding="utf-8")
        else:
            raw_report_path.write_text("[]", encoding="utf-8")

    return AiReviewResult(
        configured=True,
        raw_report_path=raw_report_path,
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        command=command,
    )
