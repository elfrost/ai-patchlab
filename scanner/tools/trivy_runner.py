"""Run Trivy and capture raw JSON output."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrivyResult:
    """Result of a Trivy invocation."""

    installed: bool
    raw_report_path: Path
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def completed(self) -> bool:
        """Whether Trivy was installed and executed."""
        return self.installed and self.returncode is not None


def run_trivy(repo_path: Path, raw_report_path: Path) -> TrivyResult:
    """Run Trivy filesystem scanning against a local repository."""
    executable = find_trivy_executable()
    if executable is None:
        return TrivyResult(installed=False, raw_report_path=raw_report_path)

    raw_report_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        "fs",
        "--format",
        "json",
        "--output",
        str(raw_report_path),
        "--scanners",
        "vuln,misconfig",
        "--no-progress",
        "--skip-version-check",
        str(repo_path),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raw_report_path.write_text('{"Results": []}', encoding="utf-8")
        return TrivyResult(
            installed=True,
            raw_report_path=raw_report_path,
            returncode=127,
            stderr=str(exc),
        )

    if not raw_report_path.exists():
        raw_report_path.write_text('{"Results": []}', encoding="utf-8")

    return TrivyResult(
        installed=True,
        raw_report_path=raw_report_path,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def find_trivy_executable() -> str | None:
    """Find Trivy on PATH."""
    return shutil.which("trivy")
