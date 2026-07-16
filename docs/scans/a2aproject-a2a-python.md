---
layout: default
title: "a2aproject/a2a-python: security scan"
date: 2026-07-16
---

# a2aproject/a2a-python - security scan

**Repository:** [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python)
**Commit scanned:** `86c6b0d7dd3ea83efb808de348a0021677b2f0b2`
**Scan date:** 2026-07-16
**Disclosure status:** public — post-only (strict-norm: official SDK + private-reporting SECURITY.md; nothing cleared the quality gate)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 10 |
| Medium | 10 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 20 (0 real after curation; one deployer-hardening note documented)

This is the official Python SDK for the Agent2Agent (A2A) protocol — the
Google/Linux-Foundation agent-interop standard. A protocol SDK's security lives
in two places static rules barely touch: how it authenticates peers, and what it
does with the **push-notification webhook URL** a client hands it. The code
scanned clean (lint + test fixtures); the one thing worth writing down is that
the reference push-notification sender POSTs to the client-supplied URL without
egress validation — a real webhook-SSRF surface, but an authenticated,
blind, deployer-mitigable one.

## Top findings

### 1. Push-notification sender has no SSRF egress validation (deployer hardening)

- **File:** `src/a2a/server/tasks/base_push_notification_sender.py`
- **Tool:** manual completeness sweep (semgrep does not flag this)
- **Confidence:** real surface; authenticated + blind + library-level
- **Why it matters:** A2A push notifications let an agent server POST task
  updates to a webhook URL the client registered. `BasePushNotificationSender`
  does exactly `url = push_info.url; await self._client.post(url, …)` — and
  there is **no URL validation anywhere in the path** (`is_private`,
  `ip_address`, `urlparse`, `validate_url` all return zero across the repo). So
  an authenticated client can register `url = http://169.254.169.254/…` and make
  the server emit a POST at an internal endpoint — the webhook-SSRF class.
- **Why it stays a note, not a filing:** Three things pull the severity down.
  (1) The URL comes from an **authenticated client** — the task submitter's own
  webhook, not an anonymous attacker. (2) It's **blind**: the send is a POST
  whose response is only `raise_for_status()`'d server-side, never returned to
  the client, so there's little exfil oracle. (3) It's a **library** — the
  reference sender — where egress controls (a private-IP block, an allowlist,
  network-level egress policy) are conventionally the deployer's or the spec's
  responsibility. And the design **does** include webhook authentication: the
  config carries a `token` the server sends as `X-A2A-Notification-Token`, so a
  receiver can verify the notification is genuine (anti-spoofing was considered).
  The honest recommendation is a deployer one — validate/allowlist push URLs and
  block link-local/private ranges — or an SDK hook to make that easy.

### 2. The auth interceptor logs schemes, not tokens

- **File:** `src/a2a/client/auth/interceptor.py:59,72,87`
- **Tool:** semgrep (`python-logger-credential-disclosure`)
- **Confidence:** high — FP
- **Why it matters / why it doesn't:** Three hits in the credential interceptor
  look like token logging. Every one logs the **scheme name**
  (`logger.debug("Added Bearer token for scheme '%s'.", scheme_name)`) — the
  Bearer/API-key credential is written to the request headers and never to the
  log. Correct correlation-logging discipline, the same pattern that keeps
  false-positiving across the series (codex-lb, mnemosyne).

### 3. The rest is CI lint, a test-fixture secret set, and one dep CVE

- **Tool:** semgrep + gitleaks + trivy
- **Confidence:** high — FP / minor
- **Why it matters / why it doesn't:** 7 `github-actions-mutable-action-tag` +
  3 dependency-cooldown nits + a `python37-compatibility` lint make up the
  semgrep bulk. All 8 gitleaks hits are in `tests/` (task-store and
  client-server integration fixtures). trivy's single finding is a `starlette`
  `request.form()`-limit CVE — reachable only when the server transport uses
  Starlette form parsing, version-match, DoS-class. Dependabot is wired.

## Patterns observed

**For a protocol SDK, the security is the peer boundary — auth and callbacks.**
Nothing in the injection/deserialization/secret families mattered here (no
`eval`, no untrusted `pickle`, no wildcard CORS, credentials logged as scheme
names). The one place worth reading closely was the push-notification path,
because "server POSTs to a URL the peer chose" is the callback-SSRF shape every
webhook system has to reckon with. A2A reckoned with the *authenticity* half
(the notification token) and left the *egress* half to the deployer — a
defensible split for a reference implementation, and one worth stating out loud
so deployers add the URL allowlist.

**Blind, authenticated, library-level — the three qualifiers that keep this a
note.** The same raw finding ("no SSRF validation on an outbound POST") would be
a filed issue on an app that fetches attacker-controlled URLs and returns the
body. Here the requester is authenticated, the response never comes back, and
the SDK is the layer below where egress policy usually lives. Naming the
qualifiers is the curation, the same way the tradingview-mcp and OpenKB scans
separated operator-directed fetches from attacker-directed SSRF.

**Strict-norm, so the channel matters too.** The SDK ships a SECURITY.md that
asks for private vulnerability reports and coordinated disclosure. A public
issue about push-notification SSRF would violate that policy; and for a
Google/LF-governed standard, an authenticated-client blind-SSRF on the reference
sender is very likely already a known spec-level consideration. Documenting the
deployer-hardening note here is the proportionate action.

## Notes on the tool

- **Callback/webhook SSRF is a semgrep-blind, protocol-shaped surface.** The
  scanner said nothing about the one thing worth reading. An outbound-request
  sink whose URL traces to a stored config (`push_info.url`) — with no
  `ip_address`/`urlparse` guard on the path — is a detectable taint pattern worth
  a rule, distinct from the operator-directed-fetch false positives.
- **`python-logger-credential-disclosure` fired on scheme-name logging again.**
  The argument to the log call was a scheme identifier, not the credential
  variable. A check on *what is interpolated* (id/scheme vs. the secret) would
  clear this recurring class — noted on codex-lb and mnemosyne.
- **`tests/` gitleaks and `github-actions-mutable-action-tag`** continue to
  dominate raw counts on otherwise-clean repos; both are established candidate-FP
  / rollup backlog items.

## Disclosure timeline

- 2026-07-16 — scan run
- 2026-07-16 — public post (this page); post-only, no upstream issue filed

This is a post-only write-up. The code is clean (credentials logged as scheme
names, secrets confined to tests, deps on Dependabot), and the one real surface —
push-notification egress — is an authenticated, blind, deployer-mitigable
hardening note on a strict-norm SDK that already authenticates its webhooks.
Nothing cleared the quality gate; the note is documented for deployers rather
than filed.

## Reproduce

```bash
git clone https://github.com/a2aproject/a2a-python /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/a2aproject-a2a-python \
  --min-severity medium --ignore-samples
```
