"""Path-based suppression of findings via .gitignore-style patterns.

A scan can be paired with an "ignore file" (passed via `--ignore-file`)
that lists path patterns to exclude from the report. Patterns use the
same syntax as `.gitignore`: glob with `**` for any-depth matches, `!`
prefix for negation. This is invaluable for scanning targets that have
recurring false-positive shapes (test cassettes, security-tool detector
fixtures, vendored libraries) without having to teach our scanner-level
rules about every project's conventions.

Suppression happens AFTER `rebase_finding_paths`, so patterns are
matched against POSIX repo-relative paths (e.g. `tests/**` matches
`tests/foo/bar.py`).
"""

from __future__ import annotations

from pathlib import Path

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern

from scanner.models import Finding


def parse_ignore_patterns(raw: str) -> list[str]:
    """Split raw text into ignore patterns; drop blank lines and comments.

    Comments are lines whose first non-whitespace character is `#`. Both
    leading and trailing whitespace is stripped from each kept pattern.
    """
    patterns: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)
    return patterns


def load_ignore_patterns(path: Path | None) -> list[str]:
    """Read an ignore file from disk and return its patterns.

    Returns an empty list when `path` is None (no suppression configured).
    Raises `FileNotFoundError` if `path` is given but does not exist.
    """
    if path is None:
        return []
    return parse_ignore_patterns(path.read_text(encoding="utf-8"))


def apply_ignore(findings: list[Finding], patterns: list[str]) -> list[Finding]:
    """Drop findings whose `file` matches one of the gitignore-style patterns.

    Findings with an empty `file` field (e.g. info-level "tool not
    installed" placeholders that point at the repo root) are never
    suppressed - they don't represent a real path and the user
    presumably wants to keep seeing infrastructure signals.
    """
    if not patterns:
        return list(findings)

    spec = PathSpec.from_lines(GitWildMatchPattern, patterns)
    return [
        finding for finding in findings if not finding.file or not spec.match_file(finding.file)
    ]
