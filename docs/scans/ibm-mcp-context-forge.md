---
layout: default
title: "IBM/mcp-context-forge: security scan"
description: "Security scan of IBM/mcp-context-forge: 946 findings, 0 real — 18th clean scan, and the richest attack surface in the series: an AI gateway / registry /"
date: 2026-07-17
---

# IBM/mcp-context-forge - security scan

**Repository:** [IBM/mcp-context-forge](https://github.com/IBM/mcp-context-forge)
**Commit scanned:** `50602d6dc1c217ed60f7ac070f2a5210f53181a2`
**Version:** 1.0.5 (beta)
**Scan date:** 2026-07-17
**Disclosure status:** public — post-only (strict-norm: IBM PSIRT private-reporting policy; 0 real findings)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 709 |
| Medium | 237 |
| Low | 0 |
| Info | 0 |

**Total findings:** 946 (0 real after curation)

This is the **18th clean scan** in the series, and the one with the richest
attack surface so far. ContextForge (aka MCP Gateway) is an **AI gateway,
registry, and reverse proxy** that sits in front of any MCP, A2A, or REST/gRPC
backend — it authenticates callers, forwards credentials to upstream servers,
proxies tool invocations out to registered endpoints, discovers JWKS keys, and
runs a plugin system. That is the credential-proxy class (last seen in
[soju06/codex-lb](soju06-codex-lb.html)) scaled up to a full multi-protocol
gateway. Every finding that *would* be real on a project like this — SSRF from
the proxy egress, an auth-bypass in the token path — turns out to be defended,
by design, secure-by-default.

## The finding that matters on a gateway: SSRF egress — and it's defended

A gateway's whole job is to take a caller's request and fetch *something else*
on their behalf. So the finding class that matters is server-side request
forgery: can a registered backend URL, a tool argument, or a JWKS discovery URL
be pointed at `169.254.169.254` (cloud metadata) or an internal host? On
[a2aproject/a2a-python](a2aproject-a2a-python.html) last week this check came
back *negative* — the push-notification sender had no egress validation at all
(mitigated only by the finding's blind/authenticated shape). Here it comes back
thoroughly **positive**.

ContextForge ships a dedicated `SecurityValidator` (`mcpgateway/common/validators.py`,
~2,300 lines) whose `validate_url` / `_validate_ssrf` runs on a percent-decoded
copy of the URL, rejects IPv6-literal and protocol-relative forms and JS-style
`\uXXXX` escapes, and then checks the resolved host against a configurable SSRF
policy. The defaults are the point:

- `ssrf_protection_enabled = True`
- cloud metadata (`169.254.169.254/32`, `169.254.169.123/32`, IPv6 `fd00::1`) and
  the **full link-local ranges** (`169.254.0.0/16`, `fe80::/10`) are **always**
  blocked, regardless of other settings
- metadata hostnames (`metadata.google.internal`, `metadata.internal`) blocked
- `ssrf_allow_localhost = False` — loopback blocked by default
- `ssrf_allow_private_networks = False` — RFC 1918 blocked by default, unless a
  specific CIDR is added to `ssrf_allowed_networks`

The validator is wired into every egress path that matters — the HTTP client
service, the A2A service, the OAuth/JWKS manager, the OpenAPI service, the LLM
proxy — and there's a separate `test_ssrf_redirect_protection.py` covering the
redirect-follow bypass, plus a Rust `backend_url_validator.rs` for the runtime
crate. A static scanner can flag a missing guard; it structurally can't *credit*
one, which is why a rich surface like this reads as 946 findings until you trace
the egress by hand.

## The auth path: 11 "unverified JWT decode" highs, all the peek-then-verify pattern

The next thing that looks alarming on a gateway is `jwt.decode(token,
options={"verify_signature": False})` — 11 of them, in `verify_credentials.py`,
`routers/auth.py`, `token_validation_service.py`, and the SSO/email-auth routers.
On an auth boundary, an unverified decode used to *grant* access is a textbook
bypass. None of these do that:

- **`verify_credentials.py` (681, 1968, 2082):** each decodes without verifying
  **only to read the `iss` claim**, then routes to the proper JWKS-based
  signature check (`verify_external_idp_token` / `verify_oauth_access_token`).
  The docstrings even note "JWKS discovery, SSRF defense and ID-token rejection
  are inherited." Peek at the issuer to pick the key, then verify — the standard,
  correct pattern.
- **`routers/auth.py:238` / `:321`:** decode a token the gateway *just created*
  to pull the `jti` for a CSRF-cookie binding ("don't verify since we just
  created it") and re-read claims after `get_current_user` already verified
  ("Already verified by get_current_user"). Own token, no trust decision.
- **`token_validation_service.py:288`:** explicitly documented "best-effort,
  **advisory** validation … the upstream MCP server is the authoritative token
  validator … warnings are logged but do not block token forwarding." The gateway
  doesn't hold the IdP's keys, so it can only log claim mismatches, not enforce.

The main verification path (`verify_credentials.py:325`) builds proper
`verify_signature` / `verify_exp` / `verify_aud` options and is the one that
actually gates access.

## Where the other 900 findings come from

- **581 "generic-api-key" secrets — 521 of them inside `.secrets.baseline`.**
  ContextForge uses detect-secrets with a committed, audited baseline file; the
  gateway's own secret inventory (regenerated 2026-07-16) is itself scanned by
  Gitleaks and every allowlisted entry re-flagged. This is the single largest
  tooling false-positive I've recorded — a scanner re-reporting another scanner's
  suppression file. The remaining ~60 are `tests/` fixtures and `docs/` examples.
- **142 "logger-credential-leak":** the auth/services logging discipline is
  actually careful — e.g. `admin.py:4540` logs the *email* on an auth failure,
  not a password or token. The rule fires on auth-context words near a log call,
  not on a secret being logged.
- **~80 Admin-UI findings** (20 Jinja2-XSS, 33 `django-no-csrf-token`, 28
  insecure-websocket): all in `mcpgateway/templates` / the admin front-end, which
  `SECURITY.md` explicitly frames as **development-only, localhost-only, and
  disabled in production** (`MCPGATEWAY_UI_ENABLED=false`). Documented scope.
- **6 `run-shell-injection`:** all in `.github/workflows` (docker-multiplatform,
  pytest) on trusted triggers (push / merge_queue / workflow_dispatch / cron)
  with static build steps — CI hardening lint, not injection.
- **`disabled-cert-validation` (2), `dynamic-urllib` (2), `subprocess-shell-true`
  (2):** all in `smoketest.py` / `run_mutmut.py` / `scripts/test_sqlite.py` —
  test and dev harnesses.
- **Dependencies clean:** pip-audit reports 0 vulnerable packages; Trivy reports
  a single medium. The repo carries `.snyk`, `.grype.yaml`, `.whitesource`, and a
  detect-secrets baseline, and patches criticals within a week per its policy.

## Patterns observed

The lesson this scan sharpens is that **surface richness and finding count are
not signal.** ContextForge has the widest genuinely-dangerous surface I've
scanned — it proxies arbitrary backends, forwards OAuth tokens, discovers remote
keys, and runs plugins — and it produced 946 findings, more than any clean scan
before it. Yet the two questions that actually decide a gateway's security
posture (is the egress SSRF-guarded? is the token path verified before it grants
access?) both resolve to "yes, by default," and you can only learn that by
reading the code. The count is dominated by a scanner re-flagging another
scanner's own baseline file.

It's also a study in what a mature security program looks like from the outside:
a 43 KB `SECURITY.md` that tells you to disable the Admin UI in production and
audit the code yourself; pre-commit gates running Bandit, Semgrep, Dodgy, and
detect-secrets; Cosign keyless-OIDC signing and attestation on release images;
secure-by-default SSRF config where you have to *opt in* to reach localhost or
RFC 1918. The right way to read a project like this is not "709 highs" but "which
of these defenses would I have to disable to get hurt" — and here the answer is
all of them, deliberately, with flags that default to safe.

## Notes on the tool

Each of these maps to an AI PatchLab backlog item:

- **Honor `.secrets.baseline` / detect-secrets exclusions.** 521 of 581 secret
  hits were inside the project's own audited baseline file. Gitleaks should skip
  a committed `.secrets.baseline` (and respect its `exclude` block) the way we
  already want to honor `# pragma: allowlist secret` (AG2) and detect-secrets
  baselines (Kiln). This is the **highest-value** backlog item from this scan —
  it would delete the single largest FP cluster in the series.
- **`unverified-jwt-decode` needs dataflow.** All 11 sites were "decode to read
  `iss`/`jti`, then verify" or a documented advisory-only decode. The rule should
  check whether the unverified payload flows into an access decision, or only
  into key-selection / logging before a real `jwt.decode(..., verify_signature=
  True)` on the same token.
- **A "dev-only surface" signal.** When `SECURITY.md` documents a component as
  development-only and feature-flag-disabled in production (the Admin UI here),
  its XSS/CSRF/websocket findings are documented-scope — treat like `tests/` /
  `legacy/` candidate-FPs (potpie's `legacy/` lesson).
- **SSRF: credit the defense.** This is the positive complement to the a2a-python
  webhook-SSRF taint rule. When an egress `url` flows through a `validate_url` /
  `_validate_ssrf` guard on the path, the egress finding should flip. A scanner
  that only flags *missing* guards will always over-count a well-defended gateway.

## Disclosure timeline

- 2026-07-17 — scan run (commit `50602d6`), curated to 0 real findings
- 2026-07-17 — public post (this page); **no upstream issue filed** — strict-norm
  (IBM PSIRT requests private reporting; there is nothing exploitability-shaped to
  report)

## Reproduce

```bash
python scanner/run_scan.py \
  --from-git-url "https://github.com/IBM/mcp-context-forge" \
  --reports-dir ./reports/ibm-mcp-context-forge \
  --min-severity medium --ignore-samples
```
