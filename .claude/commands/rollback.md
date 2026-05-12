Safely rollback recent changes when something went wrong.

## Instructions

### Phase 1: Assess the Situation

```bash
git status
git log --oneline -10
git diff --stat
```

Present the current state:
- What branch are we on?
- What are the last 10 commits?
- Are there uncommitted changes?
- What files were modified?

### Phase 2: Identify the Target

Ask the user:
"Qu'est-ce que tu veux rollback?
1. Les changements non-commités (git checkout / restore)
2. Le dernier commit (git revert)
3. Les X derniers commits (git revert range)
4. Revenir à un commit spécifique (git revert to)"

### Phase 3: Safe Rollback

Based on user choice:

#### Option 1: Uncommitted changes
```bash
# Show what will be lost
git diff
git diff --cached
```
Ask: "Ces changements vont être perdus. Confirme?"

If confirmed:
```bash
git stash save "rollback-backup-$(date +%Y%m%d-%H%M%S)"
```
Tell user: "Les changements sont sauvegardés dans git stash. Tu peux les récupérer avec `git stash pop` si besoin."

#### Option 2: Last commit
```bash
git log -1 --stat
```
Ask: "Ce commit va être annulé (un nouveau commit de revert sera créé). Confirme?"

If confirmed:
```bash
git revert HEAD --no-edit
```

#### Option 3: Last X commits
```bash
git log --oneline -X
```
Ask: "Ces X commits vont être annulés un par un (des commits de revert seront créés). Confirme?"

If confirmed:
```bash
git revert HEAD~X..HEAD --no-edit
```

#### Option 4: Specific commit
```bash
git log --oneline -20
```
Ask: "Quel commit? (copie le hash)"

Then revert all commits after that one.

### Phase 4: Verify

```bash
git log --oneline -5
git status
pytest tests/ -v --tb=short 2>&1 | tail -10
```

Report the result:
- What was rolled back
- Current state of the code
- Whether tests pass

## IMPORTANT RULES
- NEVER use `git reset --hard` — always use `git revert` (creates history)
- NEVER use `git checkout .` — always use `git stash` (preserves changes)
- ALWAYS show the user what will be affected before acting
- ALWAYS ask for confirmation before any destructive action
- ALWAYS suggest `git stash` instead of discarding uncommitted work
- If tests fail after rollback, warn the user immediately
