"""Run pip-audit and capture raw JSON output."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# pip-audit has no internal time bound: resolving a `project` input builds the
# full dependency graph and has been observed running indefinitely on large
# pyproject repositories, hanging the entire scan. Five minutes is well past a
# normal run (seconds to low tens of seconds) while keeping the scan finite.
DEFAULT_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class PipAuditInput:
    """Resolved pip-audit input for a repository."""

    kind: str
    paths: tuple[Path, ...]

    @property
    def display_path(self) -> Path:
        """Return the most useful path to show on normalized findings."""
        if len(self.paths) == 1:
            return self.paths[0]
        return self.paths[0].parent


@dataclass(frozen=True)
class PipAuditResult:
    """Result of a pip-audit invocation."""

    installed: bool
    raw_report_path: Path
    audit_input: PipAuditInput | None = None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def completed(self) -> bool:
        """Whether pip-audit was installed and executed."""
        return self.installed and self.returncode is not None


def run_pip_audit(
    repo_path: Path,
    raw_report_path: Path,
    audit_input: PipAuditInput,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> PipAuditResult:
    """Run pip-audit against supported Python dependency manifests.

    Args:
        repo_path: Repository being scanned.
        raw_report_path: Where the raw pip-audit JSON is written.
        audit_input: The resolved manifest or locked project to audit.
        timeout_seconds: Hard bound on the subprocess. On expiry an empty raw
            report is written and a `124` return code is reported, so the
            adapter surfaces a scan error instead of the scan hanging.
    """
    command_prefix = find_pip_audit_command()
    if command_prefix is None:
        return PipAuditResult(
            installed=False,
            raw_report_path=raw_report_path,
            audit_input=audit_input,
        )

    raw_report_path.parent.mkdir(parents=True, exist_ok=True)
    command = _build_pip_audit_command(command_prefix, repo_path, raw_report_path, audit_input)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        # pip-audit resolves a `project` input by building the dependency graph,
        # which on a heavy pyproject can run indefinitely. Without a timeout the
        # whole scan hangs and produces no report at all; with one, the scan
        # completes and the missing dependency coverage is stated explicitly.
        raw_report_path.write_text("[]", encoding="utf-8")
        return PipAuditResult(
            installed=True,
            raw_report_path=raw_report_path,
            audit_input=audit_input,
            returncode=124,
            stderr=f"pip-audit timed out after {exc.timeout} seconds.",
        )
    except OSError as exc:
        raw_report_path.write_text("[]", encoding="utf-8")
        return PipAuditResult(
            installed=True,
            raw_report_path=raw_report_path,
            audit_input=audit_input,
            returncode=127,
            stderr=str(exc),
        )

    if not raw_report_path.exists():
        raw_report_path.write_text("[]", encoding="utf-8")

    return PipAuditResult(
        installed=True,
        raw_report_path=raw_report_path,
        audit_input=audit_input,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def find_pip_audit_input(repo_path: Path) -> PipAuditInput | None:
    """Find supported Python dependency inputs for pip-audit."""
    requirements = _find_requirements_files(repo_path)
    if requirements:
        return PipAuditInput(kind="requirements", paths=tuple(requirements))

    pylock_files = sorted(repo_path.glob("pylock.*.toml"))
    if pylock_files:
        return PipAuditInput(kind="locked-project", paths=tuple([repo_path, *pylock_files]))

    pyproject_path = repo_path / "pyproject.toml"
    if pyproject_path.exists():
        return PipAuditInput(kind="project", paths=(repo_path,))

    return None


def find_pip_audit_command() -> list[str] | None:
    """Find pip-audit as an executable first, then as an importable module."""
    executable = shutil.which("pip-audit")
    if executable:
        return [executable]

    if importlib.util.find_spec("pip_audit") is not None:
        return [sys.executable, "-m", "pip_audit"]

    return None


def _find_requirements_files(repo_path: Path) -> list[Path]:
    """Return root-level requirements files in stable command order."""
    candidates = [
        repo_path / "requirements.txt",
        repo_path / "requirements-dev.txt",
        repo_path / "dev-requirements.txt",
    ]
    requirements_dir = repo_path / "requirements"
    if requirements_dir.is_dir():
        candidates.extend(sorted(requirements_dir.glob("*.txt")))

    return [path for path in candidates if path.exists() and path.is_file()]


def _build_pip_audit_command(
    command_prefix: list[str],
    repo_path: Path,
    raw_report_path: Path,
    audit_input: PipAuditInput,
) -> list[str]:
    """Build the pip-audit command for a resolved input."""
    command = [
        *command_prefix,
        "--format",
        "json",
        "--output",
        str(raw_report_path),
        "--progress-spinner",
        "off",
    ]

    if audit_input.kind == "requirements":
        for requirement_path in audit_input.paths:
            command.extend(["--requirement", str(requirement_path)])
        return command

    if audit_input.kind == "locked-project":
        command.append("--locked")

    command.append(str(repo_path))
    return command
