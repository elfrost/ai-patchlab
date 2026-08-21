---
layout: default
title: "Soju06/codex-lb: security scan"
description: "Security scan of Soju06/codex-lb: 76 findings, 0 real — 11th clean scan, and the most credential-dense target yet: a ChatGPT/Codex-account load balancer +"
date: 2026-07-01
---

# Soju06/codex-lb - security scan

**Repository:** [Soju06/codex-lb](https://github.com/Soju06/codex-lb)
**Commit scanned:** `f212300dbe60492accdb09115a6a64ba87646c86`
**Scan date:** 2026-07-01
**Disclosure status:** public — post-only (clean scan; no upstream issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 47 |
| Medium | 29 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 76 (0 real after curation)

codex-lb is a load balancer and proxy for ChatGPT/Codex accounts: pool multiple
accounts, store their OAuth tokens, expose an OpenAI-compatible endpoint, and
manage it all from a web dashboard with usage tracking. That makes it the most
credential-dense target in the series so far — the whole product is "hold other
people's LLM account tokens and broker requests through them."

This is the **11th clean scan**, and the most instructive kind: the finding
that would actually matter for a credential proxy is one a static scanner never
raises, and the maintainer had already engineered it correctly. Semgrep's 47
"high" findings are, on inspection, database migrations and Markdown.

## Top findings

### 1. The finding that matters — localhost auth-bypass — is correctly defended

- **File:** `app/core/request_locality.py`, `app/core/auth/dashboard_mode.py`
- **Tool:** manual project-class review (semgrep does not flag this)
- **Confidence:** high — by-design, correct
- **Why it matters:** codex-lb's dashboard **bypasses the bootstrap-token/auth
  flow for "local" access** (documented: "Local access (localhost) bypasses
  bootstrap entirely — no token needed"). The classic way this goes wrong is
  trusting a spoofable forwarding header: if the app reads
  `X-Forwarded-For: 127.0.0.1`, any remote attacker behind (or pretending to be
  behind) a proxy authenticates as localhost and skips the dashboard password.
- **Why it's not a finding:** `resolve_connection_client_ip` only consults
  forwarding headers when `trust_proxy_headers` is enabled **and the socket peer
  is inside a configured `trusted_proxy_networks` CIDR set**
  (`_is_trusted_proxy_source`). Otherwise it ignores `X-Forwarded-For` entirely
  and uses the real TCP peer. The XFF chain is walked right-to-left, every hop is
  validated as a real IP (invalid chains raise), and `dashboard_mode` strips
  `x-forwarded-*` / `forwarded` from the sensitive header set. There's an
  explicit `DashboardAuthMode` enum (STANDARD / TRUSTED_HEADER / DISABLED) and a
  dedicated `test_firewall_ip_resolution.py`. This is the CIDR-gated
  trusted-proxy model most projects get wrong, done right.

### 2. The 47 "high" findings are database migrations and Markdown

- **Files:** `app/db/alembic/versions/*.py`, `app/db/migrate.py`, plus `README.md` / `openspec/**/*.md`
- **Tool:** semgrep (`avoid-sqlalchemy-text`, `sqlalchemy-execute-raw-query`, `formatted-sql-query`)
- **Confidence:** high — FP
- **Why it matters / why it doesn't:** ~30 of the highs are `sqlalchemy.text()` /
  raw-SQL rules firing on **Alembic migration scripts** — developer-authored DDL
  that runs at deploy, with no user input in the loop. Several more are `md-*`
  rules firing on fenced code blocks in `README.md` and the `openspec/` specs.
  Neither is application code handling a request.

### 3. The one live-code SQL area is parameterized

- **File:** `app/modules/usage/repository.py:198,251,352,418,420`
- **Tool:** semgrep (`sqlalchemy-execute-raw-query`)
- **Confidence:** high — safe
- **Why it matters:** This is the usage/analytics repository — the only flagged
  SQL that runs on real requests.
- **Why it's not a finding:** Every call is `conn.execute(sql, params)` with the
  values bound as parameters (`conn.execute(latest_sql, [account_id, *scope_params, ...])`),
  and the SQL bodies are static templates with `?` placeholders. Semgrep flags the
  multi-line SQL string; the actual execution is parameterized.

### 4. Credential logging and crypto are careful / protocol-mandated

- **Files:** `app/core/clients/oauth.py`, `app/core/auth/refresh.py`, `app/core/clients/proxy.py:1492`
- **Tool:** semgrep (`python-logger-credential-disclosure`, `insecure-hash-algorithm-sha1`)
- **Confidence:** high — FP
- **Why it matters / why it doesn't:** The ~20 `logger-credential-disclosure`
  hits land on OAuth/token-refresh/proxy code, but every one logs a
  **`request_id` and status code**, never the token
  (`logger.warning("OAuth token request failed request_id=%s status=%s", ...)`) —
  that's correct correlation-ID discipline, not a leak. The lone `sha1` is the
  **RFC 6455 WebSocket handshake** (`base64(sha1(sec_key + WS_KEY))`) computing
  `Sec-WebSocket-Accept` — SHA-1 is mandated by the protocol here; "upgrading" it
  would break the handshake. Same shape as the SHA-1-for-Chromium-interop false
  positive from the linkedin-mcp-server scan.

## Patterns observed

**For a credential proxy, the real risk surface is the one semgrep can't see.**
The whole security question for codex-lb is "can someone who isn't you reach the
dashboard or the pooled tokens?" — and that reduces to how it decides a request
is "local," how it stores account tokens, and whether the proxy is an open
relay. None of those are AST-pattern findings; a rule engine has nothing to say
about them. This is the same lesson the zotero-mcp completeness sweep taught:
for a given project *class*, you have to manually walk the class-specific
surface, because the scanner's high-severity list is orthogonal to it. Here the
walk turned up a maintainer who built a dedicated `request_locality` module, a
CIDR-gated trusted-proxy model, header sanitization, and a firewall IP-resolution
test — the exact controls the threat needs.

**The count is migrations again.** 47 highs sounds alarming on a token broker;
~30 are Alembic DDL and the rest are Markdown and parameterized analytics SQL.
Auto-flagging `alembic/versions/**` (developer-authored, deploy-time, no request
input) as candidate-FP would have collapsed the high bucket to near-zero — the
same "migrations aren't request paths" point that keeps recurring.

**Spec-driven engineering shows in the security posture.** codex-lb is built
with an `openspec/` spec directory, `DECISIONS.md`, and `AGENTS.md`/`CLAUDE.md`
— and the security-relevant behavior (forwarded-header sanitization, trusted-
proxy CIDRs, auth modes) is each backed by a written spec. The discipline that
usually produces good docs here also produced the correct locality handling.
Dashboard auth is password + optional TOTP, tokens are encrypted at rest, and
dependencies are current under Renovate (trivy found nothing).

## Notes on the tool

- **`alembic/versions/**` should be candidate-FP.** Roughly 30 of the 47 highs
  were `sqlalchemy.text` / raw-SQL rules on migration scripts. Migrations are
  developer-authored DDL with no request input; treating them like `tests/` for
  candidate-FP flagging would have removed the bulk of this report's noise.
  Highest-value backlog item from this scan.
- **`insecure-hash-algorithm-sha1` needs a protocol-context exception.** The hit
  was the mandatory RFC 6455 WebSocket `Sec-WebSocket-Accept` computation.
  Combined with the linkedin-mcp SHA-1-for-Chromium case, there's a clear class:
  SHA-1 inside a protocol/interop constant is not a crypto weakness. This is the
  second backlog vote for a "mandated-interop SHA-1" allowlist.
- **`python-logger-credential-disclosure` went ~20-for-20 FP.** Every hit logged
  a request-id + status. The rule keeps flagging correlation-ID logging in
  credential-handling modules; a check for whether the logged *argument* is the
  secret (vs. an id/status) would cut this recurring class.
- **A supply-chain cooldown nit, not a vuln.** semgrep flagged the Dependabot/
  Renovate config for lacking a cooldown / minimum-release-age. Adding one (wait
  N days before auto-adopting a freshly published version) is reasonable
  supply-chain hardening after the 2026 LiteLLM PyPI incident — worth a mention,
  not a disclosure.

## Disclosure timeline

- 2026-07-01 — scan run
- 2026-07-01 — public post (this page); post-only, no upstream issue filed

This is a post-only clean-scan write-up. The credential-proxy risk that matters
(localhost auth-bypass via spoofed locality) is correctly engineered behind a
trusted-proxy CIDR model, the SQL that runs on requests is parameterized, the
credential logging is correlation-id-only, and the flagged SHA-1 is
protocol-mandated. Nothing cleared the quality gate.

## Reproduce

```bash
git clone https://github.com/Soju06/codex-lb /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/soju06-codex-lb \
  --min-severity medium --ignore-samples
```
