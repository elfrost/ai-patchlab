# /performance — Performance Analysis

Profile code and identify optimization opportunities using a two-stage Karpathy-style pipeline (per ADR-016): the sonnet `researcher` finds candidate hot paths via static pattern-hunting, then the opus `performance-profiler` does deep analysis (and optional runtime profiling) on the top candidates.

## Argument
`$ARGUMENTS` — Optional target path (file or directory). Default: `src/`.

## Process

### Phase 1: Delegate static scan to `researcher` (sonnet)

Do NOT scan the codebase yourself. Spawn the `researcher` subagent (sonnet) — pattern-hunting is mechanical breadth, not deep reasoning.

Use the Task tool with `subagent_type: "researcher"`. Pass it:
- Scope: `$ARGUMENTS` if provided, else `src/`
- An explicit list of likely-slow patterns to grep / extract (file:line + function name + sample, NO prioritization yet):
  - Sync I/O inside `async def` (e.g., `requests.get`, `time.sleep`, `open()` without aiofiles)
  - N+1 query patterns (DB call inside a loop)
  - Sequential `await` calls that could be `asyncio.gather`
  - Compiled regexes or client instantiations inside loops
  - Large in-memory data structures (lists growing unboundedly, str concatenation in loops)
  - Missing connection pooling (new aiomysql connection per request)
  - Blocking calls in async handlers
- Confidence score

The researcher returns a structured candidate list. It MUST NOT prioritize, profile, or propose fixes — that's the performance-profiler's job in Phase 2.

**Hard gate:** if confidence < 5 (scope unclear, code unreadable), ask the user for clarification.

### Phase 2: Delegate deep analysis to `performance-profiler` (opus)

Spawn `performance-profiler` with the researcher's brief.

Use the Task tool with `subagent_type: "performance-profiler"`. Pass it:
- The researcher's full candidate list with samples
- Whether the user opted in to runtime profiling (default: no, ask first)
- A directive: prioritize by likely impact, deepen analysis on top candidates, run cProfile on entry point if runtime profiling enabled, correlate static findings with hotspots, propose concrete fixes ranked by ROI

The performance-profiler returns the final ranked recommendations.

### Phase 3: Present + act

1. Show the performance-profiler's report
2. For quick wins (1-line fixes like `time.sleep` → `asyncio.sleep`):
   - Ask user before applying
   - Apply + run validation (`ruff check`, `pytest`)
3. For structural changes (N+1 queries, missing pooling, async refactor):
   - Suggest creating a PRP via `/generate-prp`
   - Or add to project TODO

## Usage
- `/performance` — Analyze all of `src/`
- `/performance src/services/scraper.py` — Analyze a specific file
- `/performance --profile` — Include runtime profiling (requires running the app)

## Rules
- ALWAYS delegate Phase 1 to `researcher` — do NOT scan inline
- ALWAYS delegate Phase 2 to `performance-profiler` — do NOT prioritize in main context
- Static analysis is safe and always runs
- Runtime profiling requires explicit user approval (modifies execution)
- Quick wins can be auto-applied with validation
- Structural changes should be planned (suggest `/generate-prp`)
- Don't optimize prematurely — focus on measurable bottlenecks
