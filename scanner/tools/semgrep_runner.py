"""Run Semgrep and capture raw JSON output."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PIP_USER_SEMGREP_PATH = Path(
    r"C:\Users\Elfrost\AppData\Roaming\Python\Python313\Scripts\semgrep.exe"
)


@dataclass(frozen=True)
class SemgrepResult:
    """Result of a Semgrep invocation."""

    installed: bool
    raw_report_path: Path
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def completed(self) -> bool:
        """Whether Semgrep was installed and executed."""
        return self.installed and self.returncode is not None


def run_semgrep(repo_path: Path, raw_report_path: Path) -> SemgrepResult:
    """Run Semgrep against a local repository and write its JSON report."""
    executable = find_semgrep_executable()
    if executable is None:
        return SemgrepResult(installed=False, raw_report_path=raw_report_path)

    raw_report_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        "scan",
        "--config",
        "auto",
        "--json",
        "--output",
        str(raw_report_path),
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
        raw_report_path.write_text('{"results": []}', encoding="utf-8")
        return SemgrepResult(
            installed=True,
            raw_report_path=raw_report_path,
            returncode=127,
            stderr=str(exc),
        )

    if not raw_report_path.exists():
        raw_report_path.write_text('{"results": []}', encoding="utf-8")

    return SemgrepResult(
        installed=True,
        raw_report_path=raw_report_path,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def find_semgrep_executable() -> str | None:
    """Find Semgrep on PATH first, then the Windows Python user Scripts path."""
    executable = shutil.which("semgrep")
    if executable:
        return executable
    if PIP_USER_SEMGREP_PATH.exists():
        return str(PIP_USER_SEMGREP_PATH)
    return None
