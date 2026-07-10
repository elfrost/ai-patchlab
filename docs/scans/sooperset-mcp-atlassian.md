---
layout: default
title: "sooperset/mcp-atlassian: security scan"
date: 2026-07-10
---

# sooperset/mcp-atlassian - security scan

**Repository:** [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)
**Commit scanned:** `4067d1db4097755cc6add87f95fe3f0746c98c0b`
**Scan date:** 2026-07-10
**Disclosure status:** public — post-only (strict-norm: SECURITY.md requests private reporting; the criticals are public dep CVEs)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 26 |
| Medium | 43 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 71 (0 novel code findings; the two criticals are reachable-in-OAuth-mode dependency CVEs)

mcp-atlassian is the popular (5.5k-star) MCP server for Jira and Confluence,
supporting API tokens, PATs, and OAuth 2.0 across Cloud and Server/Data Center.
It's credential-dense by nature, so the two questions worth asking are the ones
a scanner can't answer directly: **does it protect the tokens on the wire, and
is the OAuth path safe?** The TLS handling turns out to be correct-by-default;
the residual is a pair of public dependency criticals that bite only in the
optional multi-user OAuth mode.

## Top findings

### 1. TLS verification is secure-by-default (the semgrep-blind check clears)

- **File:** `src/mcp_atlassian/utils/ssl.py`, `src/mcp_atlassian/jira/config.py:104`
- **Tool:** manual completeness sweep (semgrep did not flag it)
- **Confidence:** high — by-design, secure
- **Why it matters:** The codebase contains a `verify=False` / `ssl.CERT_NONE`
  path (an SSLAdapter in `ssl.py`). On a server that forwards API tokens and PATs
  to Atlassian, a *default* of "don't verify certs" would expose those
  credentials to MITM. That's exactly the semgrep-blind thing to check by hand.
- **Why it's not a finding:** `ssl_verify` defaults to `True`
  (`jira/config.py:104`: `ssl_verify: bool = True`), and the `CERT_NONE` path is
  reached only behind `if not ssl_verify:` — i.e. an explicit `JIRA_SSL_VERIFY=false`
  / `CONFLUENCE_SSL_VERIFY=false` opt-in, documented for self-hosted Server/Data
  Center instances with self-signed certificates. That's the standard enterprise
  pattern (opt-out for a specific self-signed deployment), not an insecure
  default.

### 2. The two criticals are public dep CVEs, reachable only in OAuth-server mode

- **File:** `uv.lock` (`authlib` 1.6.8, `fastmcp` 2.14.5)
- **Tool:** trivy
- **Confidence:** reachable in the optional multi-user OAuth deployment; version-match
- **Why it matters:** `authlib` 1.6.8 carries a **JWK-header-injection auth
  bypass** (CVE-2026-27962, critical) plus two highs; `fastmcp` 2.14.5 carries an
  **authenticated SSRF** (CVE-2026-32871, critical). On an OAuth MCP server these
  are the scary shapes — bypass token verification, or pivot a server-side
  request.
- **The reachability nuance:** `authlib` has **zero direct imports** in
  mcp-atlassian — it arrives transitively, and its JWK-verification bypass is on
  the path only when the operator enables the multi-user **OAuth-server** mode
  (where FastMCP verifies inbound tokens). The default single-user deployment
  (API token / PAT) never verifies a JWK, so it doesn't reach the authlib bug.
  `fastmcp` is the framework and always present; its SSRF is likewise gated on
  the authenticated proxy path. So: real and reachable *in the OAuth deployment*,
  inert in the common single-user one.
- **Recommendation:** Bump `authlib` → 1.6.9 (a **one-patch-version** fix that
  clears the critical and both highs) and `fastmcp` → 3.2.0 (a **major** bump,
  more involved). And wire Dependabot — there's no `.github/dependabot.yml`, so a
  5.5k-star OAuth server's auth dependencies drift unattended.

### 3. Everything else is lint, docs, and test fixtures

- **Tool:** semgrep + gitleaks
- **Confidence:** high — FP / hardening
- **Why it matters / why it doesn't:** 18 of the 23 semgrep hits are
  `github-actions-mutable-action-tag` (SHA-pinning hardening). The `jinja2` hits
  are in `scripts/generate_tool_docs.py` (a docs generator, not runtime), and the
  `non-literal-import` is a plugin loader. The one `python-logger-credential-disclosure`
  is a `logger.debug` about OAuth token *resolution* (debug-level, and it logs the
  resolution context, not a raw secret) — worth keeping tokens out of debug logs,
  but not a leak. All 8 gitleaks hits are `docs/troubleshooting.mdx` examples and
  `tests/` fixtures.

## Patterns observed

**The credential-server questions are the ones the scanner skips.** semgrep
produced 23 findings and not one of them was the thing that actually mattered for
a token-forwarding server — the TLS-verification default. That had to be traced
by hand (`ssl.py` → `configure_ssl_verification` → the `ssl_verify` config
default), the same MCP completeness-sweep discipline the zotero-mcp and codex-lb
scans used. The good news is it came back clean: verification on by default,
`CERT_NONE` only for an explicit self-signed opt-in.

**"Reachable" needs a deployment qualifier for a dual-mode server.** The authlib
and fastmcp criticals are genuinely reachable — but only in the multi-user OAuth
deployment, not the single-user API-token mode most users run. This is the
transport/deployment-reachability nuance the tradingview-mcp and OpenKB scans
raised, applied to auth: the same lockfile is "two reachable criticals" for an
OAuth operator and "two inert transitive CVEs" for a PAT user. The honest report
states which.

**Strict-norm, so post-only — and the criticals are public CVEs anyway.**
mcp-atlassian ships a real SECURITY.md that asks reporters to use GitHub's
private vulnerability reporting. Two things follow: no public "review" issue
(policy), and no private advisory either — these are upstream `authlib`/`fastmcp`
CVEs that any scanner surfaces and Dependabot would auto-PR, so a coordinated
private disclosure adds nothing. The proportionate action is to document the
reachable-in-OAuth-mode criticals and the missing Dependabot here, and credit the
secure TLS default.

## Notes on the tool

- **`verify=False` / `CERT_NONE` deserves a config-default trace, not just a
  flag.** The scanner didn't surface the SSL path at all; when it does, the
  useful output isn't "verify=False exists" but "is it default or opt-in?" —
  which requires following the `ssl_verify` config to its default. Pairs with the
  ssl-adapter pattern being invisible to the rule here.
- **Dependency reachability is deployment-mode-dependent for dual-mode servers.**
  `authlib`/`fastmcp` criticals matter in OAuth-server mode and not in
  single-user PAT mode. Tagging a dep CVE with "reachable under config X" would
  right-size these — the same transport-reachability backlog item from
  tradingview-mcp.
- **`github-actions-mutable-action-tag` (18) dominates the semgrep count** on
  yet another scan. A repo-level "actions are SHA-pinned?" summary line would
  compress this recurring hardening class instead of 18 separate highs.

## Disclosure timeline

- 2026-07-10 — scan run
- 2026-07-10 — public post (this page); post-only, no upstream issue filed
  (strict-norm private-reporting policy; criticals are public dep CVEs)

## Reproduce

```bash
git clone https://github.com/sooperset/mcp-atlassian /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/sooperset-mcp-atlassian \
  --min-severity medium --ignore-samples
```
