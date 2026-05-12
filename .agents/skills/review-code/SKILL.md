---
name: review-code
description: Review the current diff or target files using EzProject quality rules. Use when the user asks for a code review, audit of recent changes, or a bug-risk-focused pass over modified files before merge or release.
---

# Review Code

Review changes with bugs, regressions, risks, and missing tests as the primary focus.

## Workflow
1. Read `AGENTS.md`.
2. Read `CLAUDE.md` if present for cross-runtime expectations.
3. Review the current git diff. If the user names files, review those too.
4. Check:
   - correctness and regressions
   - missing validation or tests
   - pattern drift from `examples/`
   - documentation drift for `ROADMAP.md`, `DECISIONS.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`
5. Run lightweight validation when it materially supports the review.

## Output
- Findings first, ordered by severity, with file references
- Open questions or assumptions
- Brief summary only after findings

## Rules
- Prefer concrete defects over style commentary.
- If no findings are discovered, say so explicitly and mention residual risk or testing gaps.
- Call out documentation drift when code changed but shared docs did not.
