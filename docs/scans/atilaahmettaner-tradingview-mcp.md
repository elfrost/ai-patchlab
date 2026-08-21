---
layout: default
title: "atilaahmettaner/tradingview-mcp: security scan"
description: "Security scan of atilaahmettaner/tradingview-mcp: 28 findings, 0 real — 13th clean scan: a market-data MCP server (~30 tools for Claude/Cursor)"
date: 2026-07-07
---

# atilaahmettaner/tradingview-mcp - security scan

**Repository:** [atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp)
**Commit scanned:** `36ca7ff648149682a4eb65798821718e5bdfbfea`
**Scan date:** 2026-07-07
**Disclosure status:** public — post-only (strict-norm: commercial hosted tier; no upstream issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 11 |
| Medium | 17 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 28 (0 real after curation)

tradingview-mcp is an MCP server exposing ~30 market-data / technical-analysis
tools (stocks, crypto, forex) to MCP clients like Claude and Cursor, with a paid
hosted tier at cryptosieve.com. For an MCP server the sharpest question is the
one static rules don't ask directly: **can a tool argument steer a server-side
request somewhere it shouldn't go?** Here the answer is no — the outbound
fetches are fixed-host, and the design deliberately holds no credentials. This
is the **13th clean scan**; the only residual is a dependency refresh.

## Top findings

### 1. The tool-input → outbound-request path is not SSRF (fixed host)

- **Files:** `core/services/backtest_service.py:63`, `bitcoin_market_service.py:36`, `extended_hours_service.py:142`
- **Tool:** semgrep (`dynamic-urllib-use-detected`) + MCP completeness sweep
- **Confidence:** high — not exploitable
- **Why it matters:** An MCP server that fetches URLs from tool inputs is the
  classic SSRF shape — a prompt-injected agent points a "symbol" at
  `http://169.254.169.254/…` and the server fetches it. That was a real finding
  on the zotero-mcp scan, so it's the first thing to check here.
- **Why it's not a finding:** The host is never attacker-controlled. The Yahoo
  and CoinGecko endpoints are hardcoded constants
  (`_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"`), and where a tool
  input appears it only fills a `{symbol}` slot in a fixed-host path:
  `url = f"{_YF_BASE}/{symbol}?interval={interval}&range={period}"`. Because
  `symbol` lands *after* the authority, it can influence the path/query under the
  trusted finance host but cannot redirect to a new host. All three fetches set
  explicit timeouts. The residual is input-validation hygiene (a malformed
  `symbol` yields a bad request, not a cross-host fetch), not SSRF.

### 2. No credential surface — by design

- **Tool:** gitleaks (clean) + README review
- **Confidence:** high — positive design note
- **Why it matters:** Many finance/MCP integrations hold a brokerage or vendor
  API key, which becomes the thing to protect. This server explicitly doesn't:
  it fetches from public endpoints, requires no TradingView account or API key,
  and drives no browser session. gitleaks found nothing, and there is no token
  to leak because the architecture removed the token.

### 3. The real residual: a transport-gated dependency refresh

- **File:** `uv.lock` (no `.github/dependabot.yml`)
- **Tool:** trivy
- **Confidence:** version-match, reachability split
- **Why it matters:** 17 dep advisories, and the reachability splits on the MCP
  transport. `mcp` 1.12.4 (CVE-2025-66416) is the SDK itself — reachable in any
  mode. `starlette` (5 CVEs) and `python-multipart` (7 CVEs) sit in the **HTTP**
  transport path — i.e. the hosted / streamable-HTTP deployment, not the default
  stdio mode a local Claude/Cursor client uses. `urllib3` (4 CVEs) is transitive
  behind the fixed-host fetches. None is a code-level flaw, but the hosted tier
  (which runs HTTP) is exactly where `starlette`/`python-multipart` currency
  matters.
- **Recommendation:** Bump `mcp`, `starlette`, and `python-multipart`, and wire
  Dependabot so the hosted transport stays current. Mechanical, not a
  disclosure.

## Patterns observed

**The MCP SSRF check is worth running every time, even when it comes back
negative.** The completeness-sweep discipline (walk each tool input to its sink)
is what distinguishes zotero-mcp — where a tool input genuinely reached an
attacker-chosen host — from this one, where the host is a hardcoded finance API
and the input only fills a symbol slot. Same `dynamic-urllib` rule hit, opposite
verdict, and the difference is entirely "is the authority attacker-controlled?"

**Removing the credential is the strongest credential control.** The most
notable security decision here is architectural: by fetching only public data
and holding no TradingView session or key, the server deletes the whole
credential-handling surface that the linkedin-mcp and google-workspace-mcp scans
spent their time on. The README even leads with it ("does it need — or risk —
your TradingView account? No").

**Post-only, because strict-norm and nothing cleared the bar.** There's a
commercial hosted tier, so grouped issues are off the table by policy — but it's
moot: there's no real, reachable, undefended item. The dependency tail is public
CVEs with mechanical fixes, and the hosted operator is best placed to schedule
them.

## Notes on the tool

- **`dynamic-urllib-use-detected` should note whether the host is a literal.**
  All three hits interpolate a tool input into a URL whose scheme+authority are
  constants. An SSRF rule that distinguishes "attacker controls the host" from
  "attacker controls a path/query segment under a fixed host" would have marked
  these low instead of surfacing them alongside real sinks.
- **Dependency reachability is transport-dependent for MCP servers.** trivy
  can't tell that `starlette`/`python-multipart` only matter in the HTTP
  transport and are inert under stdio. An MCP-aware pass could tag deps by which
  transport reaches them.
- **`github-actions-mutable-action-tag` (6) and docker-compose hardening**
  (`no-new-privileges`, read-only fs) are reasonable supply-chain / container
  hardening, not vulnerabilities — consistent with recent scans.

## Disclosure timeline

- 2026-07-07 — scan run
- 2026-07-07 — public post (this page); post-only, no upstream issue filed

This is a post-only clean-scan write-up. The tool-input fetches are fixed-host
(not SSRF), the design holds no credentials, secrets are clean, and the
dependency tail is public CVEs with mechanical fixes — mostly transport-gated to
the hosted HTTP mode. On a strict-norm project with a commercial tier, the
proportionate action is to document.

## Reproduce

```bash
git clone https://github.com/atilaahmettaner/tradingview-mcp /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/atilaahmettaner-tradingview-mcp \
  --min-severity medium --ignore-samples
```
