Analyze the entire project to identify dead code, unused files, and unnecessary clutter.

## Process

### Phase 1: Find the Entry Points

1. Read CLAUDE.md to understand what the project does
2. Identify ALL entry points (main scripts, run.py, etc.):
   - Check for `if __name__ == "__main__"` in all .py files
   - Check for scripts referenced in CLAUDE.md or README
   - Check package.json scripts (if Node)
   - Check any Makefile, docker-compose, or config that runs code

### Phase 2: Build the Dependency Graph

Starting from each entry point, trace ALL imports recursively:

```bash
# Find all Python imports in the project
grep -rn "^import \|^from " src/ *.py --include="*.py"
```

For each file that IS imported by an entry point (directly or transitively):
- Mark as ALIVE

For each file that is NOT imported by anything:
- Mark as DEAD (candidate for removal)

### Phase 3: Analyze Each Dead File

For each DEAD file, determine:
- **Orphan script**: Has `if __name__ == "__main__"` but is never called by the main workflow. Could be a standalone utility or an abandoned experiment.
- **Abandoned module**: Was imported before but no longer is. Old code path.
- **Duplicate/superseded**: Does the same thing as another file that IS alive.
- **Config/data file**: Not imported but used by the system (templates, configs, data files).
- **Test file**: Test that may still be relevant even if not in the main path.

### Phase 4: Check for Other Clutter

- Empty `__init__.py` files that serve no purpose
- `.pyc` / `__pycache__` directories
- Old output files, logs, temp files
- Duplicate or backup files (file_v2.py, file_old.py, file_backup.py)
- Old TODO/notes files that are outdated
- Unused config files or .env variants

### Phase 5: Generate Report

Write the report to `CLEANUP_REPORT.md`:

```markdown
# Cleanup Report - [Project Name]
Generated: [date]

## Summary
- Total files: X
- Alive (used): X (Y%)
- Dead (unused): X (Y%)
- Clutter: X

## Entry Points
- `run.py` -- Main workflow
- [other entry points]

## ALIVE Files (keep these)
| File | Imported By | Purpose |
|------|-------------|---------|
| ... | ... | ... |

## DEAD Files (candidates for removal)
| File | Type | Reason | Recommendation |
|------|------|--------|----------------|
| old_scraper.py | Abandoned | Was replaced by new_scraper.py | DELETE |
| utils_v2.py | Duplicate | Same as utils.py | DELETE |
| test_experiment.py | Orphan script | Standalone test, still useful? | ASK USER |

## Clutter
| Item | Type | Recommendation |
|------|------|----------------|
| __pycache__/ | Build artifact | DELETE |
| output_old.csv | Old output | DELETE |

## Recommended Actions
1. [Safe to delete immediately - list]
2. [Ask user first - list]
3. [Keep but move to archive/ - list]
```

### Phase 6: Ask for Confirmation

Present the report and ask:
"Voici l'analyse. Quel niveau de cleanup tu veux?
1. Safe only -- supprimer juste le clutter evident (__pycache__, backups, fichiers vides)
2. Moderate -- supprimer le clutter + les fichiers morts evidents
3. Aggressive -- tout le dead code, je veux un projet lean
4. Laisse-moi reviser le rapport d'abord"

## IMPORTANT RULES
- NEVER delete without confirmation
- Write report BEFORE deleting anything
- If unsure whether something is dead, mark as ASK USER
- Config files, .env, data files are NOT dead code even if not imported
- Git-tracked files should be committed before deletion (suggest git commit first)
- Move to archive/ instead of deleting when the code might be useful later
