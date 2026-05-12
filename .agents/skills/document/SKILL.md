---
name: document
description: Auto-generate or update project documentation from code — API reference, data dictionary, architecture overview, module docs. Mechanical extraction; never overwrites manual content marked with `<!-- manual -->`.
---

# Document

## Phase 1: Discover
1. Read CLAUDE.md for stack type
2. Scan `src/` for modules, classes, functions
3. Read `docs/schema.sql` if it exists (data dictionary source)
4. Read existing `docs/` files — preserve sections marked `<!-- manual -->`
5. Read `DECISIONS.md` for ADRs (architecture overview source)
6. Read `examples/` for pattern descriptions

## Phase 2: Extract
- Code: docstrings (Google-style), type hints, function signatures
- Schema: CREATE TABLE statements, columns, indexes, comments
- ADRs: title + decision + status from `DECISIONS.md`
- ROADMAP: current phase + completed features

## Phase 3: Generate
Default scope: all (`$ARGUMENTS` can narrow to `api`, `data`, `architecture`, or `modules`).

- **API reference** (api / ai-agent stacks): list endpoints with method, path, parameters, response model. Output: `docs/api-reference.md`
- **Data dictionary** (MySQL in stack): tables, columns, types, constraints, FKs, indexes. Output: `docs/data-dictionary.md`
- **Architecture overview**: module dependency graph, key patterns, active ADRs. Output: `docs/architecture.md`
- **Module docs**: per module — purpose, public API, usage examples. Output: `docs/modules.md`

## Phase 4: Quality check
- Verify all referenced files / classes / functions exist
- Flag stale references (deleted code)
- Flag undocumented public functions (missing docstrings)

## Phase 5: Report + commit
Show the user a coverage summary (documented vs undocumented public APIs). Ask before writing. Commit separately: `docs: auto-generate documentation`.

## Rules
- NEVER overwrite sections marked `<!-- manual -->`
- ALWAYS verify generated references point to real code
- If a public function has no docstring, generate one and add it to the source
- Show diffs before writing
- Use Google-style docstrings to match the project convention
- Keep generated docs concise (tables over paragraphs)
- Include the generation date for staleness tracking
