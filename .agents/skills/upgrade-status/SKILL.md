---
name: upgrade-status
description: Compare the current project's template adoption to the latest template state and report what's available but not yet pulled in. Use to decide whether to run `ez-upgrade-project.ps1 -Force`.
---

# Upgrade Status

Read-only report of the gap between this project's template version and the latest available state of the EzProject template repo.

## Phase 1: Locate the template repo
Try in order:
1. `$EZ_TEMPLATE_PATH` env var
2. `c:/Users/racer/OneDrive/ez-project-template/` (Windows default)
3. `~/ez-project-template/` or `~/dev/ez-project-template/` (Unix defaults)
4. Ask the user for the path if none of the above resolve

Verify by checking that the resolved path contains `template/.ezproject.json`, `DECISIONS.md`, and `template/.claude/commands/`.

## Phase 2: Read project state
Read `.ezproject.json` in the current directory and extract `template_version`, `created`, `mode`, `stack`, `runtimes`. If missing, this is not a generated EzProject — explain and exit.

## Phase 3: Read template state
- `<template>/template/.ezproject.json` for current template_version
- `<template>/DECISIONS.md` for ADRs with `**Date:** YYYY-MM-DD` and `**Status:** accepted`
- Listings of `<template>/template/.claude/commands/`, `<template>/template/.claude/agents/`, and (if Codex is enabled) `<template>/template/.agents/skills/`

## Phase 4: Compute drift
1. ADRs accepted strictly after the project's `created` date
2. Commands present in template but missing in project
3. Agents present in template but missing in project
4. Codex skills present in template but missing in project (only if `runtimes` includes Codex)

## Phase 5: Output
Print a compact report:
- Project version + created date + mode/stack/runtimes
- Template version and its on-disk path
- ADRs added since project creation (count + list)
- New commands / agents / skills available (counts + lists)
- Recommendation: exact `ez-upgrade-project.ps1 -Force` command with full template path, or "in sync, nothing to do"

## Rules
- Never modify the project. Read-only.
- Always print the exact command to run, with the full path resolved.
- Keep output under 40 lines.
- If the template path cannot be located, ask once and suggest setting `EZ_TEMPLATE_PATH`.
