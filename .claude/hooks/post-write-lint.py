#!/usr/bin/env python3
"""PostToolUse hook: run ruff --fix and black on a Python file Claude just wrote.

Replaces an inline shell one-liner that tested `$CLAUDE_FILE`, a variable Claude Code
does not define -- confirmed against the hooks documentation, which lists
CLAUDE_PROJECT_DIR, CLAUDE_PLUGIN_ROOT, CLAUDE_PLUGIN_DATA and CLAUDE_EFFORT, and no
CLAUDE_FILE. The test was therefore always false and the formatter never ran, on every
generated project, since the hook was introduced. The written path is in the hook's
stdin payload as tool_input.file_path.

Non-enforcing by design: this is a convenience, not a policy gate. It always exits 0,
never emits a permissionDecision, and stays silent when ruff/black are not installed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _run(tool: str, *args: str) -> None:
    """Run a formatter if it is on PATH; swallow every failure."""
    exe = shutil.which(tool)
    if not exe:
        return
    try:
        subprocess.run([exe, *args], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    raw_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not raw_path:
        return 0

    path = Path(raw_path)
    if path.suffix.lower() != ".py" or not path.is_file():
        return 0

    # Stay inside the project: a hook that reformats files elsewhere on the disk is a
    # surprise the user never asked for.
    project_dir = payload.get("cwd") or ""
    if project_dir:
        try:
            path.resolve().relative_to(Path(project_dir).resolve())
        except (ValueError, OSError):
            return 0

    _run("ruff", "check", "--fix", "--quiet", str(path))
    _run("black", "--quiet", str(path))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a formatter must never break the tool call
        sys.exit(0)
