---
layout: default
title: "agentscope-ai/ReMe: security scan"
description: "Security scan of agentscope-ai/ReMe: 159 findings, 3 concrete items filed (wildcard CORS + credentials on both HTTP-service entrypoints, chromadb CVE"
date: 2026-06-04
---

# agentscope-ai/ReMe — security scan

**Repository:** [agentscope-ai/ReMe](https://github.com/agentscope-ai/ReMe) — 3.0k★, Apache-2.0, an agent memory-management kit (*"Remember Me, Refine Me"*) maintained by the AgentScope team with vector-store backends (pgvector, Alibaba Hologres), a SQLite file store, an HTTP service mode, and a flow-DSL execution layer.
**Commit scanned:** `a2d76cc03420` (HEAD of `main` at scan time)
**Scan date:** 2026-06-04
**Disclosure status:** ✅ **Resolved.** Public courtesy issue ([#275](https://github.com/agentscope-ai/ReMe/issues/275)) filed with three concrete real items (wildcard CORS + credentials on both HTTP-service entrypoints, a `chromadb` CVE, and a default-credential anti-pattern in the Neo4j adapter). Maintainer @jinliyl responded item-by-item and closed the issue **~13 hours later** with all three items fixed in `reme4/` (the v4 surface — `reme/` is being deprecated as legacy v3, an important context the response surfaced). The 139-site SQL identifier pattern, the flow-DSL `exec`/`eval` surface, and the by-design agent shell tool were covered in this write-up rather than the issue.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 53 |
| Medium | 106 |
| Low | 0 |
| Info | 0 (filtered) |

**159 total findings. After curation: three concrete real items for the issue + four interesting pattern-level discussions for the post. The series-recurring SQL-identifier-interpolation class is here at its largest scale yet (139 sites in three vector/file-store backend files), and the recurring `shell=True`-in-agent-shell-tool by-design class continues — but the *new* observation is a flow-execution DSL that pipes a `flow_content` string through `exec`/`eval` with a `__builtins__: {}` sandbox, where the realistic risk is brittleness to future input-source changes rather than today's exploitability.**

## Top findings (curated)

### 1. `reme/core/service/http_service.py:35` (+ duplicate at `reme4/components/service/http_service.py:51`) — unmitigated wildcard CORS with credentials

**Tool:** Semgrep (`wildcard-cors`)
**Verdict:** **Real best-practice item — and notably *not* mitigated, unlike the [agency-swarm](vrsen-agency-swarm.html) case from earlier this week.**

The middleware is configured with all four "danger" knobs at maximum:

```python
self.http_service.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

The CORS spec requires browsers to reject `Access-Control-Allow-Origin: *` together with credentials, so this is partially self-defeating in a modern browser. But it remains a real best-practice bug: (a) non-browser HTTP clients won't enforce that rejection, (b) any operator who later relaxes the browser to allow it has no in-code guard, and (c) the *intent* the middleware advertises ("any origin can send credentials here") is exactly what the spec exists to prevent. The right shape is the `agency-swarm` pattern from last week — explicitly downgrade `allow_credentials` to `False` when `*` is in the origins list, or (better) require an explicit origins list from configuration.

The same code is duplicated in `reme4/components/service/http_service.py:51`. The `reme/` and `reme4/` paths look like a v3/v4 in-progress migration; both copies need the fix.

### 2. `pyproject.toml` — `chromadb` CVE-2026-45829

**Tool:** pip-audit / Trivy
**Verdict:** **Real — single bump clears it.**

The pinned `chromadb` is past the published fix for [CVE-2026-45829](https://github.com/advisories?query=CVE-2026-45829). For a memory framework whose value-add is vector retrieval, the affected dependency is in the core path.

### 3. `reme4/components/file_graph/neo4j_file_graph.py:71` — `password: str = "neo4j"` default

**Tool:** Semgrep (`hardcoded-password-default-argument`)
**Verdict:** **Best-practice — the classic Neo4j default-credentials anti-pattern.**

```python
def __init__(
    self,
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "neo4j",
    database: str = "neo4j",
    **kwargs,
):
```

`neo4j/neo4j` are the documented default credentials Neo4j ships with, which is exactly why every Neo4j hardening guide tells you to change them on first run. Defaulting them in the connector means a developer who instantiates `Neo4jFileGraph()` without explicit credentials silently lands on a deployment shape that's trivially scannable. The defensible shape is either (a) make `password` required (no default, raise on missing), or (b) read from an env var with a clear error message when unset.

### 4. 139× SQL identifier interpolation across three backend files

**Files:**
- `reme/core/vector_store/pgvector_store.py` — 34 `asyncpg-sqli` + 10 `sqlalchemy-execute-raw-query` + 8 `formatted-sql-query` = **52 sites**
- `reme/core/vector_store/hologres_store.py` — 32 + 8 + 6 = **46 sites** (the Alibaba Hologres backend)
- `reme/core/file_store/sqlite_file_store.py` — 33 + 8 = **41 sites**

**Verdict:** **Same class as on eight prior scans — gated by Pydantic-validated identifiers today, brittle to future input-source changes.** This is the largest concentration of the recurring SQL-text identifier class in the series so far, beating [semantic-router](aurelio-labs-semantic-router.html) (50 sites in one file) and [pixeltable](pixeltable-pixeltable.html) (26 sites). The identifiers (table names, collection names, embedding-dimension constants) come from `BaseVectorStoreConfig` / `BaseFileStoreConfig` Pydantic models — config-controlled at startup, not user input. The defensible long-term shape remains SQLAlchemy's `quoted_name()` / `Identifier()` pattern; with this many sites concentrated in three backends, a per-backend `_quoted_table_ref(self)` helper at the top of each file generalizes the fix without rewriting every call site.

Bundled into the post rather than the issue because (a) the cross-scan evidence is by now consistent enough to treat as a known pattern, and (b) filing a 139-site refactor as a courtesy item is precisely the dstack-style "advertising" failure mode the methodology now guards against.

### 5. `reme/core/flow/base_flow.py:134-136` — `exec`/`eval` over a `flow_content` DSL string with `__builtins__: {}`

**Tool:** Semgrep (`exec-detected`, `eval-detected`)
**Verdict:** **Real-but-design-context-dependent — the more interesting pattern note of this scan.**

`BaseFlow.parse_expression()` parses a string like `op_a() >> op_b() >> op_c()` into an executable operation chain via:

```python
exec("\n".join(lines[:-1]), {"__builtins__": {}}, R.ops)
result = eval(lines[-1], {"__builtins__": {}}, R.ops)
```

The `__builtins__: {}` sandbox strips `open` / `__import__` / `eval` / `exec` from the namespace, and the `R.ops` namespace is a controlled registry of operation classes. Today's callers — `ExpressionFlow(flow_config: FlowConfig)` and `CmdFlow(flow: str)` — receive their string from developer-authored configuration (YAML / programmatic init), so the realistic risk on the current code is low. The interesting point is the brittleness: if a future API surface ever exposes "submit a flow string" to a user or to an LLM tool, this function flips from low-risk to LLM-driven-RCE-in-a-restricted-sandbox without any local code change. Worth knowing it sits in the call graph; left out of the issue because today's input source doesn't make it actionable.

### 6. `reme/memory/file_based/tools/shell.py:43` — `subprocess` with `shell=True` in a "shell" agent tool

**Tool:** Semgrep (`subprocess-shell-true`)
**Verdict:** **By-design — the recurring agent-shell-tool class.**

Same shape as [fast-agent](evalstate-fast-agent.html)'s `interactive_shell.py` and [agency-swarm](vrsen-agency-swarm.html)'s `PersistentShellTool.py`: the LLM controls the command on purpose because the tool exists to give the agent a shell. Documented across the series as a by-design class.

### 7-N. By-design / out of scope

| Finding | Files | Verdict |
|---|---|---|
| 4× `pickle.load` / `pickle.dump` | `reme4/components/{file_graph/nx_file_graph.py:39,48, keyword_index/bm25_index.py:310,322}` | **By-design** — local-file serialization of a NetworkX graph and a BM25 index; the same code that wrote the file reads it back. No network-deserialization path. |
| 5× `dangerous-globals-use` | Across the flow / op layer | Plugin / dispatch pattern — same class flagged on prior scans |
| 1× `logger-credential-leak` | (one site, **low** confidence per the [series downgrade](evalstate-fast-agent.html#notes-on-the-tool)) | **FP** — historically 6/6+ FPs |

## Patterns observed

**This is the second day in a row where the curated issue scopes to "three concrete items, the rest in the post."** Yesterday's [ouroboros](q00-ouroboros.html) post-only-plus-email pattern, then this issue: both follow the "one focused note" methodology the [dstack rejection](dstackai-dstack.html#maintainer-response-and-lessons) led to. The dscover is that on a 159-finding scan, the *non-issue* findings (the 139-site SQL pattern, the flow DSL, the shell tool, the pickle-from-local-file) are themselves the most useful part of the write-up. The issue is a short surgical list; the post is the substance.

**The 139-site SQL identifier cluster is the largest in the series — but the curation answer is the same.** Across nine scans now ([Upsonic](upsonic-upsonic.html), [PraisonAI](mervinpraison-praisonai.html), [airweave](airweave-ai-airweave.html), [honcho](plastic-labs-honcho.html), [dstack](dstackai-dstack.html), [pixeltable](pixeltable-pixeltable.html), [semantic-router](aurelio-labs-semantic-router.html), and now ReMe), the same pattern repeats: identifiers from Pydantic-validated config, no real injection vector today, brittle long-term. The cumulative lesson — *don't file 139 sites as 139 issues* — is now load-bearing for the issue scoping.

**The flow-DSL `exec`/`eval`-with-restricted-globals shape is new to the series.** Prior scans had `exec` for schema-to-Pydantic-class compilation ([agency-swarm](vrsen-agency-swarm.html)) and `eval` in deliberately-vulnerable Kubernetes test fixtures ([HolmesGPT](holmesgpt-holmesgpt.html)). ReMe's `parse_expression` is a third shape: a DSL parser for "compose operations into a flow string" that runs the string through `exec` + `eval` with a `__builtins__: {}` sandbox. It's the shape most likely to *flip* into a real vulnerability with a one-line change (any future "let users submit a flow" endpoint), which makes it worth flagging as a "watch this surface" item even though it's low-risk today.

## Notes on the tool

- Three weeks of scans of memory / agent / RAG frameworks ([MemoryBear](suanmosuanyangtechnology-memorybear.html), [pixeltable](pixeltable-pixeltable.html), [semantic-router](aurelio-labs-semantic-router.html), [honcho](plastic-labs-honcho.html), ReMe) confirms the per-subsystem helper refactor is the right shape for the SQL identifier class. The pattern is consistent enough that a tool-side suggestion ("this rule fires N≥20 times in this file → propose a `_quoted_table_ref(self)` helper at the top") would compress curation work.
- The `--ignore-samples` default plus the `logger-credential-leak` low-confidence downgrade together kept the FP pile at a single hit on a 159-finding scan. Both changes are paying off in real conditions.

## Disclosure timeline

- **2026-06-04** — Scan run at commit `a2d76cc03420`; findings curated. No `.github/dependabot.yml` present, but the curated issue is focused on three specific real items rather than the dep tail.
- **2026-06-04** — Public courtesy issue [#275](https://github.com/agentscope-ai/ReMe/issues/275) filed on agentscope-ai/ReMe with the three concrete items (wildcard CORS at both HTTP-service entrypoints, `chromadb` CVE, Neo4j default credentials).
- **2026-06-05 (~13h later)** — ✅ Maintainer [@jinliyl](https://github.com/jinliyl) responded item-by-item and closed [#275](https://github.com/agentscope-ai/ReMe/issues/275) as completed. **All three fixes verified in-code on `main`**:
  - `reme4/components/service/http_service.py` — `allow_credentials="*" not in cors_origins` (inline downgrade, exactly the suggested pattern). Maintainer note: the `reme/` copy is part of a legacy v3 codebase being deprecated, so the fix is in `reme4/` only.
  - `pyproject.toml` — `chromadb>=1.5.7` (bumped from `>=1.3.5`, clears CVE-2026-45829).
  - `reme4/components/file_graph/neo4j_file_graph.py` — `password: str | None = None` with fallback to `NEO4J_PASSWORD` env var, raises a `ValueError` when neither is provided.
  - Maintainer also acknowledged the out-of-scope `parse_expression()` flow-DSL surface as a "watch this" item for any future change exposing flow strings to end-users.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/agentscope-ai/ReMe" \
  --reports-dir reports/agentscope-ai-reme \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
