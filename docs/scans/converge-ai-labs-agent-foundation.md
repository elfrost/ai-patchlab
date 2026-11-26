---
layout: default
title: "converge-ai-labs/agent-foundation: security scan"
description: "Security scan of converge-ai-labs/agent-foundation (a13n): 441 findings at medium+, 0 real after curation. A multi-tenant agent runtime whose authorization held across a 386-route sweep; two hardening notes on outbound-policy and loopback consistency. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-26
---

# converge-ai-labs/agent-foundation — security scan

**Repository:** [converge-ai-labs/agent-foundation](https://github.com/converge-ai-labs/agent-foundation)
**Commit scanned:** `c4cf89f6` (`main`)
**Scan date:** 2026-11-26
**Disclosure status:** post-only. Nothing survived curation as a vulnerability, so nothing was filed upstream. The two hardening notes below are consistency gaps between a defence and its siblings, each with a low ceiling. Neither is an exploitable path in a default deployment.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 3 |
| High | 109 |
| Medium | 326 |
| Low | 0 |
| Info | 3 |

**Total findings:** 441 at `--min-severity medium`, run with `--ignore-samples`. After curation, 0 are real. The 3 info rows are coverage meta findings.

Agent Foundation ("a13n") is a self-hosted runtime for AI agents (1.6k★, Apache-2.0, backed by
Converge AI). It ships four pieces:

- **Service:** a multi-user server with an HTTP API, a web Console, PostgreSQL and Redis. Workers
  lease runs, execute them, and checkpoint them to object storage so an interrupted run can resume.
- **Harness:** the agent loop, embeddable in a Python app.
- **Harness UI:** a local web app for a single developer.
- **`a13n-envd`:** a Rust daemon that runs inside each agent sandbox (Docker, Kubernetes, or hosted
  sandbox providers).

The repository holds about 666,000 lines of Python in 2,556 files (914 of them tests), 1,453
TypeScript files and 125 Rust files. It is one of the most active targets in the series: more than
300 pull requests merged and 163 issues closed in the 60 days before the scan, and three component
releases shipped on the scan day. It is strict-norm: `SECURITY.md` names a private email address and
asks that vulnerability details stay out of public issues and pull requests.

**Scope of this write-up.** Every tool finding was checked at its call site or by file family. The
three trust boundaries were then read by hand:

1. **Service authorization.** Every route decorator was parsed: 386 routes, tabulated against their
   auth dependencies. The outliers, the OIDC flow, API-key scoping, first-run bootstrap and
   workspace scoping were read end to end.
2. **Harness UI.** The local server's access boundary, its WebSocket and OAuth exceptions, host file
   access, and the MCP Apps sandbox.
3. **`a13n-envd` and outbound requests.** The daemon's authentication and credential handling, plus
   every server-side fetch of a URL that a workspace member or the model can choose.

The 219 Harness UI `/api` handlers were covered through the middleware's prefix match, not read
one by one. Third-party App plugin handlers live outside this repository and were not reviewed.
Read the result as "the tools' findings are accounted for, and the boundaries named above hold as
documented", not as an audit of every handler.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | A shipped lockfile was not covered by the dependency scan |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep reported 33 errors.

- **Three rule timeouts.** Two `request-with-http` runs (on the Harness UI `app.py`, 5,047 lines,
  and the browser `cdp.py`) and one `nan-injection` run (on `webui.py`) did not complete.
  `webui.py` is the Harness UI access boundary, and it was read by hand.
- **Two files that never parsed.** Semgrep rejected
  `packages/a13n-harness-ui/a13n_harness_ui/subagent_operator.py` (2,904 lines) and one 155-line
  Console component outright. The Python file parses cleanly on CPython 3.13, the project's pinned
  version, so this is a Semgrep parser limit, not broken code. No rule ran on either file, and
  neither was read by hand.
- **Partial parsing.** The remaining errors are partial parses of workflow YAML and test files.

The `dependency-scan` row is `partial` because pip-audit read the `pyproject.toml` floors while
the project installs from `uv.lock`. Trivy read the root `uv.lock` and found **zero** advisories.
Every Python CVE Trivy did report came from the stale lockfiles under `examples/`, which
`--ignore-samples` set aside (379 rows).

## Top findings

There is no vulnerability to lead with. Two hardening notes:

### 1. The media-URL tool builds its own outbound policy and skips the operator's HTTPS requirement

- **Files:** `packages/a13n-harness/a13n_harness/toolsets/media_url.py:133`, `packages/a13n-harness/a13n_harness/_media_urls.py:47`
- **Tool:** manual review
- **Confidence:** high on the code, low on impact
- **Why it matters:** most outbound fetches go through the operator's endpoint policy, built with
  `runtime.endpoint_policy.for_run(...)`. That covers web fetch, MCP servers, OAuth, provider tests
  and model base URLs. The policy defaults to `providers.require_https = true` and an empty
  plain-HTTP allowlist (`settings.py:705`). The media tool, which lets the model read an image,
  audio or video URL, instead builds `EndpointPolicy(configuration=...)` directly, and that
  object's default is `require_https=False`. The model can therefore make plain-HTTP GET requests
  from the worker that every sibling path would refuse.
- **The ceiling is low:**
  - The body comes back only for media content types, or when the content type is missing or
    `application/octet-stream`.
  - The status code always comes back, so the model can probe internal plain-HTTP hosts and
    ports.
  - The project documents that the Service "does not classify private addresses or pin DNS
    results" and leaves destination restrictions to the deployment
    (`deploy/docker/compose/README.md:60`). So `https://` to an internal host was never blocked
    on any path. Only the HTTPS requirement differs here.
- **Recommendation:** build the media policy from `runtime.endpoint_policy.for_run(configuration)`
  like its siblings, so the operator's `require_https` and `http_origins` apply. Separately,
  `runs/web.py:7` and `:180` say that resolved addresses "are checked by the host transport when it
  connects, so a DNS answer cannot bypass it". The transport in `infra/outbound.py` documents the
  opposite ("without DNS prechecks or address pinning"), and the code matches that docstring. One of
  the two should change, and the cheaper one is the comment.

### 2. `webui.allowed_origins: ["*"]` turns off the Harness UI's DNS-rebinding check, and the docs say it does not

- **Files:** `packages/a13n-harness-ui/a13n_harness_ui/webui.py:521`, `docs/a13n-harness-ui/running-webui.md:32`
- **Tool:** manual review
- **Confidence:** high on the mechanism, low on real-world reach (two explicit opt-ins)
- **Why it matters:** the Harness UI guards every `/api` route with one middleware in three steps:
  1. a `Host` allowlist (the bind address, `localhost`, `127.0.0.1`, `::1`);
  2. an `Origin` check that requires Origin to equal the request's scheme plus Host;
  3. a bearer key compared in constant time.

  Setting `allowed_origins` to `"*"` skips step 1. Step 2 then compares the attacker's Origin with
  the attacker's own Host, so it passes on a rebound page. With the API key in place nothing is
  reachable, because the rebound page cannot read the key from the real origin. Only
  `--dangerous-skip-permissions` together with `"*"` leaves a web page with owner access. The docs
  say `"*"` does not enable "cross-origin API access". The spec calls the same-origin checks the
  boundary in bypass mode.
- **Recommendation:** refuse `"*"` together with the permission bypass at startup, or keep the
  `Host` check whenever no key is configured. Then correct the sentence in the docs.

## Why the rest were dismissed

All 438 tool findings are accounted for below, plus the two hand-found notes (recorded as the
`by-design` hardening rows, so the corpus counts them). The scanner itself set aside 379 rows
under the sample-path patterns and 26 below the medium floor.

| Reason | Findings |
| --- | ---: |
| `ignore-pattern` (scanner, `examples/` lockfiles and samples) | 379 |
| `by-design` (incl. the 2 hardening notes) | 300 |
| `dependency-currency` | 39 |
| `sql-identifier-fp` | 37 |
| `test-or-fixture-path` | 32 |
| `below-min-severity` (scanner) | 26 |
| `not-reachable` | 16 |
| `domain-noun-collision` | 8 |
| `mitigated-in-app` | 3 |
| `placeholder-secret` | 2 |
| `credited-defense` | 2 |
| `product-surface` | 1 |

The largest family is `github-actions-mutable-action-tag` (252 rows): workflow actions pinned by
tag, not commit SHA. That is supply-chain hardening, not a product defect.

The three criticals all died at the reachability gate:

- **Next.js (two RCE advisories).** Next is used only by the documentation site, which builds with
  `output: "export"` and `images.unoptimized`. No Next server, Image Optimization endpoint or
  `use cache` runtime ever ships.
- **Rust `zip` parser-differential advisory.** It applies to `a13n-envd`'s self-update. That path
  checks the archive's SHA-256 against the release `SHA256SUMS` before parsing it, then accepts
  exactly two allowlisted regular entries with size caps.

The 37 SQL rows are Alembic migrations and the migration runner. They format hardcoded table names
and integer settings, never request values.

## Patterns observed

**Authorization is per route, and a sweep can enumerate it.** Every Service route declares its
caller as a typed dependency (`Actor`, `Credential`, `WorkspaceId`), so parsing the decorators
gives a complete route-by-control table. Of 386 routes, 16 have no auth dependency, and each of
those is public by intent, authenticates by its own token, or is first-run setup.

Behind the table sits a second layer:

- resources load through `find_row()`, which filters on `workspace_id`;
- admin actions re-read and lock the caller's grants inside the transaction that changes them;
- about 144 composite foreign keys such as `(workspace_id, provider_id)` make a cross-workspace
  reference fail at the database even if a handler forgot to scope.

The same handler would need to get it wrong at two layers.

**OIDC done the long way.** The flow uses `state`, `nonce` and PKCE S256. The flow key is bound to
a browser cookie and consumed once with `GETDEL`. The issuer is checked at discovery and again at
the callback, the token must name exactly this client, the algorithm comes from an allowlist, and
exactly one signing key must match. Identities are keyed on issuer and subject only. The OIDC
email is display data, never used to link an account, so a second identity provider asserting the
same address cannot take the account over. Back-channel
logout rejects tokens that carry a `nonce` and keeps a replay window.

**A loopback app that checks `Host`.** Earlier loopback targets in this series, such as
[claude-code-local](nicedreamzapp-claude-code-local.html), served `127.0.0.1` with neither a
`Host` nor an `Origin` check. The Harness UI checks both. It
uses a bearer key rather than cookies, so CSRF has nothing to ride on. Its exceptions (shared
threads, signed file-transfer links, device pairing, the OAuth callback) each carry their own
token or state binding. The MCP Apps sandbox runs untrusted app HTML on a separate,
credential-less origin and relays messages only after checking both the exact window and the
origin.

**The sandbox daemon assumes the sandbox is hostile.** `a13n-envd` has no unauthenticated
endpoint. It rejects query-string credentials, cookies and compressed requests, and refuses
plaintext outside an explicit loopback or private-link scope. Its own egress classifier blocks
private, link-local and metadata ranges after DNS resolution. That makes the hardening note
above stand out: the strictest egress check in the project lives in the Rust daemon, while the
Python Service deliberately leaves egress to the deployment and says so.

## Notes on the tool

- **Semgrep rejected a valid 2,904-line file.** `subagent_operator.py` parses on CPython 3.13
  but not in Semgrep, so the report names it as unexamined, and so does this post. The
  partial-coverage finding still suggests a higher `--timeout`, which does not help a parse
  failure. Backlog: split the recommendation by error type.
- **`--ignore-samples` earned its keep.** Five `examples/*/uv.lock` files pinned old releases of
  aiohttp, PyJWT, Pillow and FastMCP and produced 379 rows. Without the flag they would have
  outnumbered every other family combined, for code no deployment installs. The root lockfile was
  clean.
- **No rule can see a sibling that skips the policy.** The media-tool note is "this call builds
  its own policy object while every other call uses the shared one". That is a fact about
  difference, not presence. Finding it took listing every outbound path and comparing how each
  builds its policy. Backlog: a curation checklist item that lists constructors of a project's own
  policy or guard class and flags call sites that bypass the shared factory.
- **Two Django rules fired in a project with no Django.** `avoid-query-set-extra` matched anyio's
  `listener.extra(...)`, and `raw-html-format` matched a dev OAuth fixture.

## Disclosure timeline

- 2026-11-26 — scan run at `c4cf89f6` (`main`)
- 2026-11-26 — curated: no finding met the bar for a private report, so nothing was filed upstream
- 2026-11-26 — this page published

## Reproduce

```bash
git clone https://github.com/converge-ai-labs/agent-foundation /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/converge-ai-labs-agent-foundation --min-severity medium --ignore-samples
```
