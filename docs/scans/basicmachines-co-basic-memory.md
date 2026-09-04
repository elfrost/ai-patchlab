---
layout: default
title: "basicmachines-co/basic-memory: security scan"
description: "Security scan of basicmachines-co/basic-memory: 270 findings above the medium floor, zero real after curation. Local-first curated review with Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-09-04
---

# basicmachines-co/basic-memory — security scan

**Repository:** [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory)
**Commit scanned:** `a55003e7d0ab`
**Scan date:** 2026-09-04
**Disclosure status:** post-only — nothing filed upstream (strict-norm target, zero findings survived curation)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 3 |
| High | 116 |
| Medium | 151 |
| Low | 0 |
| Info | 3 |

**Total findings:** 270 above the `medium` floor — **zero real after curation**

Twenty-ninth clean scan in this series. The target is a **local-first MCP
memory server** (3.8k★, AGPL-3.0, active) that lets an AI assistant read and
write markdown notes inside directories you configure. The description makes it
sound small. The tree does not: alongside the stdio MCP tools there is a full
FastAPI v2 REST layer, a SQLite and a PostgreSQL/pgvector backend, a cloud-sync
module built on rclone and WebDAV, and an SSE/HTTP transport shipped in the
`docker-compose.yml`. That is a lot of surface for a tool that bills itself as
"runs on your machine."

## The security policy was the method

`basic-memory` ships a `SECURITY.md` that is not a mailbox with a version table
around it. It is a **threat model**, and it makes three checkable claims. The
value of a claim like this is that it can be wrong, so I spent the scan trying
to break each one rather than reading the finding list.

**Claim one — path traversal is blocked at `validate_project_path()`.** The
guard resolves `project_path / path` and then tests `resolved.is_relative_to(
project_path.resolve())`. That is the correct containment shape: a `..` or an
absolute path resolves to something outside the root and fails the check. In
front of it sits a second layer, `valid_project_path_value()`, that rejects
`~`, rejects `..` as a path *segment* (while still allowing a filename like
`hi-everyone..md`), rejects a leading backslash, and rejects absolute paths and
Windows drive letters. It even handles the Windows trailing-dot-and-space trick
(`.. ` normalizes to `..`). Both the escaping layer and the resolve check would
each have to fail. Neither does. The claim holds.

**Claim two — subprocess calls pass paths as data, not shell strings.** Every
`subprocess` call I opened uses an explicit argument list with the default
`shell=False`: the `find`-based scan optimizer, the auto-update path, and the CI
helper's `git config --get remote.origin.url`. No user string reaches a shell.
The claim holds.

**Claim three — the SQLite PRAGMA tuning is validated before interpolation.**
`db.py` builds PRAGMA statements with f-strings, which is exactly what
Semgrep's formatted-SQL rule flags. Every numeric PRAGMA is wrapped in
`int(...)` and the one string PRAGMA (`synchronous`) is checked against an
allowlist before it is used. The code even carries a comment saying so. The
claim holds.

Running a documented threat model as an oracle and getting three yeses is the
result worth publishing. The [tracecat](tracecathq-tracecat.html) scan did the
same thing with a scoping document and returned a unanimous yes; this is the
[docstring-as-contract](jgravelle-jcodemunch-mcp.html) probe applied to a whole
policy file. A check that can only ever confirm is not a check.

## The 56 first-party findings are one false positive, wearing 56 hats

Every Semgrep finding inside `src/basic_memory/` is a SQLAlchemy `text()` call —
the `avoid-sqlalchemy-text` and `sqlalchemy-execute-raw-query` cluster that is
the single most common false positive in this series. This is the best-defended
instance I have scanned.

The interesting half is full-text search, because that is the one place a user
value (the search query) reaches a raw query string. FTS5 `MATCH` cannot be
parameterized the way a `WHERE col = ?` can, so a careless project builds the
match string by interpolation and ships an injection. `basic-memory` does the
opposite twice over. The search term goes through `_prepare_single_term` /
`_prepare_boolean_query`, which double-quote-escape (`'"'.replace('"', '""')`)
and neutralize FTS5 operator characters — and then the *prepared* term is
**bound as a parameter**: `params["text"] = processed_text`, executed as
`search_index.title MATCH :text`. The Postgres backend mirrors this with
`tsquery` operand escaping (`replace("'", "''")`). Escaped *and* bound. Nothing
to inject.

