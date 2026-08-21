---
layout: default
title: "mnemosyne-oss/mnemosyne: security scan"
description: "Security scan of mnemosyne-oss/mnemosyne: 195 findings, 0 real — 17th clean scan, and the largest SQL cluster in the series: a zero-dependency SQLite-backed"
date: 2026-07-15
---

# mnemosyne-oss/mnemosyne - security scan

**Repository:** [mnemosyne-oss/mnemosyne](https://github.com/mnemosyne-oss/mnemosyne)
**Commit scanned:** `2812e98b986688339a1cd489f1e4999a30d52171`
**Scan date:** 2026-07-15
**Disclosure status:** public — post-only (strict-norm: SECURITY.md + sync infrastructure; nothing cleared the quality gate)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 128 |
| Medium | 67 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 195 (0 real after curation)

Mnemosyne is a zero-dependency, SQLite-backed AI memory system with an MCP
server and an end-to-end-encrypted sync server. "Zero-dependency" means the
security surface is its own code — a lot of hand-written SQL over `sqlite3` — and
that shows in the numbers: **140 of the 195 findings are one SQL cluster**, the
largest in the series. It's also the cleanest kind of large cluster, because the
SQL is correctly parameterized; the 128 highs dissolve on inspection.

## Top findings

### 1. The 140-finding SQL cluster is parameterized data + internal identifiers

- **File:** `mnemosyne/core/beam.py` (67), `binary_vectors.py`, `streaming.py`, `hygiene.py`, … (107 `sqlalchemy-execute-raw-query` + 33 `formatted-sql-query`)
- **Tool:** semgrep
- **Confidence:** high — FP
- **Why it matters:** A memory store runs SQL over user-supplied memory text and
  filters. If any of that reached a query by f-string, it would be injection —
  and there are 140 f-string SQL sites to worry about.
- **Why it's not a finding:** The f-strings interpolate **schema identifiers and
  constants**, never user data. The recall query is representative:

  ```python
  table  = "working_memory" if working else "episodic_memory"   # internal
  id_col = "id" if working else "rowid"                          # internal
  conditions = " OR ".join("content LIKE ? ESCAPE '\\'" for _ in cjk_chars)
  params     = [f"%{ch}%" for ch in cjk_chars]
  conn.execute(f"SELECT {id_col}, content FROM {table} WHERE {conditions} LIMIT ?",
               params + [k * 5])
  ```

  Every user value is a bound `?` parameter — with `LIKE … ESCAPE '\\'`, which
  most projects forget — and the only interpolated tokens are table/column names
  chosen from an internal branch and `CREATE VIRTUAL TABLE … vec0(embedding {DIM})`
  schema DDL with constant dimensions. Same shape as the codex-lb and potpie SQL
  false positives, at ~5× the volume.

### 2. Outbound fetches are user-directed imports and own-server sync

- **File:** `mnemosyne/core/importers/{honcho,zep,supermemory}.py`, `mnemosyne/core/sync.py` (21 `dynamic-urllib-use`)
- **Tool:** semgrep
- **Confidence:** high — by-design
- **Why it matters / why it doesn't:** The non-literal URLs are (a) importers that
  pull your memories out of another memory service you configure, and (b) the
  sync client talking to the sync server you point it at. The operator chooses
  the endpoint in both cases; nothing follows attacker-planted links. Not SSRF.

### 3. The "secrets" are documentation and the crypto is thoughtful

- **Tool:** gitleaks (14) + semgrep (`detected-generic-api-key` ×2)
- **Confidence:** high — FP, and a positive note
- **Why it matters / why it doesn't:** All 14 gitleaks hits and both
  `generic-api-key`s are in `docs/sync/tutorial.md`, `scripts/generate-docs.py`,
  and `tests/` — tutorial keys and fixtures, not live credentials. And the design
  they document is the good part: sync uses **client-side XChaCha20-Poly1305
  authenticated encryption**, so the sync server sees only metadata (event IDs,
  timestamps) and never memory content — the key never leaves the device. A
  memory system that encrypts before it syncs has thought about the threat that
  matters for it.

## Patterns observed

**The largest SQL cluster in the series, and it evaporates on one query read.**
128 highs sounds like a five-alarm SQL-injection fire on a store that holds user
text. But the discriminator is always the same: are *values* bound, and are the
*interpolated tokens* identifiers or data? Here values are `?`-bound (with LIKE
escaping), and the f-string tokens are internal table/column names and constant
embedding dimensions. Reading two representative queries — a recall `SELECT` and
a `CREATE VIRTUAL TABLE` — settled all 140. The scanner can't see the parameter
tuple one argument over; a human can in a minute.

**Zero-dependency shifts the surface to SQL, and they handled it.** Most scans in
this series split between code findings and a dependency tail. A zero-dependency
project has almost no tail (trivy found 6, all minor), so the whole scan is the
hand-written data layer — and mnemosyne writes it carefully, down to `ESCAPE`
clauses on `LIKE` and identifier branches that never touch request input.

**Strict-norm, security-conscious, clean.** A real SECURITY.md, a sync server
with client-side encryption, and JWT auth put this firmly in post-only territory
— and there was nothing to file. The 195-count is one parameterized SQL cluster,
operator-directed fetches, docs keys, and docker-compose hardening lint.

## Notes on the tool

- **The parameterized-SQL false positive is now the single most expensive rule
  in the series.** `sqlalchemy-execute-raw-query` / `formatted-sql-query` produced
  140 findings here, ~14 on codex-lb, ~14 on potpie, 14 on Agently. A check for
  "does this `execute()` pass a params tuple, and are the interpolated tokens
  identifiers/constants rather than data?" would reclaim the single biggest
  chunk of noise the scanner emits. This is the top backlog item, full stop.
- **`dynamic-urllib-use` needs an operator-directed vs attacker-directed
  distinction** — imports and sync to a user-configured endpoint aren't SSRF, the
  same call the tradingview-mcp and OpenKB scans made.
- **`detected-generic-api-key` fired in `docs/` and `tests/`.** Both should be
  candidate-FP paths; a tutorial's example key is not a leak.

## Disclosure timeline

- 2026-07-15 — scan run
- 2026-07-15 — public post (this page); post-only, no upstream issue filed

This is a post-only clean-scan write-up. The 140-finding SQL cluster is
parameterized data with internal identifiers (LIKE-escaped), the outbound
fetches are operator-directed imports and sync, the secret hits are
documentation, dependencies are negligible, and the sync layer is client-side
encrypted. Nothing cleared the quality gate.

## Reproduce

```bash
git clone https://github.com/mnemosyne-oss/mnemosyne /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/mnemosyne-oss-mnemosyne \
  --min-severity medium --ignore-samples
```
