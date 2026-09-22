#!/usr/bin/env python3
"""SessionStart hook: load WORKING-CONTEXT.md if present and inject it as
additional context. Non-blocking — silent when the file is missing or empty.

Pattern adapted from everything-claude-code (affaan-m/everything-claude-code):
preserves in-progress state across session restarts and context compactions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass

    ctx = Path("WORKING-CONTEXT.md")
    if not ctx.exists():
        return 0

    content = ctx.read_text(encoding="utf-8").strip()
    if not content:
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "# Working Context (auto-loaded from WORKING-CONTEXT.md)\n\n"
                + content
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
