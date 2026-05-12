---
name: next
description: Recommend the best next action based on current project state. Use when starting a fresh session, finishing a PRP, after a long pause, or whenever the user is unsure which command to run next.
---

# Next-step advisor

Read the project state and produce a short ranked recommendation of 1-3 actions. This skill never executes the recommended commands â€” it only suggests.

## Phase 1: Detect state
Read in this order, skipping silently any source that does not exist:

1. `.ezproject.json` for mode and stack
2. `INITIAL.md` â€” exists? when was it last modified? does it still contain placeholders?
3. `PRPs/*.md` â€” active (un-archived) PRPs
4. `PRPs/done/*.md` â€” recently completed (last 30 days)
5. `git status --short` â€” uncommitted files
6. `git rev-parse --abbrev-ref HEAD` â€” current branch
7. `git log --since="2.weeks.ago" --oneline` â€” recent activity
8. `git log -1 --format="%ar â€” %s"` â€” last commit summary
9. CLAUDE.md last modification date â€” drift signal
10. `grep -l "ai-patchlab\|2026-05-12\|\[REMPLIR\]" *.md` â€” unfinished kickoff?

## Phase 2: Decision tree (top-down, first match wins)

1. Placeholders remain in INITIAL/CLAUDE/ROADMAP/README â†’ run `kickoff` to finish project setup
2. No INITIAL.md, fresh repo, on main â†’ run `kickoff` to start a new feature interview
3. INITIAL.md exists, no PRP for it â†’ run `generate-prp INITIAL.md`
4. Active PRP, never executed â†’ run `execute-prp PRPs/<name>.md` in a NEW conversation (fresh context per ADR-013)
5. Active PRP with partial progress â†’ resume `execute-prp PRPs/<name>.md`
6. PRP moved to `PRPs/done/` within last 24h, no retrospective committed since â†’ run `retrospective last` in a NEW conversation
7. Uncommitted changes on a feature branch â†’ run `review-code` before committing
8. Feature branch ahead of main, tests passing, no active PRP â†’ open a PR or run the release pipeline if available
9. 3+ weeks since CLAUDE.md modified AND 10+ commits since â†’ run `audit-project`
10. 30+ days since pyproject.toml change, never ran a dependency check â†’ run a dependency audit
11. Many TODO/FIXME comments accumulating â†’ run a cleanup pass
12. On main, nothing in progress â†’ list top 3 unchecked ROADMAP items and ask the user to pick, then run `kickoff`

## Phase 3: Output

Produce a short report with two sections:

```
## Where you are
- Mode/Stack: ...
- Branch: ...
- Active PRP: ...
- Uncommitted: ...
- Last commit: ...
- Recent activity: ...

## Recommended next steps
1. [PRIMARY] <command with exact args> â€” <one-sentence reason tied to detected state>
2. [SECONDARY] <command> â€” <reason>
3. [LATER] <command> â€” <reason>
```

## Rules
- Always print the literal command to run, with exact arguments.
- Tag each recommendation [PRIMARY] / [SECONDARY] / [LATER].
- Always remind that `execute-prp` and `retrospective` should run in fresh sessions (ADR-013).
- If state is genuinely ambiguous (e.g., 5 PRPs active), ASK the user to pick rather than guess.
- Never fabricate state â€” if a marker is missing or unreadable, say so and skip that branch.
- Keep output under 30 lines.
- This skill MUST NOT execute the recommended commands. It only suggests.
