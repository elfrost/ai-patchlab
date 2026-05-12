Quick project status snapshot — run this at the start of a session to understand the current state.

## Instructions

Gather all this info IN PARALLEL, then present a concise summary.

### 1. Project State
- Read ROADMAP.md — count: items done, in progress, todo
- Read DECISIONS.md — check for recent decisions
- Check if INITIAL.md has been filled in (not just the template)

### 2. Git State
```bash
git status --short
git log --oneline -5
git branch -a
```

### 3. Code Health
```bash
ruff check src/ 2>&1 | tail -3
black --check src/ 2>&1 | tail -3
pytest tests/ -v --tb=no 2>&1 | tail -5
```

### 4. Quick Metrics
```bash
find src/ -name "*.py" -not -name "__init__.py" | wc -l
find tests/ -name "*.py" -not -name "__init__.py" | wc -l
find src/ -name "*.py" -exec wc -l {} + 2>/dev/null | tail -1
```

## Output Format

Present as a compact dashboard:

```
📊 PROJECT STATUS — [project name]
══════════════════════════════════

📋 Roadmap:  X done | Y in progress | Z todo
🌿 Branch:   [current branch] (X commits ahead of main)
📝 Last:     [last commit message] ([date])

🏗️ In Progress:
  - [item 1]
  - [item 2]

📁 Codebase: X source files | Y test files | Z total lines
🧪 Tests:    X passed | Y failed | Z skipped
🔍 Lint:     [clean / X issues]
🎨 Format:   [clean / X files need formatting]

⚠️ Attention:
  - [any warnings: uncommitted changes, failing tests, lint issues]

💡 Suggested next:
  - [what to work on next based on roadmap]
```

## Rules
- Be CONCISE — this is a snapshot, not a report
- If tests/lint fail, show the key errors (not full output)
- If there are uncommitted changes, flag them prominently
- Suggest what to work on next based on ROADMAP.md priorities
