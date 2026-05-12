Perform automatic housekeeping after implementation work.

Run this automatically after completing any feature, fix, or refactoring work. This command ensures documentation stays in sync with code and temporary files are cleaned up.

## Step 1: Update ROADMAP.md

1. Read ROADMAP.md
2. Check git log for recent commits: `git log --oneline -10`
3. For each item in ROADMAP.md:
   - If the work was done (based on commits), mark as `[x]` with today's date
   - If work is in progress, mark as `[-]` with today's date
4. Write the updated ROADMAP.md

## Step 2: Update CLAUDE.md if Needed

1. Read CLAUDE.md
2. Check if any of these changed:
   - Directory structure (new folders/files created)
   - Entry points or commands
   - Dependencies added
   - Architecture changes (new modules, changed patterns)
3. If changes detected, update the relevant sections in CLAUDE.md
4. Do NOT rewrite the whole file — only update what changed

## Step 3: Update AGENTS.md if Needed

1. If `AGENTS.md` exists, check whether the Codex/OpenAI runtime docs drifted from the current codebase
2. Mirror structural, dependency, command, and gotcha changes made in CLAUDE.md
3. Do NOT merge the two runtimes together — keep them parallel but aligned

## Step 4: Update README.md if it Exists

1. If README.md exists, check if setup/usage instructions are still accurate
2. Update only if something concrete changed (new dependency, new command, new env var)

## Step 5: Clean Up Temporary Files

Look for and delete:
- `CLAUDE.md.proposed` (audit output, no longer needed after applied)
- `AGENTS.md.proposed` (audit output, no longer needed after applied)
- `*.pyc` files and `__pycache__/` directories
- Any file matching patterns: `*_old.py`, `*_backup.py`, `*_temp.py`, `*_test_scratch.py`
- Empty files (0 bytes)
- `.DS_Store`, `Thumbs.db`

Before deleting, list what will be removed and ask:
"Ces fichiers temporaires vont etre supprimes. OK?"

## Step 6: Verify Git State

```bash
git status
```

If there are uncommitted changes from the doc updates:
```bash
git add ROADMAP.md CLAUDE.md README.md
# If present: git add AGENTS.md
git commit -m "docs: update documentation to match current state"
```

## Step 7: Self-Healing Reminder (output only, do NOT execute)

If this housekeeping was run after `/execute-prp` or any non-trivial implementation, append this reminder to the output:

```
💡 Self-healing pending — recommend running in a SEPARATE conversation:
   /retrospective last

This catches AI-layer drift (CLAUDE.md gotchas missing, examples to extract,
skill steps too vague) that the implementer can't see from inside its own
context window. Skip if the implementation was trivial.
```

Do NOT run `/retrospective` from this command. The whole point is fresh context.

## Output

```
Housekeeping complete:
- ROADMAP.md: X items updated
- CLAUDE.md: [updated/no changes needed]
- AGENTS.md: [updated/no changes needed/not found]
- README.md: [updated/no changes needed/not found]
- Temp files removed: X
- Git: [committed/clean]

💡 [Self-healing reminder if applicable — see Step 7]
```

## IMPORTANT
- Never delete source code files (.py, .js, etc.) -- only obvious temp/backup files
- Always ask before deleting if unsure
- Keep changes minimal and focused -- don't rewrite docs unnecessarily
- NEVER run /retrospective from inside /housekeeping — it must be a fresh context
