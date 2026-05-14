"""Display-path helpers for scanner findings.

When AI PatchLab scans a temporary clone (e.g. from `--from-git-url`) or
any absolute repo path, the raw `Finding.file` value is the absolute disk
path. Reports are easier to read - and survive cleanup of the temp dir -
when paths are rebased relative to the repository root and rendered with
POSIX separators.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from scanner.models import Finding


def rebase_finding_path(file: str, repo_root: Path) -> str:
    """Return a repo-relative POSIX path for display.

    Args:
        file: Raw `Finding.file` value (absolute, relative, empty, or a
            sentinel like `<unknown>`).
        repo_root: Scan root that the path should be made relative to.

    Returns:
        - `""` when `file` is empty.
        - `"."` when `file` resolves to `repo_root` itself.
        - A POSIX-style relative path (e.g. `"src/db/usage.py"`) when the
          file lives inside `repo_root`.
        - The original `file` value when it cannot be resolved or lives
          outside `repo_root`.
    """
    if not file:
        return file

    try:
        finding_path = Path(file).resolve()
    except (OSError, ValueError):
        return file

    try:
        resolved_root = repo_root.resolve()
    except (OSError, ValueError):
        return file

    if finding_path == resolved_root:
        return "."

    try:
        rel = finding_path.relative_to(resolved_root)
    except ValueError:
        return file

    return rel.as_posix()


def rebase_finding_paths(findings: list[Finding], repo_root: Path) -> list[Finding]:
    """Return new findings with `file` rebased relative to `repo_root`.

    Findings whose path stays unchanged are returned as-is (same object)
    so identity-sensitive callers can detect "no rebase happened". When a
    finding's `id` was generated from the absolute file path (common in
    Semgrep), the same substitution is applied to the id so it does not
    contradict the rebased `file`.
    """
    rebased: list[Finding] = []
    for finding in findings:
        new_file = rebase_finding_path(finding.file, repo_root)
        if new_file == finding.file:
            rebased.append(finding)
            continue
        new_id = (
            finding.id.replace(finding.file, new_file)
            if finding.file and finding.file in finding.id
            else finding.id
        )
        rebased.append(replace(finding, file=new_file, id=new_id))
    return rebased
