---
name: create-skill
description: Create a new project-local Codex skill under .agents/skills and wire it into the EzProject workflow. Use when the user wants a repeatable Codex skill for project-specific work, custom automation, or a reusable review/build/deploy workflow.
---

# Create Skill

Create a focused project-local Codex skill that matches EzProject conventions.

## Workflow
1. Derive a hyphen-case skill name from the user's request.
2. Read:
   - `AGENTS.md`
   - `CLAUDE.md` if present
   - existing `.agents/skills/*/SKILL.md`
   - related examples or project files
3. Design the skill:
   - purpose
   - trigger wording
   - required workflow
   - optional scripts or references
4. Create `.agents/skills/<skill-name>/SKILL.md`.
5. Update `AGENTS.md` to list the new skill.
6. If the repository also uses Claude, note whether a matching `.claude` command should be created for parity.

## Rules
- Keep the skill narrow and reusable.
- Use the EzProject docs as the source of truth for conventions.
- Do not overwrite an existing skill without confirmation.
