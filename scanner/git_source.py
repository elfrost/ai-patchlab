"""Acquire a scan target from a remote git URL.

This module is the only place where AI PatchLab clones source code from a
remote location. It exposes a context manager that performs a shallow
public clone into a temporary directory, yields the path, and removes the
directory on exit so a scan never leaves files behind.

Only public HTTPS / SSH remotes are supported. The module shells out to
the local `git` executable through `subprocess.run(..., shell=False)` and
never invokes a remote API.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

_GIT_URL_PATTERN = re.compile(
    r"^(https?://[^\s]+|git@[^\s:]+:[^\s]+\.git)$",
)


class GitCloneError(RuntimeError):
    """Raised when cloning a remote git repository fails."""


@dataclass(frozen=True)
class GitCloneResult:
    """Outcome of a successful git clone operation."""

    url: str
    repo_path: Path
    head_sha: str | None


def is_valid_git_url(url: object) -> bool:
    """Return True when the URL looks like a clonable git remote.

    Cheap shape check that runs before invoking `git`. Accepts HTTPS, HTTP,
    and SSH (`git@host:owner/repo.git`) forms. Rejects local paths, FTP,
    `file://`, empty strings, and non-string inputs.
    """
    if not isinstance(url, str):
        return False
    candidate = url.strip()
    if not candidate:
        return False
    return bool(_GIT_URL_PATTERN.match(candidate))


@contextmanager
def cloned_repo(url: str, depth: int = 1) -> Iterator[GitCloneResult]:
    """Shallow-clone a public git URL into a temp directory; cleanup on exit.

    Args:
        url: HTTPS or SSH git URL to clone.
        depth: Clone depth (default `1` for fast scans).

    Yields:
        A `GitCloneResult` whose `repo_path` is a temporary directory that
        is removed when the context exits.

    Raises:
        GitCloneError: If the URL is invalid, git is not installed, or the
            clone process exits non-zero.
    """
    if not is_valid_git_url(url):
        raise GitCloneError(f"Not a recognized git URL: {url}")

    if shutil.which("git") is None:
        raise GitCloneError("git is not installed or not on PATH")

    with TemporaryDirectory(prefix="ai-patchlab-clone-") as tmp:
        target = Path(tmp) / "repo"
        try:
            subprocess.run(
                ["git", "clone", "--depth", str(depth), url, str(target)],
                check=True,
                capture_output=True,
                text=True,
                shell=False,
            )
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise GitCloneError(
                f"git clone failed (exit {exc.returncode}): {stderr or 'no stderr'}"
            ) from exc
        except FileNotFoundError as exc:
            raise GitCloneError("git executable could not be invoked") from exc

        head_sha = _read_head_sha(target)
        yield GitCloneResult(url=url, repo_path=target, head_sha=head_sha)


def _read_head_sha(repo_path: Path) -> str | None:
    """Return the resolved HEAD commit SHA, or None when unavailable."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            shell=False,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None
