Generate a complete PRP (Product Requirements Prompt) for feature implementation with thorough research.

Read the feature file first: $ARGUMENTS

## Your Task

You are generating a PRP — a comprehensive implementation blueprint that another AI agent (or yourself in a new session) will use to implement this feature in ONE PASS.

The agent only gets the context in the PRP + the codebase. It does NOT have your conversation history. So the PRP must be SELF-CONTAINED.

## Phase 0: Discovery Triage (Understanding Lock)

Before research, assess the feature file. If it is **clear, scoped, and unambiguous**, skip directly to the Research Phase.

If at least 2 of these are true, enter **Understanding Lock** mode:
- The feature file is shorter than 10 lines or vague ("add X feature")
- Critical aspects are missing: target users, success criteria, non-goals, scale, security/privacy constraints
- Multiple plausible interpretations would lead to very different implementations
- The feature touches data, auth, money, or external integrations without specs

**Understanding Lock rules:**
1. Ask **one question at a time** — never batch.
2. Prefer **multiple-choice** questions over open-ended ones (faster for the user).
3. Cover in order: **purpose → target users → success criteria → non-goals → constraints (perf/scale/security)**.
4. After ≤5 questions, write an **Understanding Summary** (5-7 bullets, list assumptions + open questions) and **wait for explicit confirmation** before proceeding.
5. Once confirmed, fold the answers back into the feature file (or a `[feature]-clarified.md` next to it) and continue to Research Phase.

The hard gate: do NOT generate the PRP until the user has explicitly confirmed the Understanding Summary. This prevents "implemented the wrong thing perfectly" — the most expensive failure mode.

## Phase 1: Delegate Research (Token-Efficient)

Do NOT do the codebase research yourself in this context window. Spawn the `researcher` subagent — it runs on a cheaper model (sonnet) and returns a compact structured brief, keeping your main context free for synthesis.

**How to invoke:**
Use the Task tool with `subagent_type: "researcher"`. Pass it:
- The full feature file content (read from `$ARGUMENTS`)
- An explicit directive listing what you need:
  - Existing patterns in `examples/` and `src/` that this feature should follow
  - Files likely to be modified (with paths)
  - Relevant ADRs from `DECISIONS.md` and gotchas from `CLAUDE.md`
  - Recent related git history
  - External docs/libraries needed (WebSearch if applicable)
  - Confidence score with justification

**Hard gate on the returned brief:**
- If `Confidence < 7`: do NOT proceed to PRP writing. Either (a) ask the user for clarification on the specific gaps the researcher flagged, or (b) delegate a follow-up research pass focused only on the unknowns.
- If `Confidence >= 7`: continue to Phase 2.

**Why delegate (Karpathy-style context engineering):**
- Heavy file-reading happens on sonnet → cheaper tokens
- Your main context (opus) stays lean for the actual synthesis work — designing the PRP architecture
- The researcher already structures its output (Sources / Findings / Architecture Impact / Risks / Recommendation) — perfect input for a PRP

## Phase 2: Verify Before You Cite

Before writing anything into the PRP's MUST READ or Files to Modify sections, verify each candidate the researcher flagged:

1. **File existence** — `test -f path` for each MUST READ candidate. If a file doesn't exist, drop it from the brief or replace it with the correct path.
2. **Content sanity** — open each file briefly, confirm the pattern claim still matches (file may have been refactored since the researcher's last context).
3. **Project docs alignment** — read CLAUDE.md, DECISIONS.md, ROADMAP.md yourself only if the researcher's summary missed something critical. Otherwise trust the brief.
4. **External URLs** — if external docs are referenced, ensure they're load-bearing for the implementation, not just background.

This catches stale recommendations before they propagate into a PRP that someone else will execute.

## *** CRITICAL ***
*** ULTRATHINK ABOUT THE PRP AND PLAN YOUR APPROACH BEFORE YOU START WRITING ***
*** Synthesize from the verified brief — NOT from raw file dumps re-read into your context ***

## PRP Structure

Write the PRP to `PRPs/<feature-name>.md` using the template from `PRPs/templates/prp_base.md`.

Key sections:

```markdown
# PRP: [Feature Name]

## Overview
[What needs to be built — specific end state]

## Dependencies
- Requires: [other PRPs/features this depends on, or "none"]
- Blocks: [PRPs/features that are waiting on this, or "none"]

## Context & References
### MUST READ — Include these in your context window
- file: [path/to/example.py] — why: [pattern to follow]
- file: `DECISIONS.md` — why: past decisions
- url: [docs URL] — why: [specific sections needed]
- doc: [library docs] — section: [relevant part]

### Critical Gotchas
- [Library X requires specific setup Y]
- [API Z has rate limit of N/second]
- [Database constraint: ...]

## Architecture
### Files to Create
- `src/module/file.py` — [purpose]

### Files to Modify
- `src/existing.py` — [what changes and why]

### Database Changes
- [New tables, columns, indexes — with migration SQL including date comment]

## Implementation Plan

### Task 1: [Name]
**Goal:** [What this accomplishes]
**Files:** [Files to create/modify]
**Details:**
- Step-by-step instructions
- Code patterns to follow (reference examples/)
- Expected behavior

**Validation:**
```bash
[Command to verify this task works]
```

### Task 2: [Name]
[Same structure...]

## Validation Loop
After ALL tasks are complete, run:
```bash
ruff check src/
black --check src/
pytest tests/ -v
python -m src.main  # or appropriate smoke test
```

Fix any failures and re-run until ALL pass.

## Success Criteria
- [ ] [Specific measurable outcome 1]
- [ ] [Specific measurable outcome 2]
- [ ] All tests pass
- [ ] No lint errors
- [ ] ROADMAP.md updated
- [ ] DECISIONS.md updated (if applicable)

## PRP Quality Checklist
- [ ] All referenced files exist
- [ ] Each task has a validation command
- [ ] DB changes have migration SQL with date
- [ ] Dependencies section filled
- [ ] Confidence >= 7
```

## Quality Check

Before saving the PRP, run this automated checklist:

### Automated Validation
1. **File references exist?** — For each file in "MUST READ", verify it exists:
   ```bash
   test -f "path/to/file" && echo "OK" || echo "MISSING: path/to/file"
   ```
2. **All tasks have validation commands?** — Every Task section MUST have a `Validation:` block
3. **Database changes include migration SQL?** — If DB changes exist, SQL must have a `-- Migration: YYYY-MM-DD` comment
4. **Dependencies section is filled?** — Either list dependencies or explicitly write "none"
5. **No orphan references?** — Don't reference files/modules that don't exist yet without specifying their creation

### Subjective Check
1. Is ALL necessary context included (no assumptions)?
2. Are file paths specific and correct?
3. Are examples referenced for each pattern?
4. Could an agent implement this WITHOUT asking questions?

Score the PRP on a scale of 1-10 (confidence level for one-pass implementation).
If score < 7, add more context until it reaches 7+.

Remember: The goal is ONE-PASS implementation success through COMPREHENSIVE context.

## Next Step

After the PRP is saved with confidence >= 7, end the conversation with this exact message:

```
PRP saved to PRPs/<name>.md (confidence: X/10).

**Next step:** open a NEW conversation and run:
  /execute-prp PRPs/<name>.md

Per ADR-013, /execute-prp must run in a fresh context window. The implementer cannot review its own work objectively at the end if it sees the conversation that produced the PRP ("kid grading own homework").

Other useful commands at this stage:
- `/next` — context-aware advice if you want to do something else first
- `/architect` (subagent) — if you want a second opinion on the design before implementing
```
