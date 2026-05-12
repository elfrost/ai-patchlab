# /upgrade-status — Template Drift Detection

Compare the current project's template adoption to the latest template state. Surfaces features available in the template that haven't been pulled into this project yet — so you know when it's worth running `ez-upgrade-project.ps1 -Force`.

This command never modifies the project. It only reports.

## Argument
None.

## Process

### Phase 1: Locate the template repo

The command runs from a generated project, but needs to find the EzProject template repo elsewhere on the machine. Try these in order:

1. `$EZ_TEMPLATE_PATH` environment variable (if set, point to the template repo root)
2. Common Windows location: `c:/Users/racer/OneDrive/ez-project-template/`
3. Common Unix location: `~/ez-project-template/` or `~/dev/ez-project-template/`
4. If none of the above exist or contain a `template/.ezproject.json`, ask the user for the path

Verify the resolved path is a real EzProject template by checking for `template/.ezproject.json` AND `DECISIONS.md` AND `template/.claude/commands/`.

### Phase 2: Read project state

1. Read `.ezproject.json` in the current directory:
   - Extract `template_version`, `created`, `mode`, `stack`, `runtimes`
   - If the file doesn't exist: this isn't a generated EzProject — print a friendly explanation and exit (suggest running `ez-upgrade-project.ps1` to adopt)

### Phase 3: Read template state

1. Read `<template>/template/.ezproject.json` — current template_version
2. Read `<template>/DECISIONS.md` — list ADRs with their accepted dates
3. List the contents of:
   - `<template>/template/.claude/commands/`
   - `<template>/template/.claude/agents/`
   - `<template>/template/.agents/skills/`

### Phase 4: Compute drift

1. **ADRs added since project creation**: parse `<template>/DECISIONS.md` for `**Date:** YYYY-MM-DD` entries with `**Status:** accepted` whose date is strictly after `.ezproject.json#created`. List ADR number + title.

2. **New commands available**: files in `<template>/template/.claude/commands/*.md` that have NO counterpart at `./.claude/commands/*.md`.

3. **New agents available**: same logic for `.claude/agents/*.md`.

4. **New Codex skills available** (only if the project has Codex enabled per `.ezproject.json#runtimes`): same logic for `.agents/skills/*/SKILL.md`.

5. **Modified core files** (optional, low-priority): if `.claude/commands/<name>.md` exists in both but has substantially different content, list it as "may have updates".

### Phase 5: Output

Render a tight report:

```
## Upgrade Status

**Your project:** v[X], created [YYYY-MM-DD], mode=[mvp|project], stack=[X], runtimes=[claude|claude+codex]
**Template:** v[Y] (latest at [path])

### ADRs added since your project was created ([N])
- ADR-013 (2026-04-25) — Self-healing layer integration
- ADR-014 (2026-05-01) — AI-layer enrichment from antigravity-awesome-skills
- ADR-015 (2026-05-05) — Multi-model orchestration + Karpathy research pipeline

### New commands available ([N])
- /next, /tdd, /upgrade-status

### New agents available ([N])
- (none, or list)

### New Codex skills available ([N], if Codex enabled)
- next, tdd

### Files that may have updates ([N])
- .claude/commands/generate-prp.md (Phase 1 researcher delegation per ADR-015)
- .claude/agents/researcher.md (model: opus → sonnet)

### Recommendation
You are [N] features behind. To pull these in, run from this directory:
  <full path to template>\ez-upgrade-project.ps1 -Force

If you're up to date (zero drift):
  > Project is in sync with the template. Nothing to upgrade.
```

## Rules
- NEVER modify the project — `/upgrade-status` is read-only.
- ALWAYS show the exact `ez-upgrade-project.ps1 -Force` command with the full template path so the user can copy-paste.
- If the template repo cannot be located, ask the user for the path and store it in `$EZ_TEMPLATE_PATH` for next time.
- If `.ezproject.json` is missing in the current directory, suggest running `ez-upgrade-project.ps1` to adopt rather than failing silently.
- Keep output under 40 lines — terse, scannable, one-shot decision support.
- The "Files that may have updates" section is best-effort; if computing diffs is expensive, omit it and say so.
