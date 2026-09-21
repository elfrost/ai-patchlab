---
layout: default
title: "HarnessRouter/harnessrouter: security scan"
date: 2026-09-21
---

# HarnessRouter/harnessrouter - security scan

**Repository:** [HarnessRouter/harnessrouter](https://github.com/HarnessRouter/harnessrouter)
**Commit scanned:** `76c0d0a`
**Scan date:** 2026-09-21
**Disclosure status:** post-only — the actionable item is a published upstream dependency CVE, not a first-party code bug; no advisory filed. The maintainer has a real SECURITY.md with private vulnerability reporting enabled, which is the right channel for a bump they may not be seeing (see below).

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 42 |
| Medium | 70 |
| Low | 0 |
| Info | 3 |

**Total findings:** 117 (1 actionable after curation — a dependency-currency finding, not a code defect)

## Scan coverage

The dependency picture on this repository is only legible if you read the
coverage block first, because the two dependency tools **disagreed about
whether there was anything to scan** — and one of them was wrong.

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | No supported Python dependency manifest found |
| `ai-security-review` | `not_run` | disabled by default (ADR-010) |

**Coverage complete:** no. `dependency-scan` (pip-audit) reported **no manifest
at all** — it scans the repository root, and this project keeps its Python
requirements in `gateway/requirements.txt` and `runner/requirements.txt`, one
level down. Trivy walks the whole tree, so it read both and found 53 + 1 pip
advisories the root-only pass never saw. **On a monorepo, "no manifest found"
reads identically to "clean" unless you say otherwise** — this is exactly that
case, and everything of interest below came from the tool that looked deeper.
Semgrep's partial status is non-Python config/data files, no first-party module
skipped.

## Top findings

### 1. Pinned Next.js is one patch behind two published unauthenticated-RCE fixes

- **File:** `ui/package-lock.json` (`next` 15.5.23), reachable via the published UI port
- **Tool:** trivy
- **Confidence:** high on the currency gap; medium on worst-case reachability
- **Why it matters:** The lockfile pins `next` **15.5.23**; **15.5.24** fixes two
  criticals — [CVE-2026-75604](https://github.com/advisories) (RCE on
  *Windows-hosted* servers) and
  [GHSA-2xp9-vwfh-vxw4](https://github.com/advisories) (RCE in the **Image
  Optimization API** when AVIF files are processed). The first **does not apply
  as shipped** — the image is `python:3.12-slim`, i.e. Linux — and I dropped it.
  The second is the one to act on: the app declares no `images` config, so the
  optimizer runs at its **default (enabled)** setting, and the middleware
  matcher **explicitly excludes `_next/image`**, so the optimizer endpoint is
  reachable **without a session**. The app itself never imports `next/image`, and
  the default-empty `remotePatterns` constrains an attacker from pointing the
  optimizer at their own host — so this is a *reachable surface to a fixed
  critical*, not a demonstrated end-to-end RCE. I could not stand up the
  container to run the exploit primitive, so I am not claiming more than the
  currency gap plus the exposed surface.
- **Recommendation:** Bump `next` to `>=15.5.24` (the pin is `^15.5.19`, so this
  is a lockfile refresh) and add a `dependabot.yml` covering **both** `npm` and
  `pip` — there is none today, so the lockfile will not self-update, and (see
  coverage) a root-only dependency scan will not flag the Python side at all.

### 2. `gateway/requirements.txt` carries auth- and crypto-relevant CVEs (currency)

- **File:** `gateway/requirements.txt`
- **Tool:** trivy
- **Confidence:** high that the CVEs are real; low that they are reachable *self-hosted*
- **Why it matters:** The gateway pins `PyJWT` 2.10.1 (CVE-2026-48526,
  *authentication bypass via forged tokens*), plus `cryptography` 44.0.0,
  `aiohttp` 3.11.11, and `python-multipart` 0.0.20, all with published fixes.
  Self-hosted reachability is low — the gateway binds **loopback only**, and the
  self-hosted entrypoint runs `HR_IDENTITY_MODE=off`, so the login-JWT path
  (where PyJWT matters) is not the security boundary there. But **the hosted
  build shares this code**, where identity *is* enforced by that JWT, so this is
  worth the maintainer's attention regardless of the self-hosted default.
- **Recommendation:** Refresh the gateway pins; the dependabot config from
  finding 1 covers this file too.

## Why the rest were dismissed

Of 117 findings, 116 were false positives, by-design, or not-applicable. One
sentence on the largest family: the 43 `by-design` findings are dominated by 29
`github-actions-mutable-action-tag` (SHA-pin hardening on CI action refs) and 11
workflow shell-injection hits that all sit on `workflow_dispatch` or
`push: tags` triggers — the `${{ }}` input comes from someone who already holds
write access, so the [trigger decides the severity](lightseekorg-tokenspeed.html)
and here it decides "not outsider-reachable."

| Reason | Findings |
| --- | ---: |
| `by-design` | 43 |
| `below-min-severity` | 22 |
| `confirmed-real` | 13 |
| `product-surface` | 13 |
| `not-reachable` | 1 |
| `test-or-fixture-path` | 1 |

The 13 `product-surface` hits are subprocess/audit rules in `runner/`, which
spawns agent CLIs (Codex, Claude Code, and a dozen others) as a per-session uid
— [running code *is* the product](realiti4-claude-swap.html), and the one real
injection boundary (the per-session uid write-wall) is guarded. The one
`test-or-fixture-path` is a synthetic key in `gateway/tests/test_media_attack.py`;
the `not-reachable` one is the Windows-only Next.js RCE from finding 1. A
`detect-insecure-websocket` "high" was a plain false positive — it matched
`ws://` inside a `.replace()` scheme-transform string, not an actual socket.

## Patterns observed

The interesting story here is not a bug — it is a **well-built authorization
layer that survives the sweep the series usually breaks projects on.** I ran the
route inventory: 113 gateway routes, and after resolving the project's own
identity idioms (`_owned_session`, `_pub_org_member`, `_principal`), exactly five
answer without a credential — `/v1/uhp` discovery, `/healthz`, `/readyz`,
`/version`, and `/share/{token}` where the unguessable token *is* the credential.
Every session, file, workspace, and media route enforces org ownership. That is
the [name-matched-sweep](mai-with-u-maibot.html) coming back empty for the right
reason, not the wrong one.

Two design choices earn credit. First, the self-hosted **BFF stamps its internal
trust key onto a gateway call only for a request carrying a valid session
cookie** — an earlier version stamped it unconditionally ("there is no login"),
and the code comments document catching and fixing exactly that
([the conditional-verification class](sentelabsai-openexecutive.html), fixed
before I arrived). A bearer-only request forwards bare and gets the gateway's own
401. Second, the **gateway binds loopback and only the UI port is published**, so
the [DNS-rebinding shape](liaohch3-claude-tap.html) that has caught several
desktop apps in this series does not apply — the published surface is the
session-gated Next.js app, with `X-Frame-Options: DENY` and
`frame-ancestors 'none'` set. When the machine is well-built, the finding moves
to the dependency manifest, and that is where it moved.

## Notes on the tool

This scan is a clean example of the **root-only dependency-scan blind spot**
(already a known AI PatchLab gotcha): pip-audit reported "no manifest" and would
have rendered as a clean Python dependency surface, when in fact two subdirectory
`requirements.txt` files carried 54 advisories. Trivy's whole-tree walk is what
saved the run. The backlog item is real: `scan_dependency` should descend into
common subdirectory manifest locations (or at least emit a *louder* meta-finding
when it finds none but Trivy reports pip advisories) rather than leaving the two
tools to silently disagree.

## Disclosure timeline

- 2026-09-21 — scan run; curated to one actionable dependency-currency finding
- 2026-09-21 — public post (this page). No advisory filed: the actionable item is
  a published upstream CVE with a one-line fix, not a first-party defect, and I
  could not run the exploit primitive to justify an RCE-shaped advisory. A short
  private note via the maintainer's enabled private vulnerability reporting would
  be a reasonable courtesy, since they have no dependabot and may not be seeing
  the Python side at all.

## Reproduce

```bash
git clone https://github.com/HarnessRouter/harnessrouter /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/harnessrouter-harnessrouter --min-severity medium
```
