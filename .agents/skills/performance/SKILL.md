---
name: performance
description: Identify performance bottlenecks via static pattern hunting plus optional runtime profiling. Combines Claude's two-stage Karpathy pipeline (researcher + performance-profiler per ADR-016) into one inline pass.
---

# Performance

Inline two-stage analysis: gather candidate hot paths first (mechanical grep), then prioritize and deepen on the top targets.

## Phase 1: Gather candidates
Default scope: `src/` (or `$ARGUMENTS` if provided). Look for likely-slow patterns:
- Sync I/O inside `async def` (`requests.get`, `time.sleep`, `open()` without aiofiles)
- N+1 query patterns (DB call inside a loop)
- Sequential `await` calls that could be `asyncio.gather`
- Compiled regexes or client instantiations inside loops
- Unbounded list / str growth in loops
- Missing connection pooling (new aiomysql connection per request)
- Blocking calls in async handlers

For each candidate: file:line + function name + sample.

## Phase 2: Prioritize + deep analysis
1. Rank candidates by likely impact
2. For top candidates, examine call frequency and data volumes
3. If user opts in to runtime profiling: `python -m cProfile -o /tmp/profile.out src/main.py` then parse with `pstats`
4. Correlate static findings with runtime hotspots

## Phase 3: Report + act
Produce ranked recommendations with concrete fix proposals (not "use async" — show the exact replacement).

For quick wins (1-line fixes like `time.sleep` -> `asyncio.sleep`):
- Ask the user before applying
- Apply + run validation (`ruff check`, `pytest`)

For structural changes (N+1 fixes, async refactors, pooling):
- Suggest creating a PRP via the `generate-prp` skill

## Rules
- Static analysis is safe and always runs
- Runtime profiling requires explicit user approval (modifies execution)
- Quick wins can be auto-applied with validation
- Structural changes belong in a PRP
- Don't optimize prematurely — focus on measurable bottlenecks
