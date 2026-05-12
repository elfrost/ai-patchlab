---
name: retrospective
description: Run a self-healing retrospective in a fresh context after `execute-prp` (lite mode, target a specific PRP) or a broader sprint review (no argument). Surfaces AI-layer drift in CLAUDE.md, AGENTS.md, examples, skills, and agents and proposes concrete file edits. Always invoke from a NEW session — never the same context that produced the implementation.
---

# Retrospective

Identify systemic improvements to the AI layer (`CLAUDE.md`, `AGENTS.md`, `examples/`, `.claude/`, `.agents/skills/`, PRP templates, pipelines) so the same friction does not appear in the next implementation.

## Modes

The optional argument selects the mode:

- **Self-healing mode** — argument is `last`, a PRP file name, or a path under `PRPs/done/`. Focused review of one recent implementation. Run right after `execute-prp` finishes, in a fresh session.
- **Sprint mode** — no argument or `sprint`. Broad retrospective over the last ~2 weeks of git history.

## Prime Rule
Never run this skill in the same context that did the implementation. The implementer is biased about its own output. The whole point is fresh-context review.

## Self-Healing Workflow (one PRP)

1. **Identify the target**
   - If the argument is `last`, find the most recently archived PRP: `ls -t PRPs/done/ | head -1`
   - Otherwise treat the argument as a PRP name or path
   - Read the PRP completely

2. **Compare plan vs reality**
   - Run `git log --oneline --since="3 days ago" | head -20`
   - Run `git log --since="3 days ago" --name-only --pretty=format: | sort -u` to list changed files
   - Compare against the PRP's planned files; note deviations

3. **Find friction signals**
   - `fix:` commits right after `feat:` commits → implementation needed touch-ups, why?
   - Many small commits on the same file → instability, why?
   - Commits that revert or rework earlier work in the same PRP → planning gap, why?

4. **Diagnose root causes**
   For each painful moment, ask: what could we have put in `CLAUDE.md`, `AGENTS.md`, `examples/`, `.claude/commands/`, `.claude/agents/`, `.agents/skills/`, or PRP templates to prevent this?

   Common roots:
   - Missing rule or gotcha in `CLAUDE.md` / `AGENTS.md`
   - Missing pattern in `examples/` (had to invent something reusable)
   - Skill or command was too vague
   - Agent prompt missing context
   - PRP template missing a section
   - Validation gate not strict enough

5. **Output concrete AI-layer changes**
   ```
   ## Self-Healing Retrospective — [PRP name]

   ### Plan vs Reality
   - Files planned: X | Files actually changed: Y
   - Deviations: [list, or "none"]

   ### Friction signals
   - [Painful moment 1]
     - Root cause: [missing rule / pattern / etc.]
     - Fix: [exact change to file path]
   - [Painful moment 2] ...

   ### Proposed AI-layer changes
   - [ ] **[file path]** — [exact addition/edit]
   - [ ] **examples/[name].py** — [pattern to extract]
   - [ ] **.claude/commands/[name].md** — [step to add]
   - [ ] **.agents/skills/[name]/SKILL.md** — [parity edit if Claude side changed]

   ### What worked well (do NOT change)
   - [Aspect that went smoothly — keep as-is]
   ```

6. **Apply only after approval** — never silently edit AI-layer files.

## Sprint Workflow (no argument)

1. Read `ROADMAP.md` and `DECISIONS.md`
2. `git log --oneline -30 --since="2 weeks ago"` and grep for `feat:`, `fix:`, `refactor:` counts
3. List PRPs in `PRPs/done/` with dates
4. Run `ruff check src/` and `pytest tests/ -v --tb=no`
5. Most-modified files: `git log --since="2 weeks ago" --name-only --pretty=format: | sort | uniq -c | sort -rn | head -10`
6. Categorize improvements: process / code / docs / template / tech debt
7. Output the "Rétrospective" report covering Résumé, Ce qui a marché, Ce qui était difficile, and the five categorized improvement buckets

## Rules
- Be specific — name files and exact edits, not vague suggestions
- Only flag an improvement if you can name the next bug it prevents
- If nothing went wrong, say "Implementation was clean, no AI-layer changes needed" and stop
- Never silently edit `CLAUDE.md`, `AGENTS.md`, examples, skills, or agents
- Maintain Claude/Codex parity — when proposing a `.claude/` edit, propose the matching `.agents/skills/` edit too
