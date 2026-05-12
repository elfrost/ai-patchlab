---
name: status
description: Produce a compact EzProject status snapshot. Use when the user asks for project status, a session-start dashboard, a quick repo health check, or an overview of roadmap, git state, and validation state.
---

# Status

Produce a concise dashboard of the current project state.

## Workflow
1. Read `ROADMAP.md`, `DECISIONS.md`, and `INITIAL.md`.
2. Inspect git state:
   - `git status --short`
   - recent commits
   - current branch
3. Run lightweight health checks when available:
   - `ruff check`
   - `black --check`
   - `pytest`
4. Report:
   - roadmap counts
   - branch and last commit
   - codebase size
   - validation state
   - warnings that need attention
   - suggested next step

## Rules
- Keep it compact.
- Surface uncommitted changes clearly.
- If validation fails, summarize only the key failure lines.
