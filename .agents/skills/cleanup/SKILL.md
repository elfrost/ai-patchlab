---
name: cleanup
description: Identify dead code, unused files, and clutter via import-graph tracing from entry points. Writes a report and asks before deleting anything.
---

# Cleanup

## Phase 1: Find entry points
1. Read CLAUDE.md to understand the project
2. Identify all entry points:
   - `if __name__ == "__main__"` in `.py` files
   - Scripts referenced in CLAUDE.md / README
   - Anything in Makefile, docker-compose, scripts/

## Phase 2: Build the dependency graph
For each entry point, trace imports recursively. Mark every reachable file ALIVE. Mark unreachable ones DEAD.

## Phase 3: Classify dead files
For each DEAD file, categorize:
- **Orphan script** — has `__main__`, never called by main flow (could be a utility)
- **Abandoned module** — imported before, no longer is
- **Duplicate / superseded** — does the same as an alive file
- **Config / data file** — used at runtime but not imported (templates, configs)
- **Test file** — may still be relevant even outside main path

## Phase 4: Other clutter
- Empty `__init__.py` that serves nothing
- `.pyc` / `__pycache__` directories
- Old output / log / temp files
- Backup files (`*_v2.py`, `*_old.py`, `*_backup.py`)
- Stale TODO / notes files

## Phase 5: Report
Write `CLEANUP_REPORT.md` with:
- Summary counts (alive / dead / clutter)
- Entry points list
- Alive files table (file -> imported by)
- Dead files table (file -> type -> reason -> recommendation: DELETE / ARCHIVE / ASK USER)
- Clutter items
- Recommended actions (Safe / Moderate / Aggressive levels)

## Phase 6: Confirm + act
Ask the user:
"Quel niveau de cleanup tu veux?
1. Safe only — clutter évident
2. Moderate — clutter + dead code évident
3. Aggressive — tout le dead code, projet lean
4. Laisse-moi reviser le rapport d'abord"

Apply only what is approved. Move ambiguous items to `archive/` instead of deleting.

## Rules
- NEVER delete without confirmation
- Write the report BEFORE deleting anything
- If unsure, mark ASK USER
- Config / .env / data files are NOT dead even if not imported
- Suggest a `git commit` before deletion to keep recovery easy
