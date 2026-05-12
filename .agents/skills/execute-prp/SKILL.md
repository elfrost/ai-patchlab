---
name: execute-prp
description: Implement a PRP end to end with validation and mandatory documentation sync. Use when the user asks to execute a PRP, build a planned feature, implement a spec from PRPs/, or carry a planned change through coding, tests, and housekeeping.
---

# Execute PRP

Implement the PRP exactly, validate each stage, then sync the shared project documents.

## Workflow
1. Read the PRP completely.
2. Read:
   - `AGENTS.md`
   - `CLAUDE.md` if present
   - `DECISIONS.md`
   - every file referenced by the PRP
   - `examples/` or `template/examples/`
3. Confirm pre-flight checks:
   - referenced files exist
   - each task has validation
   - required dependent PRPs are complete
4. Break the work into concrete tasks and execute them in order.
5. After each major task:
   - run the task validation command
   - fix failures before continuing
6. After all tasks, run the full validation loop from the PRP.
7. Perform mandatory housekeeping:
   - update `ROADMAP.md`
   - update `DECISIONS.md` if architecture changed
   - update `AGENTS.md`
   - update `CLAUDE.md` if present
   - update `README.md` if setup or usage changed
   - archive the PRP into `PRPs/done/` with a date prefix
   - remove scratch files
8. Output a self-healing handoff message and STOP. Do NOT run a retrospective in this same conversation:
   ```
   PRP [name] complete. Housekeeping done.

   Recommended next step in a SEPARATE session:
     retrospective last      (or: retrospective <prp-name>)

   Reason: the implementer is biased about its own work. A fresh context
   surfaces AI-layer drift (CLAUDE.md, AGENTS.md, examples, skills, agents)
   and proposes concrete edits to prevent the same friction next time.
   ```

## Rules
- Do not skip validation.
- Do not leave docs stale after implementation.
- Keep commits focused if you commit, but do not force commits when the user did not ask.
- Treat `AGENTS.md` and `CLAUDE.md` as sibling runtime documents when both exist.
- NEVER run the `retrospective` skill in the same context that did the implementation — recommend it only.
