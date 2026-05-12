"""Run Gitleaks and capture raw JSON output."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

WINGET_GITLEAKS_PATH = Path(
    r"C:\Users\Elfrost\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gitleaks.Gitleaks_Microsoft.Winget.Source_8wekyb3d8bbwe\gitleaks.exe"
)


@dataclass(frozen=True)
class GitleaksResult:
    """Result of a Gitleaks invocation."""

    installed: bool
    raw_report_path: Path
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def completed(self) -> bool:
        """Whether Gitleaks was installed and executed."""
        return self.installed and self.returncode is not None


def run_gitleaks(repo_path: Path, raw_report_path: Path) -> GitleaksResult:
    """Run Gitleaks against a local repository and write its JSON report."""
    executable = find_gitleaks_executable()
    if executable is None:
        return GitleaksResult(installed=False, raw_report_path=raw_report_path)

    raw_report_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        "detect",
        "--source",
        str(repo_path),
        "--report-format",
        "json",
        "--report-path",
        str(raw_report_path),
        "--no-git",
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
        raw_report_path.write_text("[]", encoding="utf-8")
        return GitleaksResult(
            installed=True,
            raw_report_path=raw_report_path,
            returncode=127,
            stderr=str(exc),
        )

    if not raw_report_path.exists():
        raw_report_path.write_text("[]", encoding="utf-8")

    return GitleaksResult(
        installed=True,
        raw_report_path=raw_report_path,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def find_gitleaks_executable() -> str | None:
    """Find Gitleaks on PATH first, then the Windows WinGet package path."""
    executable = shutil.which("gitleaks")
    if executable:
        return executable
    if WINGET_GITLEAKS_PATH.exists():
        return str(WINGET_GITLEAKS_PATH)
    return None
