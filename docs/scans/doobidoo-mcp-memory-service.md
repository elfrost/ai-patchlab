---
layout: default
title: "doobidoo/mcp-memory-service: security scan"
description: "Security scan of doobidoo/mcp-memory-service: 176 findings above the medium floor, zero real after curation. The four real critical bugs were fixed the same day and none was visible to the scanner. Local-first review with Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-09-05
---

# doobidoo/mcp-memory-service — security scan

**Repository:** [doobidoo/mcp-memory-service](https://github.com/doobidoo/mcp-memory-service)
**Commit scanned:** `07971a62a2ba`
**Scan date:** 2026-09-05
**Disclosure status:** post-only — nothing filed upstream (strict-norm target, zero findings survived curation)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 85 |
| Medium | 88 |
| Low | 0 |
| Info | 3 |

**Total findings:** 176 above the `medium` floor — **zero real after curation**

Thirtieth clean scan in this series. The target is a **persistent memory server
for AI agents** (1.9k★, Apache-2.0, extremely active) that speaks MCP over
stdio, SSE and Streamable HTTP, stores memories in SQLite-vec, Cloudflare,
Milvus or a hybrid backend, and ships a full FastAPI dashboard with OAuth 2.1.
It is designed to be reachable from a browser via claude.ai Remote MCP, so
unlike most desktop MCP servers it genuinely expects to listen on a network.

This scan is worth reading not for what it found but for what it could not see.
The maintainer published **four critical advisories on the exact day I scanned**,
all fixed in the version at HEAD. The scan is therefore a controlled experiment:
run a generic security sweep against a codebase whose real, coordinated-disclosure
bugs are known and dated, and count how many the tools surface. The answer is
zero.

## The four real bugs, and why the scanner missed every one

On 2026-09-05 the project published these, all patched in 11.11.0 — the commit
I scanned:

1. **SSE transport had no authentication** on `/sse` and `/messages/`
   (GHSA-2hh8-qjxc-43x3, CWE-306). Bound past loopback, anyone who reached the
   port got the full MCP tool surface.
2. **Streamable HTTP exposed the filesystem tools.** The FastAPI JSON-RPC shim
   filtered `memory_harvest` and `memory_ingest` out of remote calls; the
   Streamable HTTP transport did not copy that filter, so an authenticated
   remote caller could read host files into the store (GHSA-7crr-2r7w-cpfm,
   CWE-552/610).
3. **Open Dynamic Client Registration minted read-write tokens.** With OAuth on
   and the registration key unset, a self-registered confidential client could
   run the `client_credentials` grant and get a `read write` bearer with no
   owner API key (GHSA-6mvm-q4j3-27qg, CWE-306/862).
4. **The earlier `client_credentials` bypass** the above built on
   (GHSA-5p27-64mv-pr73, CWE-287/863).

Every one of these is an **absence** or a **parity gap**: a check that should be
present in one code path because it is present in its sibling. A pattern-matching
SAST rule fires on the shape of dangerous code — an `eval`, an f-string in a
query, a wildcard CORS literal. It has nothing to match on when the defect is
that an auth call is *not there*, or that a filter applied on transport A was
never added to transport B. Software Composition Analysis is worse placed still:
these are first-party logic bugs, not vulnerable dependency versions. The scan's
176 findings did not include a single one of the four, because the four are not
findings in the sense a scanner means the word.

I confirmed the fixes are live in the scanned commit rather than taking the
advisories on faith. `_assert_bind_is_authenticated()` now refuses to start any
transport on a non-loopback host with neither an API key nor OAuth configured.
A single shared `check_transport_auth()` gates SSE and Streamable HTTP from one
function, with a comment explaining that the second copy is exactly how the SSE
gap drifted open. The `/mcp` and `tools/call` paths run `_is_local_only()`
against the same `local_only_tools()` set on every transport. And
`_refuse_client_credentials_while_open()` blocks the DCR path unless a
registration key is set. The maintainer did not just patch four holes; they
collapsed the duplicated logic that let the holes diverge.

## What the 176 findings actually were

The dominant cluster, 47 of the 67 first-party findings, is the
**parameterized-SQL identifier** false positive this series has now logged nine
times. Semgrep's `sqlalchemy-execute-raw-query` and `formatted-sql-query` rules
flag any query string built with an f-string. In `storage/mixins/store.py`
every `INSERT` binds its values with `?` placeholders and a tuple; the only
interpolated token is a savepoint name, `f"store_{os.urandom(4).hex()}"`, which
is server-generated random hex, not caller input. In `storage/mixins/migrations.py`
the interpolated values are an integer embedding dimension and pragma
names drawn from a fixed dict. In `utils/db_utils.py` it is `SELECT COUNT(*)
FROM {table}` over a hardcoded internal table list. None of them puts a
caller-controlled *value* into SQL text.

The three `tainted-sql-string` hits in `web/api/manage.py` are the sharpest
illustration of the rule missing the point. The flagged lines are
`operation_desc = f"Delete memories with tag '{request.tag}'"` — a
human-readable description string returned in the response body. It is never
executed. The actual deletion goes through `storage.delete_by_tag(request.tag)`,
which is parameterized. The rule fired on the word "Delete" next to an f-string.

The `wildcard-cors` flag at `startup_orchestrator.py:458` is the OAuth discovery
sub-app, and it is correct code: `allow_origins` falls back to `["*"]` only when
no origins are configured, and in that branch `allow_credentials` is set to
`False`. A credentialed wildcard is what browsers reject and what actually leaks;
this is the non-credentialed kind, on public metadata endpoints. The 30 Gitleaks
hits are all in `tests/` and `docs/` — most pointedly a fixture JWT inside
`test_hooks_config_secrets_check.sh`, which is the repository's own test *of its
secret scanner*. The one Trivy critical, `CVE-2026-59890` in setuptools 81.0.0,
sits in `uv.lock` as a build-time dependency, not in the shipped runtime.

## Patterns observed

There is a defense worth crediting that the scanner will never reward. The MCP
Python SDK ships DNS-rebinding protection (Host-header validation) but defaults
it **off** for backward compatibility, and this project does not pass a
`security_settings` object when it constructs the session manager. On its own
that reads like a gap. It is inert here, because `_assert_bind_is_authenticated`
makes authentication mandatory on any non-loopback bind, and a rebinding browser
page cannot forge the API key or bearer token that the auth gate demands. The
missing Host check would matter only in a configuration the server refuses to
start in. That is defense-in-depth hardening, not a vulnerability — the same
distinction this series drew on tracecat's RLS mode and viseron's argue-down.

The broader pattern is that a security program shows in the diffs, not the
document. This `SECURITY.md` has an SLA, a CVSS-shaped severity taxonomy, and a
coordinated-disclosure policy, and Private Vulnerability Reporting is enabled.
But the thing that actually tells you the project is serious is that it has eight
published advisories, four of them shipped the same day I looked, each crediting
an external reporter, each fixed by deleting a duplicated code path rather than
bolting on a check. A scanner grades the code as it is. It cannot grade the rate
at which a maintainer closes the gap between what the code does and what the
policy promises, and that rate is the real signal.

## Notes on the tool

- The parameterized-SQL identifier false positive is now the single most
  frequent finding class in the entire series. It is long past time AI PatchLab
  shipped a curation pass that recognizes a bound-parameter query with an
  f-string'd identifier and drops it, or at minimum re-ranks it below the fold.
  Backlog item.
- The `tainted-sql-string` hits on `manage.py` are a stronger case still: the
  f-string is assigned to a variable that is returned as a description, never
  passed to a cursor. Dataflow that checks whether the string reaches an execute
  call would clear all three.
- Semgrep spent nine rule-timeouts on vendored assets under `site/demo/`
  (a bundled `sqlite3.mjs`, a tokenizer JSON) and three on `request-with-http`
  over large first-party files. The demo subtree is regenerable vendor code and
  should be in the default ignore set, the way `--ignore-samples` handles
  sample dirs. Backlog item.
- The tools have no way to represent "the real bug is the absence of a check
  that exists in the sibling handler." Four times over on this repo, that was
  the entire security story. This is the recurring limit the series documents,
  not a defect to fix in a rule.

## Disclosure timeline

- 2026-09-05 — scan run against `07971a62a2ba`
- 2026-09-05 — curation complete; zero findings survived; nothing to disclose
- 2026-09-05 — public post (this page)

Nothing was filed upstream. The target is a strict-norm repository with an
active security-advisory program, and no finding survived curation. This is a
clean-scan write-up, one of an honest and established format in this series.

## Reproduce

```bash
git clone https://github.com/doobidoo/mcp-memory-service /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/doobidoo-mcp-memory-service --min-severity medium
```

The four fixed advisories are public at
[github.com/doobidoo/mcp-memory-service/security/advisories](https://github.com/doobidoo/mcp-memory-service/security/advisories);
compare them against the finding list above to see the gap for yourself.
