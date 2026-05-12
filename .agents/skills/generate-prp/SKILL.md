---
name: generate-prp
description: Generate a self-contained PRP from INITIAL.md or another feature spec. Use when the user asks to generate a PRP, create an implementation plan, turn a feature request into a one-pass blueprint, or prepare work for later execution.
---

# Generate PRP

Create a complete Product Requirements Prompt that another agent can execute without the current conversation history.

## Phase 0: Discovery Triage (Understanding Lock)

Before research, assess the feature file. If it is clear, scoped, and unambiguous, skip directly to step 1.

Enter Understanding Lock mode if at least 2 of these are true:
- The feature file is short or vague
- Critical aspects are missing (target users, success criteria, non-goals, constraints)
- Multiple plausible interpretations would lead to very different implementations
- Feature touches data, auth, money, or external integrations without specs

Rules in Understanding Lock:
- One question at a time, prefer multiple-choice
- Cover purpose -> users -> success criteria -> non-goals -> constraints
- After at most 5 questions, write a 5-7 bullet Understanding Summary with assumptions and open questions
- Wait for explicit user confirmation before continuing
- Fold the answers back into the feature file or a `[feature]-clarified.md` sibling

Hard gate: do NOT generate the PRP until the Understanding Summary is confirmed.

## Workflow

### Step 1: Read the feature file
Read the feature file the user points to. If none is given, default to `INITIAL.md`.

### Step 2: Multi-source research (filter -> rank -> synthesize)
Codex does not have a subagent delegation primitive like Claude, so the executing model does the research itself — but applies the same discipline:

**Filter** — only read what is plausibly relevant to this feature, not every file in every directory:
- `AGENTS.md`
- `CLAUDE.md` if present
- `DECISIONS.md` (skim ADR titles, read in full only the ones touching the feature area)
- `ROADMAP.md` (current state only)
- `PRPs/` (only PRPs marked as dependencies or recently completed in the same area)
- `examples/` or `template/examples/` (only the patterns matching the feature's stack)
- Relevant codebase files (grep first, read second)

**Rank** — prioritize sources by signal-to-noise:
1. Files the feature explicitly references
2. Examples matching the same pattern (api, data, ai-agent, web)
3. Recent git history in affected directories
4. ADRs touching the same architectural area

**Synthesize** — keep an internal compact brief (5-10 bullets) before writing the PRP. Do not paste raw file content into the PRP — extract the load-bearing fact and cite the path.

### Step 3: Verify before citing
Before writing anything into the PRP's must-read or files-to-modify sections:
- Confirm each cited file exists at the path used
- Confirm the pattern claim still matches by reopening the file briefly
- Drop any reference that fails verification

### Step 4: Build the PRP
Use `PRPs/templates/prp_base.md` when available.
If this is the template repo, fall back to `template/PRPs/templates/prp_base.md`.

Produce `PRPs/<feature-name>.md` with:
- overview and dependencies
- must-read files and docs
- critical gotchas
- files to create and modify
- database changes if any
- ordered tasks with validation commands
- final validation loop
- success criteria

### Step 5: Quality gate
Verify the PRP before finishing:
- Referenced files exist
- Every task has validation
- Dependencies are explicit
- Confidence is at least 7/10
- If confidence is below 7, do NOT save — either ask the user clarifying questions or expand research on the specific gaps

## Rules
- Make the PRP self-contained.
- Prefer exact file paths over vague descriptions.
- Include shared-document sync in success criteria:
  - `ROADMAP.md`
  - `DECISIONS.md` if applicable
  - `AGENTS.md`
  - `CLAUDE.md` if present
- Do not start implementation in this skill.
