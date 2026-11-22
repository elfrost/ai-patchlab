"""Strip local and editable lines out of a target's requirements files.

pip resolves `-e .`, `.[extra]`, `./pkg` and `file:` entries against its working
directory and then builds them, which runs the build backend of whatever it
found there. Handed a scanned repository's requirements file, that means either
auditing the wrong project (the scanner's own cwd, observed on a scanned repository whose
`requirements.txt` is only `-e .[app]`) or executing code the target controls.

This module reads the files as data, never hands those lines to pip, and says
what it dropped. The project's own declared dependencies are recovered from
`pyproject.toml` when they are statically listed.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

MAX_INCLUDE_DEPTH = 10

_INCLUDE_OPTIONS = ("-r", "--requirement")
_CONSTRAINT_OPTIONS = ("-c", "--constraint")
_EDITABLE_OPTIONS = ("-e", "--editable")
_PROJECT_ROOT_TARGETS = frozenset({".", "./", ".\\"})
_EXTRAS_PATTERN = re.compile(r"^(?P<target>[^\[]*)\[(?P<extras>[^\]]*)\]\s*$")
_LOCAL_AFTER_AT = re.compile(r"@\s*(?:file:|\.|/|\\|~|[A-Za-z]:[\\/])", re.IGNORECASE)


@dataclass(frozen=True)
class SkippedRequirement:
    """One requirements line that was never handed to pip."""

    file: str
    line: int
    text: str
    reason: str
    resolved: bool = False

    def describe(self) -> str:
        """Return a one-line description for a report."""
        return f"{self.file}:{self.line} `{self.text}` ({self.reason})"


@dataclass(frozen=True)
class SanitizedRequirements:
    """Requirements that are safe to audit, plus what was left out."""

    lines: tuple[str, ...]
    skipped: tuple[SkippedRequirement, ...]
    rewritten: bool

    @property
    def unresolved(self) -> tuple[SkippedRequirement, ...]:
        """Skipped lines whose dependencies are not covered by the audit."""
        return tuple(item for item in self.skipped if not item.resolved)


def sanitize_requirements(repo_path: Path, files: tuple[Path, ...]) -> SanitizedRequirements:
    """Flatten `files`, dropping every line pip would resolve from disk.

    Args:
        repo_path: Repository root. Includes that leave it are not followed.
        files: Requirements files in command order.

    Returns:
        Auditable lines, the skipped entries, and whether the output differs
        from the input files (so a clean file can be audited in place).
    """
    lines: list[str] = []
    skipped: list[SkippedRequirement] = []
    rewritten = False
    for path in files:
        rewritten |= _walk(repo_path, path, lines, skipped, seen=set(), depth=0)

    pyproject = _read_pyproject(repo_path)
    resolved_skipped: list[SkippedRequirement] = []
    for item in skipped:
        extras = _project_root_extras(item.text)
        if extras is None:
            resolved_skipped.append(item)
            continue
        recovered = _declared_dependencies(pyproject, extras)
        if recovered is None:
            resolved_skipped.append(item)
            continue
        lines.extend(line for line in recovered if line not in lines)
        resolved_skipped.append(
            SkippedRequirement(item.file, item.line, item.text, item.reason, resolved=True)
        )
    return SanitizedRequirements(tuple(lines), tuple(resolved_skipped), rewritten)


def _walk(
    repo_path: Path,
    path: Path,
    lines: list[str],
    skipped: list[SkippedRequirement],
    seen: set[Path],
    depth: int,
) -> bool:
    """Append one file's auditable lines to `lines`. Return true if it changed."""
    label = _relative(path, repo_path)
    resolved = path.resolve()
    if resolved in seen or depth > MAX_INCLUDE_DEPTH:
        return False
    seen.add(resolved)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        skipped.append(SkippedRequirement(label, 0, str(path.name), "unreadable-file"))
        return True

    changed = False
    for number, logical in _logical_lines(text):
        option, argument = _split_option(logical)
        if option in _INCLUDE_OPTIONS:
            changed = True
            target = (path.parent / argument).resolve() if argument else None
            if target is None or not _inside(target, repo_path) or not target.is_file():
                skipped.append(SkippedRequirement(label, number, logical, "unusable-include"))
                continue
            _walk(repo_path, target, lines, skipped, seen, depth + 1)
        elif option in _EDITABLE_OPTIONS:
            changed = True
            skipped.append(SkippedRequirement(label, number, logical, "editable"))
        elif option in _CONSTRAINT_OPTIONS:
            changed = True
            target = (path.parent / argument).resolve() if argument else None
            if target is not None and _inside(target, repo_path) and target.is_file():
                lines.append(f"{option} {target}")
            else:
                skipped.append(SkippedRequirement(label, number, logical, "unusable-constraint"))
        elif option is None and _is_local_target(_requirement_spec(logical)):
            changed = True
            skipped.append(SkippedRequirement(label, number, logical, "local-path"))
        else:
            lines.append(logical)
    return changed


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Join `\\` continuations, drop comments and blanks, keep line numbers."""
    result: list[tuple[int, str]] = []
    buffer = ""
    start = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        if not buffer:
            start = number
        stripped = raw.rstrip()
        if stripped.endswith("\\"):
            buffer += stripped[:-1] + " "
            continue
        buffer += stripped
        content = re.sub(r"(^|\s)#.*$", "", buffer).strip()
        buffer = ""
        if content:
            result.append((start, content))
    if buffer.strip():
        content = re.sub(r"(^|\s)#.*$", "", buffer).strip()
        if content:
            result.append((start, content))
    return result


def _split_option(line: str) -> tuple[str | None, str]:
    """Return `(option, argument)` for `-r x`, `--editable=x`, `-e.`; else None."""
    for option in (*_INCLUDE_OPTIONS, *_CONSTRAINT_OPTIONS, *_EDITABLE_OPTIONS):
        if option.startswith("--"):
            if line == option:
                return option, ""
            if line.startswith((option + "=", option + " ")):
                return option, line[len(option) + 1 :].strip()
        elif line.startswith(option):
            # pip accepts the attached short form (`-e.`, `-rfile.txt`).
            return option, line[len(option) :].strip()
    return None, line


def _requirement_spec(line: str) -> str:
    """Drop per-requirement options such as `--hash=...` from a line."""
    return re.split(r"\s+--?[A-Za-z]", line, maxsplit=1)[0].strip()


def _is_local_target(spec: str) -> bool:
    """Return true when pip would read `spec` from disk instead of an index."""
    if not spec:
        return False
    lowered = spec.lower()
    if lowered.startswith("file:"):
        return True
    if _LOCAL_AFTER_AT.search(spec) or re.match(r"^[A-Za-z]:[\\/]", spec):
        return True
    if "://" in spec:
        return False
    if spec.startswith((".", "/", "\\", "~")):
        return True
    head = re.split(r"[;\s=<>!~@\[]", spec, maxsplit=1)[0]
    return "/" in head or "\\" in head


def _project_root_extras(text: str) -> tuple[str, ...] | None:
    """Return the extras of a `.` / `.[a,b]` line, or None for any other line."""
    spec = text
    option, argument = _split_option(text)
    if option in _EDITABLE_OPTIONS:
        spec = argument
    spec = _requirement_spec(spec).split("#egg=")[0].strip()
    match = _EXTRAS_PATTERN.match(spec)
    target, extras = (match.group("target"), match.group("extras")) if match else (spec, "")
    if target.strip() not in _PROJECT_ROOT_TARGETS:
        return None
    return tuple(part.strip() for part in extras.split(",") if part.strip())


def _read_pyproject(repo_path: Path) -> dict | None:
    """Parse the target's `pyproject.toml` as data. Never imports or builds it."""
    try:
        return tomllib.loads((repo_path / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None


def _declared_dependencies(pyproject: dict | None, extras: tuple[str, ...]) -> list[str] | None:
    """Return statically declared dependencies, or None when they cannot be read.

    `None` covers a missing `[project]` table (Poetry, flit-legacy), a
    `dynamic = ["dependencies"]` project, and an extra the project never
    defines. Guessing in any of those cases would report an audit that never
    looked at the real dependency set.
    """
    project = (pyproject or {}).get("project")
    if not isinstance(project, dict):
        return None
    dynamic = project.get("dynamic") or []
    optional = project.get("optional-dependencies") or {}
    if "dependencies" in dynamic and "dependencies" not in project:
        return None
    if extras and "optional-dependencies" in dynamic and not optional:
        return None
    declared = project.get("dependencies", [])
    if not isinstance(declared, list):
        return None
    collected = [str(item) for item in declared]
    for extra in extras:
        group = optional.get(extra) if isinstance(optional, dict) else None
        if not isinstance(group, list):
            return None
        collected.extend(str(item) for item in group)
    return collected


def _inside(path: Path, repo_path: Path) -> bool:
    """Return true when `path` is within the repository."""
    try:
        path.relative_to(repo_path.resolve())
    except ValueError:
        return False
    return True


def _relative(path: Path, repo_path: Path) -> str:
    """Return a repo-relative POSIX path for display."""
    try:
        return path.resolve().relative_to(repo_path.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
