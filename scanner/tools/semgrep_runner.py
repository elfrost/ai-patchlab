"""Run Semgrep and capture raw JSON output."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

PIP_USER_SEMGREP_PATH = (
    Path.home() / "AppData" / "Roaming" / "Python" / "Python313" / "Scripts" / "semgrep.exe"
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
            env=_build_semgrep_env(executable),
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


def _build_semgrep_env(executable: str | PathLike[str]) -> dict[str, str]:
    """Build the Semgrep child environment.

    Two concerns:
    1. Ensure adjacent Semgrep helper scripts are discoverable on Windows.
    2. Force UTF-8 file I/O. Semgrep writes its ``--output`` report via
       Python's default text codec, which on Windows is the locale codepage
       (e.g. cp1252). Source content containing non-Latin-1 characters
       (Chinese/Japanese/Korean comments, emoji, ...) then raises
       ``UnicodeEncodeError`` mid-write, leaving a 0-byte report and a
       non-zero exit. Setting ``PYTHONUTF8`` / ``PYTHONIOENCODING`` makes the
       child use UTF-8 regardless of the host locale.
    """
    import os

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    executable_dir = str(Path(executable).parent)
    current_path = env.get("PATH", "")
    if executable_dir and executable_dir.lower() not in current_path.lower().split(os.pathsep):
        env["PATH"] = (
            f"{executable_dir}{os.pathsep}{current_path}" if current_path else executable_dir
        )
    return env
