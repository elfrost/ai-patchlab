# /document — Auto-Generate Documentation

Generate or update project documentation from the current codebase.

## Argument
`$ARGUMENTS` — Optional scope: `api`, `data`, `architecture`, `modules`, or `all` (default: `all`).

## Process

1. **Spawn documentation-writer agent** with scope `$ARGUMENTS`
2. Agent analyzes code, schema, decisions, and existing docs
3. **Generate/update** documentation files in `docs/`:
   - `docs/api-reference.md` — API endpoints (if stack = api/ai-agent)
   - `docs/data-dictionary.md` — Database tables and columns (if MySQL)
   - `docs/architecture.md` — Module structure, patterns, ADRs summary
   - `docs/modules.md` — Per-module documentation
4. **Show coverage report** — documented vs undocumented public APIs
5. **Flag stale docs** — references to code that no longer exists

## Usage
- `/document` — Generate all documentation
- `/document api` — Only API reference
- `/document data` — Only data dictionary
- `/document architecture` — Only architecture overview

## Instructions

1. Read CLAUDE.md for project context and stack type
2. Determine the scope:
   - If `$ARGUMENTS` is provided, generate only that type
   - If empty or `all`, generate everything applicable to the stack
3. Use the documentation-writer agent (Agent tool) to perform the analysis and generation
4. Before writing any files, show the user:
   - What files will be created/updated
   - A preview of the generated content
5. After user approval, write the documentation files
6. Show the coverage report (documented vs undocumented public APIs)
7. If undocumented functions are found, offer to add docstrings to the source code
8. Commit documentation separately: `docs: auto-generate documentation`

## Rules
- NEVER overwrite manually-written documentation sections (check for `<!-- manual -->` markers)
- ALWAYS verify generated references point to existing code
- If a function has no docstring, generate one and add it to the source code
- Show diff of all changes before writing
- Commit documentation separately: `docs: auto-generate documentation`
