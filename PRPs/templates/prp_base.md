---
name: "EzProject PRP Template"
description: |
  Template optimized for AI agents to implement features with sufficient
  context and self-validation capabilities for one-pass implementation.

  Principles:
  - Context is King: Include ALL necessary docs, examples, and caveats
  - Validation Loops: Provide executable tests the AI can run and fix
  - Information Dense: Use keywords and patterns from the codebase
  - Progressive Success: Start simple, validate, then enhance
  - Global Rules: Follow all rules in CLAUDE.md
---

# PRP: [Feature Name]

## Overview
[What needs to be built — be specific about the end state]

## Dependencies
<!-- Other PRPs or features that must be completed first -->
- Requires: [PRP/feature name or "none"]
- Blocks: [PRP/feature name or "none"]

## Context & References

### MUST READ — Load these into your context
- file: `examples/[relevant_pattern].py` — why: [pattern to follow]
- file: `CLAUDE.md` — why: project rules and standards
- file: `DECISIONS.md` — why: past architectural decisions
- url: [API docs URL] — why: [specific endpoints/methods needed]
- doc: [Library docs URL] — section: [relevant section]

### Critical Gotchas
<!-- Things that commonly trip up AI coding assistants -->
- CRITICAL: [Specific setup requirement]
- CRITICAL: [Rate limit or API constraint]
- CRITICAL: [Database constraint or schema requirement]

## Architecture

### New Files
| File | Purpose |
|------|---------|
| `src/[module]/[file].py` | [Description] |
| `tests/test_[file].py` | [Tests for what] |

### Modified Files
| File | Changes |
|------|---------|
| `src/[existing].py` | [What changes and why] |

### Database Changes (if applicable)
```sql
-- Migration: YYYY-MM-DD — [description]
CREATE TABLE IF NOT EXISTS [table_name] (
    id INT AUTO_INCREMENT PRIMARY KEY,
    -- columns here
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## Implementation Plan

### Task 1: [Setup / Foundation]
**Goal:** [What this accomplishes]
**Files:** `src/[file].py`
**Pattern:** Follow `examples/[pattern].py`
**Details:**
- Step 1: ...
- Step 2: ...

**Validation:**
```bash
python -c "from src.[module] import [class]; print('OK')"
```

### Task 2: [Core Logic]
**Goal:** [What this accomplishes]
**Files:** `src/[file].py`
**Details:**
- Step 1: ...
- Step 2: ...

**Validation:**
```bash
pytest tests/test_[file].py -v
```

### Task 3: [Integration]
**Goal:** [Connect components together]
**Details:**
- ...

**Validation:**
```bash
python -m src.main  # smoke test
```

## Final Validation Loop

After ALL tasks complete, run in order:
```bash
# 1. Lint
ruff check src/ tests/

# 2. Format check
black --check src/ tests/

# 3. Tests
pytest tests/ -v

# 4. Smoke test
python -m src.main
```

Fix ANY failures. Re-run until ALL pass.

## Success Criteria
- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]
- [ ] All tests pass
- [ ] No lint errors
- [ ] Code follows patterns from examples/
- [ ] ROADMAP.md updated
- [ ] DECISIONS.md updated (if architectural decisions were made)

## PRP Quality Checklist
<!-- Validation automatique avant exécution -->
- [ ] All referenced files (examples/, docs/) exist in the project
- [ ] Each task has a validation command
- [ ] Database changes include migration SQL with date comment
- [ ] Dependencies section filled (or explicitly "none")
- [ ] Confidence score >= 7

## Confidence Score: [X/10]
<!-- Score yourself. If < 7, add more context before executing. -->
