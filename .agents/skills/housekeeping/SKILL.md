---
name: housekeeping
description: Sync shared project docs after implementation work and clean temporary artifacts. Use when the user asks for housekeeping, doc sync, cleanup after a feature, or wants ROADMAP, DECISIONS, AGENTS, README, and CLAUDE updated to match the codebase.
---

# Housekeeping

Run the post-implementation sync pass that keeps project state documents accurate.

## Workflow
1. Read `ROADMAP.md`, recent git history, and the changed files.
2. Update `ROADMAP.md` statuses with the current date where appropriate.
3. Update `AGENTS.md` when structure, commands, dependencies, or gotchas changed.
4. If `CLAUDE.md` exists, update the matching sections there too.
5. Update `README.md` if setup, usage, or dependencies changed.
6. Update `DECISIONS.md` if new architectural decisions were made.
7. Remove obvious temporary artifacts such as:
   - `*.pyc`
   - `__pycache__/`
   - `*.proposed`
   - scratch files created during the task
8. Show the resulting git state.
9. If the housekeeping ran after a non-trivial implementation, append this self-healing reminder to the output (do NOT execute):
   ```
   Self-healing pending — recommend running in a SEPARATE session:
     retrospective last

   Catches AI-layer drift the implementer can't see from inside its own context.
   Skip if the implementation was trivial.
   ```

## Rules
- Keep documentation edits minimal and concrete.
- Never delete source files as part of cleanup.
- If a deletion is ambiguous, ask before removing it.
- NEVER run the `retrospective` skill from inside `housekeeping` — it must be a fresh context.
