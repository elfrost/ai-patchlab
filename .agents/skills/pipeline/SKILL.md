---
name: pipeline
description: Execute a predefined or custom pipeline workflow defined in `.claude/pipelines/*.yml`. Codex walks the steps inline since it has no subagent primitive. Use when the user wants to run a sequenced workflow like `pipeline feature` or `pipeline release`.
---

# Pipeline

Execute a YAML-defined workflow step by step. Each `type: agent` step is executed by reading the corresponding agent's prompt at `template/.claude/agents/<agent>.md` and following it inline.

## Phase 1: Load
1. Parse `$ARGUMENTS` for pipeline name (first word) and input (rest)
2. Look for the pipeline file in: `.claude/pipelines/<name>.yml` then `.yaml`
3. If not found, list available pipelines and ask the user to choose
4. Parse the YAML
5. Check the `mode` field — if it requires `project` mode, verify `.ezproject.json#mode` matches; warn if not

## Phase 2: Show plan
Display the steps in order with a table (id, type, agent, depends_on). Highlight gates (human approval) and ask for confirmation before executing.

## Phase 3: Execute
Walk steps in dependency order. For each step:

- **type: agent** — read `.claude/agents/<agent>.md` (or project-mode equivalent at `project-mode/.claude/agents/`), follow that agent's process inline using its prompt. Substitute `{{step_id.output}}` with previous step outputs and `{{input}}` with the user's input. Capture the output.
- **type: command** — invoke the corresponding skill described in `.agents/skills/<name>/SKILL.md`.
- **type: validation** — run each command in `commands` list. Retry up to `retry` count if any fail. If still failing, STOP and ask the user.
- **type: gate** — show the message and ask the user. Stop gracefully on rejection.
- **type: summary** — collect previous step outputs and produce a structured summary.

## Phase 4: Report
Produce a final report:
- Steps table with status per step
- Summary
- Suggested next actions

## Rules
- Always show the execution plan and get approval before running
- Always respect dependency order
- If a gate is rejected, stop gracefully
- Do not skip ahead to dependent steps if a predecessor failed
- Without subagent isolation, run agent steps sequentially even if Claude would parallelize them
