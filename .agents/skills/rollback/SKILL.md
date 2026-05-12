---
name: rollback
description: Safely roll back recent changes — uncommitted edits, last commit, range of commits, or back to a specific commit. Always uses `git revert` (preserves history) and `git stash` (preserves work). Never `git reset --hard`.
---

# Rollback

## Phase 1: Assess
```
git status
git log --oneline -10
git diff --stat
```
Show: branch, last 10 commits, uncommitted state, files modified.

## Phase 2: Identify the target
Ask the user:
"Qu'est-ce que tu veux rollback?
1. Les changements non-commités (stash)
2. Le dernier commit (revert)
3. Les X derniers commits (revert range)
4. Revenir à un commit spécifique (revert chain)"

## Phase 3: Execute the chosen option (always confirm first)

### Option 1 — Uncommitted changes
Show `git diff` and `git diff --cached`. Confirm with the user, then:
```
git stash save "rollback-backup-<timestamp>"
```
Tell the user: "Recoverable via `git stash pop`."

### Option 2 — Last commit
Show `git log -1 --stat`. Confirm. Then:
```
git revert HEAD --no-edit
```

### Option 3 — Last X commits
Show `git log --oneline -X`. Confirm. Then:
```
git revert HEAD~X..HEAD --no-edit
```

### Option 4 — Specific commit
Show `git log --oneline -20`. Ask for the hash. Then revert all commits after that one.

## Phase 4: Verify
```
git log --oneline -5
git status
pytest tests/ -v --tb=short
```
Report: what was rolled back, current state, whether tests pass.

## Rules
- NEVER use `git reset --hard` — always `git revert`
- NEVER use `git checkout .` — always `git stash`
- Always show the user what will be affected before acting
- Always require confirmation before any destructive action
- If tests fail after rollback, warn the user immediately