The rest of the cluster is generated bind-placeholder lists (`:entity_id_0`,
`:row_id_1`), internal constants, and Alembic migration DDL. The two
`dynamic-urllib` findings resolve to fixed hosts — a PyPI version check and an
opt-out Umami telemetry endpoint — not attacker-influenced URLs. None of the 58
first-party findings is real.

## The three criticals are a benchmark harness, and the product is already patched

Trivy's three criticals are an `authlib` JWK-header-injection auth bypass, a
`fastmcp` authenticated-SSRF path traversal, and a `node-tar` gzip-bomb DoS.
Every one of them is pinned to a **non-shipped subtree**: `benchmarks/uv.lock`
and `integrations/openclaw/bun.lock`. The benchmark lock pins `authlib 1.6.8`
and `fastmcp 3.0.2`.

The tell is what Trivy *did not* flag. `basic-memory` depends on `authlib` and
`fastmcp` at runtime — they are in the root `pyproject.toml` — but the root
`uv.lock` resolves them to `authlib 1.7.2` and `fastmcp 4.0.0b1`, and Trivy read
that lock and raised nothing. The product ships fixed versions; only the
benchmark harness, which nobody deploys, carries the stale pins. This is the
[test-only-dependency](../what-83-scans-found.html) shape: split the ownership
before you rate the severity, and a "critical" on a benchmark fixture stops
being a product vulnerability.

## The one architectural fact — and why it is not a finding

`basic-memory` has a genuine networked deployment. The shipped
`docker-compose.yml` publishes port 8000 and runs
`basic-memory mcp --transport sse --host 0.0.0.0`, with **no authentication** on
the SSE/streamable-HTTP transport. An MCP client that can reach that port can
read, write, and delete notes in the mounted project directory. In most of the
repos in this series that would be the filing.

Here it is not, because the maintainer says so first. The line directly above
the command in the compose file reads: `# IMPORTANT: The SSE and
streamable-http endpoints are not secured`. That is a boundary advertised
*downward* — the same move [tracecat](tracecathq-tracecat.html) made when it
declared its Docker Compose isolation "None." An out-of-scope declaration made
at the exact place a deployer would copy the command is not a hidden footgun; it
is a documented posture, and reporting it back would be reporting the project's
own README to it.

The one honest gap worth a sentence: the `SECURITY.md` threat model discusses
only the local file-access surface ("runs on your machine with your user
permissions") and is silent on the networked transport, while the warning lives
only in the compose comment. Someone who reads the security policy and not the
compose file could miss it. Aligning the two — one sentence in `SECURITY.md`
saying the HTTP/SSE transport is unauthenticated and must sit behind your own
gateway — would close the gap. That is documentation hardening, not a
vulnerability, and it is not filed.

## Notes on the tool

- **Partial Semgrep coverage, named and then cleared.** One rule
  (`request-with-http`) timed out on `mcp/tools/search.py`, and Semgrep's
  parser rejected two files (`markdown/temporal_qualifier.py`,
  `ci/project_updates.py`) — the 3.13 parser chokes on newer syntax. Absence of
  a finding from a rule that never ran is not evidence of clean, so I opened all
  three by hand: `search.py` only uses the internal `memory://` scheme (no
  insecure HTTP), `temporal_qualifier.py` has no security-relevant construct,
  and `project_updates.py`'s only subprocess call is an argument-list
  `git config`. The gap is real; the code behind it is clean.
- **Gitleaks fired four times, all on fixtures.** `sk-live-0123456789abcdef`,
  `bmc_test_key_12345`, and friends, all under `benchmarks/tests/` and
  `tests/`. Obvious placeholders. The recurring lesson that finding *count*
  scales with test-surface richness, not risk, held again.
- **The unaudited-lockfile meta finding did its job.** pip-audit reads
  `pyproject.toml` floors and does not read `uv.lock`; the scanner flagged that
  as an install-path question rather than assuming clean. Trivy read the lock,
  so the two tools together covered both install paths — which is precisely how
  the "product is patched, benchmark is not" split above became visible.

## Disclosure timeline

- 2026-09-04 — scan run; zero findings survived curation
- 2026-09-04 — public post (this page). Nothing filed upstream: strict-norm
  target (`SECURITY.md` forbids public vulnerability issues) and no real finding
  to report.

## Reproduce

```bash
git clone https://github.com/basicmachines-co/basic-memory /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/basicmachines-co-basic-memory \
  --min-severity medium --ignore-samples
```
