Implement a feature using the PRP file: $ARGUMENTS

## Instructions

1. **Read the PRP file completely** — it contains everything you need
2. **Read CLAUDE.md** — follow all project rules
3. **If AGENTS.md exists, read it too** — keep Codex/OpenAI runtime docs aligned in parallel projects
4. **Read DECISIONS.md** — understand past architectural decisions
5. **Read all referenced files** in the PRP's "Context & References" section
6. **Read examples/** that are referenced in the PRP

## Pre-Flight Check

Before implementing, verify:

1. **PRP quality checklist passes:**
   - All referenced files exist
   - Each task has a validation command
   - Dependencies section is filled

2. **Dependencies are met:**
   - If the PRP has a "Dependencies > Requires" section, check that those PRPs are in `PRPs/done/`
   - If dependencies are NOT met, STOP and warn: "Ce PRP dépend de [X] qui n'est pas encore complété."

## Planning

Think hard before you execute the plan.

- Create a comprehensive plan addressing ALL requirements from the PRP
- Break down complex tasks into smaller, manageable steps using your todos tools
- Use the TodoWrite tool to create and track your implementation plan
- Identify implementation patterns from existing code to follow

## Execution

For each task in the PRP:

1. **Implement** the task following the PRP instructions exactly
2. **Validate** using the validation command specified in the task
3. **Fix** any issues before moving to the next task
4. **Commit** after each major task: `git add [specific files] && git commit -m "feat: [task description]"`

## After ALL Tasks

Run the full validation loop from the PRP:

```bash
ruff check src/
black --check src/
pytest tests/ -v
```

If validation fails, use error patterns in the PRP to fix and retry.
Keep iterating until ALL validations pass.

## Final Steps: Housekeeping (MANDATORY — do NOT skip)

After all tasks pass validation, perform a FULL documentation sync:

### 1. Update ROADMAP.md
- Read ROADMAP.md
- Mark completed items with `[x]` and today's date
- Mark in-progress items with `[-]` and today's date
- Add any new items discovered during implementation

### 2. Update DECISIONS.md
- If any architectural decisions were made during implementation, add new ADR entries
- Format: `ADR-XXX: [title]` with Date, Status, Decision, Context, Consequences

### 3. Update CLAUDE.md
- Check if any of these changed during implementation:
  - New directories or files created → update Key Directories section
  - New dependencies added → update Tech Stack section
  - New gotchas discovered → update Known Gotchas section
  - New architecture decisions → update Architecture Decisions section
- Do NOT rewrite the whole file — only update sections that actually changed

### 4. Update README.md
- If new setup steps, commands, dependencies, or env vars were added, update README.md
- Keep it accurate with the current state of the project

### 4b. Update AGENTS.md if it exists
- Mirror the structural, dependency, command, and gotcha updates made to CLAUDE.md
- Keep both runtime docs aligned without merging them together

### 5. Archive PRP
- Move the completed PRP: `mv PRPs/[feature].md PRPs/done/$(date +%Y%m%d)-[feature].md`
  - On Windows: `move PRPs\[feature].md PRPs\done\[date]-[feature].md`

### 6. Clean up temp files
- Delete any scratch/temp files created during implementation
- Remove `__pycache__/` if present

### 7. Final commit
```bash
git add ROADMAP.md DECISIONS.md CLAUDE.md README.md PRPs/
# If present: git add AGENTS.md
git commit -m "docs: update documentation after [feature name]"
```

If there are also code changes not yet committed:
```bash
git add [specific source files]
git commit -m "feat: complete [feature name]"
```

### 8. Self-Healing Handoff (recommend, do NOT execute here)

The implementer (this conversation) is biased about its own work — never review your own implementation in the same context window where you wrote it.

After housekeeping, output this handoff message and STOP:

```
✅ PRP [name] terminé.
✅ Housekeeping terminé.

Prochaine étape recommandée — dans une CONVERSATION SÉPARÉE :
  /retrospective last        # ou /retrospective <prp-name>

Pourquoi en contexte frais : un implémenteur est biaisé sur son propre travail
(c'est l'enfant qui corrige son propre devoir). Une session vierge attrape les
frictions et propose des correctifs systémiques au "AI layer" (CLAUDE.md,
skills, examples, agents) pour éviter que le même problème revienne.
```

Do NOT run `/retrospective` yourself in this conversation. Just leave the recommendation.

## IMPORTANT
- Do NOT skip validation steps
- Do NOT skip the housekeeping steps — documentation MUST stay in sync with code
- Do NOT assume — if something is unclear, check the PRP and examples
- Keep things SIMPLE — follow the PRP, don't over-engineer
- If a task seems too complex, break it down further before implementing
- NEVER leave documentation out of sync with the code after a PRP execution
- NEVER run the self-healing retrospective in the same context that did the implementation
