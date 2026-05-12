Audit and optimize the CLAUDE.md file for this project.

## Process

### Phase 0: Delegate discovery to smart-context

Before reading anything yourself, spawn the `smart-context` subagent. It runs on opus and produces a structured drift report comparing CLAUDE.md to the actual project state:
- New directories not listed in Key Directories
- New dependencies not in Tech Stack
- Conventions detected in code that aren't documented
- Stale entries (references to files/dirs that no longer exist)
- Gotchas discovered from git log + TODO/FIXME/HACK comments
- Slash commands present in `.claude/commands/` but missing from CLAUDE.md

Use the Task tool with `subagent_type: "smart-context"` and pass it the directive: "Compare CLAUDE.md to actual project state and produce a drift report. Do NOT apply changes yet — just report findings."

The smart-context agent may also write `CLAUDE.md.proposed` with concrete edits. If it does, treat that file as your starting point for Phase 3 synthesis (don't redo the work — refine it).

### Phase 1: Read Current State

1. Read CLAUDE.md yourself (the smart-context brief covers drift, but you still need the full text for scoring criteria below)
2. If `AGENTS.md` exists, read it too and look for runtime drift
3. Skim the codebase only to fill scoring gaps that smart-context did not cover:
   - What language/framework is used
   - Test setup (if any)
   - Database schema (if any)
   - Common commands used (Makefile, scripts/, package.json scripts)
4. Check if these files exist and what's in them:
   - AGENTS.md
   - ROADMAP.md
   - .env.example
   - .mcp.json
   - .claude/settings.local.json
   - .claude/commands/*
   - .claude/agents/*
   - .agents/skills/*
   - examples/

### Phase 2: Score the Current CLAUDE.md

Rate the existing CLAUDE.md on these criteria (1-10 each):

| Criteria | Description |
|----------|-------------|
| **Project Context** | Does it explain what the project IS and does? |
| **Directory Map** | Does it list key directories and their purpose? |
| **Coding Standards** | Are naming, style, and patterns documented? |
| **Common Commands** | Are dev/test/build commands listed? |
| **Database Conventions** | Schema, naming, query patterns documented? |
| **Error Handling** | Are error handling expectations clear? |
| **Testing Standards** | Test framework, patterns, and expectations? |
| **Git Workflow** | Branch naming, commit format, PR process? |
| **Architecture Decisions** | Key design decisions documented? |
| **Gotchas & Warnings** | Known issues and pitfalls captured? |

### Phase 3: Generate Recommendations

Based on the audit, provide:

1. **OVERALL SCORE: X/100**

2. **Missing sections** that should be added (with suggested content based on what you found in the codebase)

3. **Weak sections** that need more detail

4. **Outdated content** that doesn't match the current codebase

5. **Suggested CLAUDE.md** — write a complete, optimized version to `CLAUDE.md.proposed`
6. **Suggested AGENTS.md** — if `AGENTS.md` exists and is stale, write an aligned version to `AGENTS.md.proposed`

### Phase 4: Check Infrastructure

Report what's missing from the project and suggest adding:

```
Infrastructure Checklist:
[ ] .claude/commands/generate-prp.md    — Slash command pour PRP
[ ] .claude/commands/execute-prp.md     — Slash command pour exécution
[ ] .claude/commands/review-code.md     — Slash command pour review
[ ] .claude/agents/researcher.md        — Subagent recherche
[ ] .claude/agents/code-reviewer.md     — Subagent review
[ ] .claude/agents/tester.md            — Subagent tests
[ ] .claude/settings.local.json         — Permissions + hooks
[ ] AGENTS.md                           — Codex/OpenAI runtime instructions
[ ] .agents/skills/                     — Codex skills for repeatable workflows
[ ] .mcp.json                           — MCP servers
[ ] PRPs/templates/prp_base.md          — PRP template
[ ] examples/                           — Code patterns de référence
[ ] ROADMAP.md                          — Suivi de progression
[ ] .env.example                        — Template variables d'env
```

For each missing item, ask:
"Veux-tu que j'installe [item]? Je peux le copier du template EzProject."

## Output

Present findings conversationally in French, then ask:
"Voici mon audit. Veux-tu que j'applique les changements recommandés?
1. Remplacer CLAUDE.md par la version optimisée
2. Ajouter les fichiers d'infrastructure manquants
3. Les deux
4. Laisse-moi réviser d'abord"

## IMPORTANT
- Do NOT overwrite CLAUDE.md without confirmation
- Write proposed version to CLAUDE.md.proposed
- If AGENTS.md exists and needs changes, write AGENTS.md.proposed instead of overwriting it
- Preserve any project-specific content that's already correct
- Be honest about what's weak — don't sugarcoat
