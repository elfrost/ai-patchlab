---
name: audit-project
description: Audit the project runtime docs and scaffolding for drift or missing setup. Use when the user asks for a project audit, wants AGENTS or CLAUDE cleaned up, or needs to check whether the repository still matches EzProject conventions.
---

# Audit Project

Audit the project instructions and supporting scaffold, then propose precise updates.

## Workflow
1. Read:
   - `AGENTS.md`
   - `CLAUDE.md` if present
   - `ROADMAP.md`
   - `DECISIONS.md`
   - `README.md`
   - `.ezproject.json` if present
2. Explore the codebase, dependencies, test setup, MCP config, and project structure.
3. Score the runtime docs on:
   - project context
   - directory map
   - coding standards
   - common commands
   - testing guidance
   - architecture notes
   - gotchas
4. Write `AGENTS.md.proposed` when the current document needs improvement.
5. If `CLAUDE.md` exists and is out of sync, call that out and propose matching updates.
6. Report missing EzProject infrastructure and suggest what should be installed or refreshed.

## Rules
- Do not overwrite runtime docs without confirmation.
- Preserve project-specific details that are already correct.
- Be direct about weak sections or stale content.
