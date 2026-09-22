#!/usr/bin/env python3
"""PreToolUse hook: block `git commit` when the commit would include secret files,
and prompt for confirmation when the incoming diff looks like it holds a hardcoded
secret.

Replaces an inline shell one-liner that was inert twice over: it called `jq` (absent
on Windows, so the command variable was always empty and the guard body never ran),
and it signalled a block with `exit 1`, which Claude Code treats as NON-blocking.
Policy enforcement needs `exit 2` or a JSON permissionDecision; this uses the JSON
form, like vague-verb-check.py.

Covers three commit shapes, because reading only the index misses two of them:
  git commit                 -> staged files only
  git commit -a / -am        -> staged + modified tracked files
  git commit <pathspec>      -> staged + any named file that is a modified tracked file

Known limits, accepted deliberately: a commit executed against another repository
(`git -C other commit`, `cd other && git commit`) is judged against the wrong index,
and shell aliases that never spell "git commit" are not seen at all. This hook is a
seatbelt against accident, not a defence against a determined bypass.

Fails open on any internal error. NOTE: fail-open only covers errors *inside* this
script -- if the interpreter cannot start (bad path, no `python` on PATH) the exit
code is decided by the shell, which is why settings.json must invoke it through
${CLAUDE_PROJECT_DIR} rather than a cwd-relative path.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

# A git commit invocation, tolerating global options and odd spacing.
# The (?!-) tail keeps `git commit-tree` from matching.
COMMIT_RE = re.compile(r"\bgit\b[^;&|]*?\bcommit\b(?!-)")

# -a / -am / -ma / --all, but never --amend.
ALL_FLAG_RE = re.compile(r"(?<![-\w])-[a-zA-Z]*a[a-zA-Z]*\b|--all\b")

# Paths that must never be committed.
SECRET_FILE_RE = re.compile(
    r"(?:^|/)\.env(?:\.|$)"
    r"|\.(?:key|pem|p12|pfx|jks|keystore)$"
    r"|(?:^|/)(?:id_rsa|id_dsa|id_ecdsa|id_ed25519)$"
    r"|(?:^|/)\.(?:npmrc|pypirc|pgpass|netrc)$"
    r"|(?:^|/)credentials(?:\.json|\.ya?ml)?$",
    re.IGNORECASE,
)

# Placeholder files that share those names but carry no secret.
SECRET_FILE_ALLOW_RE = re.compile(r"(?:^|/)\.env\.(?:example|sample|template|dist)$", re.IGNORECASE)

# An assignment of a secret-looking name to a non-trivial value.
SECRET_VALUE_RE = re.compile(
    r"(api[_-]?key|api[_-]?secret|password|token|secret[_-]?key"
    r"|private[_-]?key|access[_-]?token)\s*[=:]\s*\S{8,}",
    re.IGNORECASE,
)


def _git(*args: str) -> str:
    """Run a git command, returning stdout ('' if git fails or is unavailable)."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def _git_lines(*args: str) -> list[str]:
    return [line for line in _git(*args).splitlines() if line]


def _is_secret_path(path: str) -> bool:
    return bool(SECRET_FILE_RE.search(path)) and not SECRET_FILE_ALLOW_RE.search(path)


def _candidate_paths(command: str) -> set[str]:
    """Paths this commit would actually include, across all three commit shapes."""
    paths = set(_git_lines("diff", "--cached", "--name-only"))
    modified = set(_git_lines("ls-files", "-m"))
    if ALL_FLAG_RE.search(command):
        paths |= modified
    else:
        # Explicit pathspec: only count tokens that are really modified tracked
        # files, so a commit *message* mentioning ".env" cannot trip the guard.
        tokens = {token.strip("\"'") for token in command.split()}
        paths |= modified & tokens
    return paths


def _candidate_diff(command: str) -> str:
    diff = _git("diff", "--cached", "-U0")
    if ALL_FLAG_RE.search(command):
        diff += _git("diff", "-U0")
    return diff


def _decide(decision: str, reason: str) -> None:
    """Emit a PreToolUse permission decision. stdout must hold only this JSON."""
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not COMMIT_RE.search(command):
        return 0

    offenders = sorted(path for path in _candidate_paths(command) if _is_secret_path(path))
    if offenders:
        _decide(
            "deny",
            "BLOCKED: refusing to commit secret-bearing files: "
            + ", ".join(offenders)
            + ". Unstage them (git restore --staged <file>) and add them to .gitignore.",
        )
        return 0

    hits = {m.group(1).lower() for m in SECRET_VALUE_RE.finditer(_candidate_diff(command))}
    if hits:
        _decide(
            "ask",
            "Possible hardcoded secret in the incoming diff (matched: "
            + ", ".join(sorted(hits))
            + "). Confirm this is a placeholder, an example value, or a test fixture.",
        )
        return 0

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - fail open, never wedge the Bash tool
        sys.exit(0)
