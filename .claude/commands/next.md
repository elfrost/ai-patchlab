# /next â€” Context-Aware Next-Step Advisor

Read the current project state and recommend the 1-3 best next actions, ranked by priority. Use this any time you don't know what to do next â€” opening a fresh session, finishing a PRP, after a long pause, or when the command list feels overwhelming.

This command never takes action by itself â€” it only recommends.

## Argument
None. (Future: an optional `--verbose` flag could show the full reasoning.)

## Process

### Phase 1: Detect Project State

Run these checks (in parallel where possible) and capture the results. Skip silently any check whose underlying file/marker is missing.

```bash
# Mode and stack
cat .ezproject.json 2>/dev/null

# Active feature spec
test -f INITIAL.md && stat -c '%Y' INITIAL.md 2>/dev/null

# PRPs
ls PRPs/*.md 2>/dev/null
ls -t PRPs/done/*.md 2>/dev/null | head -3

# Git state
git status --short
git rev-parse --abbrev-ref HEAD
git log --since="2.weeks.ago" --oneline | wc -l
git log -1 --format="%ar â€” %s"

# Drift detection
stat -c '%Y' CLAUDE.md 2>/dev/null

# Unfinished kickoff (any placeholder remaining?)
grep -l "ai-patchlab\|2026-05-12\|\[REMPLIR\]" *.md 2>/dev/null
```

### Phase 2: Apply Decision Tree (top-down, first match wins)

Match the detected state against these scenarios in order. The first match drives the [PRIMARY] recommendation. Subsequent matches become [SECONDARY] or [LATER] if relevant.

| # | Scenario | Recommendation |
|---|----------|----------------|
| 1 | Placeholders remain in INITIAL/CLAUDE/ROADMAP/README (`ai-patchlab`, `[REMPLIR]`) | `/kickoff` to finish project setup |
| 2 | No INITIAL.md, no PRPs, on main, fresh repo | `/kickoff` to start a new feature interview |
| 3 | INITIAL.md exists but no PRP yet | `/generate-prp INITIAL.md` |
| 4 | Active PRP in `PRPs/`, never executed | `/execute-prp PRPs/<name>.md` (in a NEW conversation â€” fresh context per ADR-013) |
| 5 | Active PRP, partial progress visible in commits | `/execute-prp PRPs/<name>.md` to resume |
| 6 | A PRP moved to `PRPs/done/` within last 24h, no retrospective committed since | `/retrospective last` (in a NEW conversation â€” fresh context per ADR-013) |
| 7 | Uncommitted changes on a feature branch | `/review-code` before committing |
| 8 | Feature branch with passing tests, ahead of main, no active PRP | Open a PR, or `/pipeline release` (project mode only) |
| 9 | 3+ weeks since CLAUDE.md last modified AND 10+ commits since | `/audit-project` â€” drift likely |
| 10 | 30+ days since `pyproject.toml` change, never ran dependency-check | `/dependency-check` |
| 11 | Many TODO/FIXME comments accumulating in `src/` | `/cleanup` |
| 12 | On main, no active work, no recent PRPs | List top 3 unchecked ROADMAP items, ask user to pick one, then `/kickoff` |

### Phase 3: Output

Render a compact report:

```
## Where you are
- **Mode/Stack:** [project|mvp] / [data|api|ai-agent|web]
- **Branch:** [name] ([N] commits ahead of main)
- **Active PRP:** [name].md (or "none")
- **Uncommitted:** [N] files (or "clean")
- **Last commit:** [time ago] â€” "[message]"
- **Recent activity:** [N] commits in last 2 weeks

## Recommended next steps

1. **[PRIMARY] /command args** â€” [one-sentence reason tied to detected state]
2. **[SECONDARY] /command args** â€” [reason]
3. **[LATER] /command args** â€” [reason]

> Tip: type `/do "<describe what you want>"` for natural-language routing,
> or `/status` for a deeper snapshot.
```

## Rules
- ALWAYS print the literal command to run, with exact arguments.
- Tag recommendations [PRIMARY] / [SECONDARY] / [LATER] for clear prioritization.
- Always remind that `/execute-prp` and `/retrospective` should run in fresh conversations (ADR-013).
- If multiple PRPs are active, pick the one with most recent activity in commit history.
- If state is genuinely ambiguous (e.g., 5 PRPs active, no clear winner), ASK the user to pick rather than guess.
- Never fabricate state â€” if a marker is missing or unreadable, say so and skip that branch of the tree.
- Keep output under 30 lines â€” terse, scannable, actionable.
- This command MUST NOT execute the recommended commands. It only suggests.
