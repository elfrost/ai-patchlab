---
layout: default
title: "shy3130/tick-stock-panel: security scan"
date: 2026-08-31
---

# shy3130/tick-stock-panel — security scan

**Repository:** [shy3130/tick-stock-panel](https://github.com/shy3130/tick-stock-panel)
**Commit scanned:** `869c49bb0be4af6825e3797c9cde380d34488ad9`
**Scan date:** 2026-08-31
**Disclosure status:** public — [issue #224](https://github.com/shy3130/tick-stock-panel/issues/224)

Tick Stock Panel (TSP) is a self-hosted, zero-ops personal quantitative
workbench for China A-shares — screening, monitoring, backtesting, with an
LLM strategy layer (4.0k★, MIT, personal open-source). It stores and queries
market data through **DuckDB**, and that engine is the whole story of this
scan.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 24 |
| Medium | 50 |
| Low | 0 |
| Info | 3 |

**Total findings:** 77 (1 of interest after curation)

The high tier is entirely dependency-CVE version drift from `backend/uv.lock`
and `frontend/pnpm-lock.yaml` (Starlette SSRF-on-Windows-UNC, three Pillow DoS
CVEs, and so on) — worth a lockfile refresh, but nothing reachable in a way
that beats "update your deps." The one finding that matters came from reading
the code, not the tool output.

## Top finding

### `POST /api/screener/run` — custom-SQL screener is file-write RCE, not just file reads

- **File:** `backend/app/services/screener.py:343-349`
- **Tool:** manual review (semgrep flagged the same line as a generic medium `formatted-sql-query`, with no reachability or auth context)
- **Confidence:** high — exploit primitive verified against DuckDB directly
- **Why it matters:** `conditions` and `order_by` arrive unvalidated on the
  request body (`CustomRequest`, `api/screener.py:27-34`) and are f-string'd
  straight into a DuckDB `execute()`. A code comment argues the isolated
  `:memory:` connection bounds any injection to *reading* `read_csv`/`read_parquet`
  files. It does not: a fresh `:memory:` connection keeps
  `enable_external_access` **on**, so `COPY TO` writes arbitrary files
  (`authorized_keys`, `crontab`) → RCE — the exact vector the maintainer already
  confirmed real when they fixed [issue #150](https://github.com/shy3130/tick-stock-panel/issues/150).
  For the authenticated operator this is by design (custom-SQL screening is the
  advertised feature). The unauthenticated path is narrow but real: before a
  password is set, the auth middleware lets any **RFC1918 LAN** client through
  (`main.py` case 1 + `auth.py:_is_local_network`), and the shipped
  `docker-compose.yml` binds `0.0.0.0`.
- **Recommendation:** this connection registers its data via
  `con.register("enriched", df.to_arrow())` and never reads a file, so external
  access can be disabled *on this connection specifically* —
  `duckdb.connect(":memory:", config={"enable_external_access": False})` — which
  kills both the write→RCE and read→exfil vectors while leaving the operator's
  SQL `WHERE` fully intact. Crucially it does **not** re-trigger the reason #150
  gave for keeping external access on globally (that global switch also disables
  `read_parquet`, the core data path) — this isolated connection never touches
  `read_parquet`.

This is the sink the original #150 reporter listed as "sink #1" and the
maintainer refuted — correctly for `api/screener.py`, but the real
`conditions`/`order_by`/`execute()` combination lives in the *other*
`screener.py`, under `services/`, and the `quote_ident` fix never reached it.

## Patterns observed

The interesting thing about this repo is how well-defended it already is, which
is why the scanner's 77 findings collapse to one. The #150 SQL-injection fix was
model behaviour: the maintainer verified each claimed sink by hand, refuted the
one that did not exist, centralised the fix into a shared `quote_ident` primitive,
added 24 security tests including end-to-end `COPY TO` / `UNION` assertions, and
documented *why* they rejected the blunt "just turn off `enable_external_access`"
fix (it would disable `read_parquet`, the app's core data access). The auth layer
is similarly careful: the `X-Forwarded-For` trust is gated on the direct peer
being loopback/LAN first (so a public client cannot spoof `127.0.0.1` — the
verify-then-branch order that so many projects get backwards), login has
rate-limiting with lockout, sessions are HttpOnly cookies, and the pre-setup
window explicitly 403s public clients to prevent takeover. The CORS config —
`allow_origins=*` with `allow_credentials=false` — is the *correct* trade for a
self-hosted LAN tool: a malicious web page can reach unauthenticated endpoints
but cannot ride the operator's session cross-origin.

So the one surviving finding is not a rule miss in the usual sense — semgrep
*did* flag `services/screener.py:349`. It is that no rule can see the three facts
that compose into the finding: (1) the sink is operator-SQL by design, (2) the
containment the maintainer *documented in a comment* is factually wrong about
read-vs-write, and (3) there is a pre-setup, LAN-adjacent window where a
non-operator reaches it. Each is individually invisible; the finding is their
product. It also needed the one thing static analysis cannot do — running the
`COPY TO` primitive against a real `:memory:` connection to prove the comment
wrong.

The `enable_external_access`-on posture is a genuine double-edged design choice.
It is load-bearing (`read_parquet` is how the app reads its own data), which is
exactly why the #150 fix escaped identifiers instead of disabling it. The lesson
this scan adds: that global constraint does not apply to the *isolated* query
connections that never read files — those can and should turn it off.

## Notes on the tool

- **The finding is a "documented-containment-is-wrong" shape** — the security
  argument lives in a source comment, and the exploit primitive contradicts it.
  This is the same family as the docstring-contract-oracle backlog item: diff a
  security function's *stated* failure mode against what the code actually does.
  Worth a first-class curation prompt: "does any comment claim a bound that a
  one-command primitive can break?"
- **Two files named `screener.py`** is why the #150 refutation missed this sink.
  When a reported location does not match, resolve the *symbol* (here
  `conditions`+`order_by`+`execute`) across every same-named file before calling
  it a false positive — a lesson that generalises past this repo.
- **`enable_external_access` is invisible to the SCA and SAST layers** — trivy
  and semgrep both scanned the DuckDB call sites; neither can know that the
  engine's file-access switch is left on, which is the difference between "SQL
  injection into a sandbox" and "RCE." A DuckDB-aware note ("f-string into
  `execute()` + external access on = file write, not just query") would have
  ranked this above the dependency noise.
- The 24-high dependency tier is real version drift but reachability-blind: the
  Starlette Windows-UNC SSRF needs a Windows host serving `StaticFiles` from a
  UNC path; the Pillow CVEs are DoS. The "affected surface / reachable here?"
  columns the SCA backlog keeps asking for would have de-ranked all of them.

## Disclosure timeline

- 2026-08-31 — scan run, exploit primitive verified, issue [#224](https://github.com/shy3130/tick-stock-panel/issues/224) filed (public; no SECURITY.md, PVR disabled, personal MIT project)
- 2026-09-03 — fixed and closed by the maintainer in `e89ea9b`, three days after filing. The
  screener's isolated in-memory connection is now created with
  `config={"enable_external_access": False}`, so an injected `read_parquet` /
  `COPY` raises instead of touching the filesystem; view data is injected through
  `con.register`, which the switch does not affect, so normal filtering is
  unchanged. The maintainer added a regression test with a **positive and negative
  control** — an unhardened connection is shown to read an arbitrary parquet file
  through the same injected SQL (confirming the attack surface was real), and the
  hardened one rejects it. 592 tests pass.

## Reproduce

```bash
git clone https://github.com/shy3130/tick-stock-panel /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/shy3130-tick-stock-panel --min-severity medium
```
