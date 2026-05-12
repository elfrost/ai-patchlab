# /pipeline — Execute a Pipeline

Execute a predefined or custom pipeline workflow.

## Argument
`$ARGUMENTS` — Pipeline name (required) + optional input context.
Format: `<pipeline-name> [input description]`

## Process

### Phase 1: Load Pipeline
1. Parse `$ARGUMENTS` — extract pipeline name (first word) and input (rest)
2. Look for pipeline file in order:
   a. `.claude/pipelines/<name>.yml`
   b. `.claude/pipelines/<name>.yaml`
3. If not found, list available pipelines:
   ```bash
   ls .claude/pipelines/*.yml .claude/pipelines/*.yaml 2>/dev/null
   ```
   Ask user to choose from available pipelines.
4. Read and parse the YAML pipeline definition
5. Check `mode` field — if pipeline requires `project` mode:
   - Read `.ezproject.json` and check `"mode"` field
   - If mode is `mvp` and pipeline requires `project`, warn user and ask to proceed or abort

### Phase 2: Present Plan
1. Display the pipeline steps in order:
   ```
   ## Pipeline: [name]
   [description]

   ### Execution Plan
   | # | Step | Type | Agent | Depends On |
   |---|------|------|-------|------------|
   | 1 | research | agent | researcher | — |
   | 2 | design | agent | architect | research |
   | 3 | plan_approval | gate | — | design |
   ...
   ```
2. Highlight gates (human approval points) with a note
3. Highlight parallel steps (steps whose dependencies are all met at the same time)
4. Ask user for confirmation before executing
5. Store the input text (everything after pipeline name) as `{{input}}` for step substitution

### Phase 3: Execute Steps
Process steps respecting dependency order. Group into waves:
- **Wave N:** All steps whose dependencies are complete and not yet started

For each step in a wave:

**type: agent**
1. Build the prompt by substituting `{{step_id.output}}` placeholders with previous step outputs
2. Also substitute `{{input}}` with the user's input text
3. Spawn the agent using Agent tool:
   - Map agent name to subagent_type using the mapping table below — every agent is a real `.claude/agents/*.md` file, so each name maps to itself (do NOT collapse to `general-purpose`, that bypasses the agent's prompt)
   - Set `isolation: "worktree"` if step has `isolation: worktree`
   - Set `run_in_background: true` if multiple steps in the same wave (parallel execution)
4. Capture the agent's output for artifact passing
5. Mark step as DONE in TodoWrite tracking

**type: command**
1. Build the command arguments by substituting placeholders
2. Execute the slash command via Skill tool
3. Capture output

**type: validation**
1. Run each command in `commands` list sequentially via Bash
2. If ALL pass -> step DONE
3. If any fail -> retry (up to `retry` count):
   a. Identify the failure
   b. Spawn a debugger agent to fix the issue
   c. Re-run validation commands
4. If still failing after all retries -> STOP and ask user

**type: gate**
1. Display the `message` to the user
2. Ask for approval (use AskUserQuestion tool or direct prompt)
3. If rejected -> STOP pipeline gracefully with reason
4. If approved -> continue to next steps

**type: summary**
1. Collect all previous step outputs
2. Generate a structured summary covering all steps
3. Display to user

### Phase 4: Report
After all steps complete:
```
## Pipeline Execution Report: [name]

### Steps
| Step | Status | Agent |
|------|--------|-------|
| research | DONE | researcher |
| design | DONE | architect |
| validation | DONE (retry 1/3) | — |
...

### Summary
[Generated summary from summary step, or auto-generated if no summary step]

### Next Actions
- [Suggested follow-up actions]
```

## Agent Name Mapping

Every agent below is defined in `.claude/agents/<name>.md` (or installed by `/upgrade-to-project` for project-mode agents). Map each name to itself — collapsing to `general-purpose` would discard the agent's specialized prompt.

| Pipeline Agent | Claude Code subagent_type | Notes |
|----------------|--------------------------|-------|
| researcher | researcher | sonnet (breadth) |
| architect | architect | opus |
| tester | tester | opus |
| debugger | debugger | opus |
| code-reviewer | code-reviewer | opus |
| security-auditor | security-auditor | opus |
| refactorer | refactorer | opus |
| performance-profiler | performance-profiler | opus |
| smart-context | smart-context | opus |
| documentation-writer | documentation-writer | sonnet (mechanical) |
| dependency-manager | dependency-manager | sonnet |
| integration-tester | integration-tester | opus (writes E2E test code) |
| orchestrator | orchestrator | opus, project-mode only |
| release-manager | release-manager | sonnet, project-mode only |

## Available Pipelines
```
/pipeline feature [description]   — Full feature delivery (Project mode)
/pipeline bugfix [description]    — Bug diagnosis -> fix -> test -> review
/pipeline security [scope]        — Security audit -> fix -> validate
/pipeline release                 — Pre-release validation -> release (Project mode)
```

## Rules
- ALWAYS show the execution plan and get approval before running
- ALWAYS respect dependency order — never skip ahead
- Steps with no mutual dependencies in the same wave run in parallel (run_in_background: true)
- Track progress visibly using TodoWrite
- If a pipeline requires Project mode, check .ezproject.json first
- Custom pipelines in `.claude/pipelines/` are supported — same YAML format
- If an agent step fails -> retry once, then stop pipeline
- If a validation step fails -> retry up to `retry` count, then stop
- If a gate is rejected -> stop pipeline gracefully
- On any stop: display what completed, what was skipped, and the failure reason
