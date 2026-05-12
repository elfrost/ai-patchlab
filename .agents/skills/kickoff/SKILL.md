---
name: kickoff
description: Run the EzProject feature kickoff interview, then update INITIAL, ROADMAP, README, DECISIONS, AGENTS, and CLAUDE when present. Use when the user starts a new feature, project direction, or major initiative and wants the shared project documents populated before planning.
---

# Kickoff

Run a short interview, one question at a time, then update the project docs from the answers.

## Workflow
1. Read `.ezproject.json` if it exists to detect mode and stack.
   - If `stack` is `auto` (with `stack_pending: true`), set `STACK_PENDING = true`, skip the stack question, and run the **Stack Advisor** step (5) after the interview.
2. Interview the user one question at a time:
   - what they want to build
   - why it matters and who uses it
   - core stack and data sources (skip stack question if `STACK_PENDING`)
   - outputs, constraints, MVP scope, environment
3. Read:
   - `AGENTS.md`
   - `CLAUDE.md` if present
   - `ROADMAP.md`
   - `README.md`
   - `DECISIONS.md`
   - `examples/` or `template/examples/`
4. Update all relevant files:
   - `INITIAL.md`
   - `ROADMAP.md`
   - `README.md`
   - `AGENTS.md`
   - `CLAUDE.md` if present
   - `DECISIONS.md` if new architecture decisions were made (always add an ADR for the stack choice when STACK_PENDING was true)
5. **Stack Advisor (only if STACK_PENDING):** score the answers (Q1/Q4/Q5/Q7) against the 4 stacks and recommend one with concrete justification.
   - Stacks: `data` (parsing, ETL, scrape→DB/sheet), `api` (REST endpoints), `ai-agent` (LLM agents, MCP), `web` (server-rendered UI).
   - Watch for hybrids (e.g., statements→sheet with auto-categorize = `data` + `ai-agent` patterns). Pick a primary, optionally a secondary for cherry-picked patterns.
   - Wait for user confirmation, then run:
     ```bash
     EZ_ROOT=$(python -c "import json; print(json.load(open('.ezproject.json'))['ezproject_root'])")
     powershell -ExecutionPolicy Bypass -File "$EZ_ROOT/ez-finalize-stack.ps1" -ProjectPath "$(pwd)" -Stack <chosen>
     ```
   - For hybrids, also `cp "$EZ_ROOT/template/examples/<secondary>/<file>.py" examples/` (1-2 files max).
6. Present the generated scope and ask for confirmation before moving on to PRP generation.

## Rules
- Ask one question at a time.
- Keep the conversation in French unless the user asks otherwise.
- Keep generated file content in English for portability.
- Remove placeholders instead of leaving them behind.
- Keep the MVP concrete and small.
- If STACK_PENDING and the user pushes back on the recommendation, listen — they know their context better than the heuristics.
