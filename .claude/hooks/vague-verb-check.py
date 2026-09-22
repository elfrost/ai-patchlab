#!/usr/bin/env python3
"""UserPromptSubmit hook: detect vague verbs and inject a reminder to define
verifiable success criteria before acting. Non-blocking — exits 0 always.

Adapted from Karpathy CLAUDE.md guidelines (forrestchang/andrej-karpathy-skills).
"""
from __future__ import annotations

import json
import re
import sys

VAGUE_VERBS = (
    "fix", "improve", "refactor", "clean up",
    "optimize", "polish", "enhance", "make it better",
)

REMINDER = (
    "Vague verb detected in user prompt. Before acting, restate the task as a "
    "verifiable success criterion (what observable state proves it's done?) and "
    "surface any assumption you're about to make. If unclear, ask one targeted "
    "question instead of guessing."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    prompt = (payload.get("prompt") or "").lower()
    if not prompt:
        return 0

    pattern = r"\b(" + "|".join(re.escape(v) for v in VAGUE_VERBS) + r")\b"
    if not re.search(pattern, prompt):
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": REMINDER,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
