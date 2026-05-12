---
name: ez-project-workflow
description: Apply the EzProject operating workflow to any coding task in this repository or an EzProject-generated project. Use for implementation, debugging, refactoring, planning, or review work when Codex should read shared project context, follow PRP discipline, and keep ROADMAP, DECISIONS, AGENTS, README, and CLAUDE in sync.
---

# EzProject Workflow

Use this skill as the default operating guide for work inside an EzProject repository.

## Workflow
1. Read `AGENTS.md` first.
2. Read `ROADMAP.md` and `DECISIONS.md`.
3. Check `PRPs/` and `INITIAL.md` when the task is feature-related.
4. Read `examples/` before implementing new patterns.
   If this is the template repo, use `template/examples/`.
5. If `CLAUDE.md` exists, treat it as a sibling runtime document that must stay aligned with structural and workflow changes.
6. Validate changes with the smallest useful loop before moving on.
7. Finish with documentation sync:
   - `ROADMAP.md`
   - `DECISIONS.md` when architecture changed
   - `AGENTS.md`
   - `CLAUDE.md` if present
   - `README.md` if setup or usage changed

## Rules
- Prefer existing project patterns over new abstractions.
- Keep file paths and references concrete.
- Do not leave PRPs, docs, or runtime instructions stale.
- When the repo contains both `.claude/` and `.agents/`, preserve parity instead of merging the systems together.
