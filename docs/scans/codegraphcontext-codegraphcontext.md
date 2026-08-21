---
layout: default
title: "CodeGraphContext/CodeGraphContext: security scan"
description: "Security scan of CodeGraphContext/CodeGraphContext: 112 findings, 0 real — 24th clean scan. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-07-26
---

# CodeGraphContext/CodeGraphContext — security scan

**Repository:** [CodeGraphContext/CodeGraphContext](https://github.com/CodeGraphContext/CodeGraphContext)
**Commit scanned:** `e839c95e488e41b45bc96ab1b1968bf3da90b7aa`
**Scan date:** 2026-07-26
**Disclosure status:** public — post-only (strict-norm: private-reporting `SECURITY.md` — email-only, coordinated disclosure)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 32 |
| Medium | 80 |
| Low | 0 |
| Info | 0 |

**Total findings:** 112 (0 real after curation)

CodeGraphContext (CGC, 4.0k★, MIT) is an **MCP server plus a CLI** that indexes
a local codebase into a graph database — Neo4j, embedded KùzuDB, or FalkorDB —
so an AI assistant can ask structural questions ("who calls this function?",
"what inherits from this class?") over a real code graph instead of a flat
grep. That is a rich, dangerous-looking surface for a security tool to chew on:
it reads arbitrary source trees off disk, builds and runs graph queries, ships
an **optional HTTP/SSE gateway** advertised for ChatGPT Actions and remote
agents, a VSCode extension, a local visualization server, and a marketing
website. For a code-graph MCP tool the three questions are: *is the graph-query
path injectable?*, *is the optional gateway an unauthenticated network
exposure?*, and *are the database credentials and embedded secrets handled
safely?* All three close — and they close because the maintainer has already
done the security work, out loud, in the code.

## Top findings (all curated out)

### 1. 12 graph-query "SQL highs" — internal DDL, the purest identifier FP in the series

- **File:** `src/codegraphcontext/core/database_embedded_kuzu.py:303,313,315,398,400,417`
- **Tool:** semgrep (`sqlalchemy-execute-raw-query` ×6 + `formatted-sql-query` ×6)
- **Verdict:** false positive — the [#1 recurring parameterized-**identifier**
  FP](mnemosyne-oss-mnemosyne.html)

Every flagged `self._conn.execute(f"…")` is **schema DDL**, not a data query:
`CREATE NODE TABLE`, `CREATE REL TABLE GROUP`, `ALTER TABLE … ADD`. The only
interpolated tokens are the `table_name`, `schema`, and `column_type` fields —
and each one is drawn from a **hardcoded constant tuple list** inside the same
module (`node_tables`, `rel_tables`, `simple_migrations`, `_CALLS_SUBTABLES`, …).
No caller-supplied string reaches any of them; there is no data value in these
statements at all. This is the identifier FP in its purest form — Kùzu's schema
builder writing its own fixed schema.

### 2. `wildcard-cors` on the gateway — paired with `allow_credentials=False`, and commented

- **File:** `src/codegraphcontext/api/app.py:24`
- **Tool:** semgrep (`python.fastapi.security.wildcard-cors`)
- **Verdict:** false positive — **credit the defense**

The `allow_origins=["*"]` is exactly the config semgrep flags, but it sits
beside `allow_credentials=False` and a comment that explains *why*: "Credentials
must stay disabled while origins is a wildcard; the combination is rejected by
browsers and would leak cookie-authed responses to any site." Wildcard CORS is
only dangerous with credentials on — the developer named the trap and stayed
out of it.

### 3. Optional HTTP gateway — auth exists, warns loudly, but defaults to `0.0.0.0`

- **File:** `src/codegraphcontext/cli/main.py:1044` (`api start`) · `src/codegraphcontext/api/auth.py` · `src/codegraphcontext/api/router.py:22`
- **Tool:** manual sweep (no scanner flagged it)
- **Verdict:** hardening observation — **not filed** (see disclosure note)

The primary MCP transport is **STDIO** (`server.run()` reads JSON-RPC off
stdin — local, no network). The gateway is a separate, opt-in command,
`cgc api start`. Its auth story is genuinely well-built: `require_api_key` is a
**router-wide FastAPI dependency** (`APIRouter(dependencies=[Depends(require_api_key)])`),
uses `secrets.compare_digest` for constant-time comparison, is backward-compatible
opt-in via `CGC_API_KEY`, and — when unset — logs a prominent startup **warning
that names the exact exposure**: *"CodeGraphContext API is running WITHOUT
authentication. Anyone who can reach this server can index code, run Cypher
queries and call tools."* The one residual is that `cgc api start` defaults its
`--host` option to `0.0.0.0` while auth is opt-in, so an operator who exposes
the gateway without setting a key binds an unauthenticated Cypher/tool endpoint
to all interfaces (the same class as the resolved [code-graph-rag
#808](vitali87-code-graph-rag.html)). The safer default would be `127.0.0.1`,
requiring an explicit `--host 0.0.0.0` to publish. That said, the project has
**already pre-mitigated most of this**: the auth mechanism ships, the warning
ships, and the API reference documents `cgc api start --host 127.0.0.1` as an
option. It is a secure-by-default nit on a feature the maintainer clearly
understands.

### 4. Neo4j credentials — no default password, fails closed

- **File:** `src/codegraphcontext/core/database.py:79-81`
- **Tool:** manual sweep (gitleaks flagged only CI/test material)
- **Verdict:** false positive — **credit the defense**

`neo4j_password = os.getenv('NEO4J_PASSWORD')` has **no fallback default** — the
driver raises `Neo4jConnectionError` with actionable guidance if it is unset,
and even fast-fails on an unreachable host before building a driver. The
username defaults to the standard `neo4j`; there is no shipped default password
to guess. The `neo4j/12345678` that gitleaks surfaced is a **throwaway CI
service-container password** in `db-parity-check.yml`, not a real credential.

### 5. Secrets — Supabase anon keys (public by design) + generated protobuf + CI material

- **File:** `website/src/lib/supabase-client.ts:5`, `website/src/pages/Explore.tsx:465`, `website/public/pr-data/…989.json:45`, `src/codegraphcontext/tools/scip_pb2.py:23`
- **Tool:** gitleaks (`jwt` ×3, `generic-api-key` ×2)
- **Verdict:** false positive

The three JWTs are Supabase **anon keys** embedded in the marketing website's
frontend — public by design (row-level security enforces access; they are meant
to ship to the browser), the same class as the publishable keys credited on
[IBM ContextForge](ibm-mcp-context-forge.html). The `generic-api-key` in
`scip_pb2.py` is the `serialized_pb=b"…"` **descriptor bytes of a generated
protobuf module**, not a secret.

## Patterns observed

This is the **24th clean scan** in the series, and one of the cleaner
*security-aware* codebases in it — not clean because the surface is small
(112 findings, a full HTTP gateway, three graph backends, a VSCode extension,
and a website), but because the maintainer keeps writing the mitigation right
next to the risk. The CORS wildcard carries the credentials caveat in a comment;
the unauthenticated gateway logs a warning that spells out precisely what an
attacker could do; the Kùzu migration code, like [Osmantic/ODS](osmantic-ods.html)'s
token-store before it, validates identifiers it already controls. There is even
a `tests/unit/utils/test_path_sandbox_security.py` guarding the indexer's
path-confinement — a test suite for a threat the scanner never raised.

The count is, once again, structural rather than substantive. Two rule families
account for most of it: **43 `github-actions-mutable-action-tag`** mediums
(SHA-pin hygiene) and the **12 graph-DDL identifier "highs"**. The genuine
residuals are the familiar reachability-gated tail — a `website/` frontend
dependency refresh (lodash, PostCSS, `ws`, react-router — the visualization
UI's npm tree, a [Kiln](kiln-ai-kiln.html)-shaped lockfile drift) and a
transitive `protobuf 3.20.3` bump behind the Neo4j driver. The one exception to
"all FP" is a genuine **secure-by-default** hardening opinion (the `0.0.0.0`
gateway default), and even that the project has mostly answered already.

The XML parsers deserve a specific note: `maven.py` and `mybatis.py` both use
stdlib `xml.etree.ElementTree.parse()` on `pom.xml` / `*Mapper.xml` files as
they index a target repo, which trips `use-defused-xml-parse`. As on
[KiCAD-MCP](mixelpixx-kicad-mcp-server.html), this is **DoS-only** — CPython's
etree does not resolve external entities, so the exposure is billion-laughs
entity expansion on a maliciously-crafted file the operator chose to index, not
XXE file-read or SSRF. Swapping in `defusedxml` is still worth doing as
defense-in-depth, and it is the single most concrete code change the whole scan
produced.

## Notes on the tool

- **`0.0.0.0`-default gateway bind is manual-sweep-only, again.** Semgrep found
  the wildcard CORS but not the more consequential insecure-by-default network
  bind (`host="0.0.0.0"` + opt-in auth), because it lives in a Typer option
  default two files away from the FastAPI app. This is the same under-count
  shape as the [zotero-mcp](54yyyu-zotero-mcp.html) / [docetl](ucbepic-docetl.html)
  sweeps: the finding that matters is a *default value* plus an *absence of a
  key*, which no single-file AST rule sees. Backlog: a "network-bind + auth
  default" cross-file heuristic for CLI-launched servers.
- **`.github/SECURITY.md` must count for strict-norm detection.** The initial
  pre-check queried root `SECURITY.md` (404) and nearly mis-classified this repo
  as non-strict-norm; GitHub also recognizes `.github/SECURITY.md`, which here
  carries a real email-only private-reporting policy. Backlog: the strict-norm
  probe should check `SECURITY.md`, `.github/SECURITY.md`, and `docs/SECURITY.md`.
- **DDL vs DQL for the identifier FP.** Every `sqlalchemy-execute-raw-query` hit
  here was `CREATE`/`ALTER TABLE` (schema DDL), which by construction cannot
  carry a bound data value. A cheap pre-filter — "does the interpolated
  statement start with a DDL keyword?" — would auto-downgrade this entire
  cluster below `--min-severity`.
- **Public-by-design frontend keys** (Supabase anon JWTs) keep landing as
  gitleaks highs; a `website/` + `*anon*`/`publishable` heuristic would suppress
  them, consistent with the IBM ContextForge baseline lesson.

## Disclosure timeline

- 2026-07-26 — scan run; 0 real findings after curation
- 2026-07-26 — public post (this page). **Post-only:** the project ships a real
  `.github/SECURITY.md` requiring private, email-only vulnerability reporting
  under coordinated disclosure. The single hardening observation (the
  `0.0.0.0` gateway default) is a publicly-documented, self-warned configuration
  choice — the maintainer's own startup warning and API docs already surface it —
  so it is described here as methodology commentary, not filed as a disclosure.

## Reproduce

```bash
git clone https://github.com/CodeGraphContext/CodeGraphContext /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/codegraphcontext-codegraphcontext --min-severity medium
```

---

*This scan is a probabilistic signal from an automated toolchain plus manual
curation, not a security audit or a guarantee. Findings are dispositioned in
good faith; a "0 real" result means nothing rose above the noise floor on this
commit, not that the code is free of vulnerabilities.*
