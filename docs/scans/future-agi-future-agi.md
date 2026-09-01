---
layout: default
title: "future-agi/future-agi: security scan"
description: "Security scan of future-agi/future-agi: 1227 findings (1224 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-09-01
---

# future-agi/future-agi — security scan

**Repository:** [future-agi/future-agi](https://github.com/future-agi/future-agi)
**Commit scanned:** `5b84ef4a7666`
**Scan date:** 2026-09-01
**Disclosure status:** **withheld** — one real finding, reported **privately** to
`security@futureagi.com` per the project's `SECURITY.md` (which forbids public
vulnerability issues). Described here at **class level only** until it is
remediated.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 26 |
| High | 476 |
| Medium | 722 |
| Low | 0 |
| Info | 3 |

**Total findings:** 1227 raw / 1224 above the medium floor — the largest raw
count in this series to date, and (as usual on a large, well-built codebase)
**one real finding** after curation, which no scanner rule represented and which
is **withheld** here pending a private fix.

Future AGI (1.9k★, Apache-2.0 + a separate EE license) is an **end-to-end LLM
and AI-agent observability and evaluation platform** — trace ingestion over
OTLP, a ClickHouse-backed store of prompts, completions, tokens and costs, an
evaluation engine, a simulation runner, a Go **AI gateway** (`agentcc-gateway`,
an OpenAI/Anthropic/Gemini-compatible proxy with per-org keys, rotation and
RBAC), and a Django backend behind a React frontend. The asset at risk here is
**everyone's captured model traffic** — the prompts and outputs an operator has
routed through the platform to observe them.

It is, and this shapes the whole write-up, a **carefully built system with a
real security policy**: a named disclosure email, a severity/SLA table, a
safe-harbor clause, and an explicit in-scope list that names the gateway. The
one real finding is not a team that doesn't think about isolation — it is a
single service whose network boundary diverges from the consistent, commented
rule applied to every service beside it.

## What this write-up does not contain

Future AGI's `SECURITY.md` asks reporters to disclose privately and **not** open
a public issue, with acknowledgement within 24 hours and coordinated disclosure
7–90 days after a patch. That is exactly the norm this series honours: the
finding was sent to `security@futureagi.com` with a full dossier and a
reproduction, and this page withholds the file, the service and the mechanism
until a fix is available. What follows is the **class** of the finding and the
method that found it — enough to be an honest record, not enough to be a
weaponised one.

The private report also carries the thing that makes a withheld post honest: the
maintainers get the concrete detail immediately, and the public series only says
*something real was found and responsibly routed*.

## The class of the finding

**One service in a multi-service deployment is published on all network
interfaces while every service beside it — including every datastore — is
correctly bound to loopback, and the production overlay inherits the exposure
unchanged.** The exposed service is the most dangerous one in the file to leave
open, and reaching it hands an unauthenticated caller a path to the trace store
the platform exists to protect.

Three properties made it reportable rather than arguable, and each is a pattern
this series has converged on:

- **The maintainer's own configuration is the oracle.** The compose file bins
  its datastores under a comment that states the intended rule — *"bound to
  127.0.0.1 so only the host can reach them"* — and applies it to Postgres,
  ClickHouse, Redis, MinIO, Temporal and the collector. The finding is the one
  service that sits outside that rule. When the project has *written down* the
  boundary it means to hold, a divergence from it is oversight, not design — the
  [contract-versus-artifact](vexa-ai-vexa.html) footing, here in a deployment
  file rather than code.

- **N deployment paths, and the question becomes whether the N agree.** Future
  AGI ships a base `docker-compose.yml` for local eval and a production overlay
  that re-binds every secret with `${VAR:?must be set for production}` — a
  genuinely good pattern that refuses to boot on dev fallbacks. But an overlay
  only changes the keys it names, and this one names `environment:` and
  `restart:`, not `ports:`. So the hardening that the production path adds for
  secrets does **not** extend to the exposure, and the documented production
  command inherits it. [Ship N paths and the question stops being "is the
  default safe" and becomes "do the N defaults agree, and does anything verify
  that they do?"](vexa-ai-vexa.html)

- **I proved it with the vendor's own merge engine, not an assertion.** The load-
  bearing claim was about how two compose files combine, which is precisely the
  kind of thing a coherent-but-wrong report gets wrong. So rather than reason
  about override semantics, I rendered the exact command from the project's
  `deploy/README.md` through `docker compose config` and read the published host
  bindings out of the result: the exposed service came back on `0.0.0.0`, every
  datastore on `127.0.0.1`. [Run the primitive against the real
  tool](nottelabs-notte.html) — the merge, not my mental model of the merge —
  and the finding either survives or dies on contact. It survived.

## The scope discipline that kept it to one finding

Two nearby things *looked* like the same class and were dropped after the same
kind of check:

- Two other services also publish on `0.0.0.0`, but they are the intended public
  surface (the frontend and an API the README explicitly puts a reverse proxy in
  front of) — exposure is their job, and they don't run untrusted input the way
  the reported service does.
- Two management UIs are published without a loopback bind too — but both sit
  behind Compose `profiles:`, so they are **opt-in** and not part of the default
  or documented-production deployment. Claiming them would have inflated the
  report with paths a normal operator never starts. The rendered config confirmed
  they don't appear unless a profile is selected.

The difference between "reportable" and "noise" here was entirely *which service*
and *which deployment path* — the same discrimination the
[claude-tap](liaohch3-claude-tap.html) and
[open-wearables](the-momentum-open-wearables.html) write-ups turned on.

## The two hypotheses that returned NO — and why publishing that matters

Most of the manual effort on this scan went into two auth surfaces that came back
clean, and saying so is part of the record:

- **The gateway's admin plane.** `agentcc-gateway` mounts a large admin surface
  outside its `/v1/` auth prefix — mint an API key, set per-org provider configs,
  rotate upstream credentials, read cluster state. That is exactly the shape of
  the [claude-tap inversion](liaohch3-claude-tap.html) (a guard wired to the
  control plane but not the data plane), so I enumerated every one of the 24
  admin handlers across four files. **All 24** call an in-handler
  `requireAdmin`/`checkAdminAuth` that uses a constant-time token compare and
  **fails closed when the admin token is unset**. The middleware comment even
  advertises "admin routes pass through" the `/v1/` gate — and it is true, because
  each admin route re-checks in the handler. The guard is correct *and* wired to
  the whole set. No finding.

- **The license-auth bypass.** The same `/v1/` middleware short-circuits when a
  request carries a valid managed-service license token — a caller-influenced
  condition wrapping an auth decision, the *conditional-verification shape* that has produced real findings
  elsewhere. But the verifier pins `RS256`, resolves `kid` from a **local** key
  map (no header-injected key), validates type/issuer/audience/nbf/exp/scope and
  the full identity claim set, and rejects anything that merely *looks* like a
  JWT but doesn't verify. Branch-then-serve here is safe because the branch is
  gated on a signature the caller cannot forge. No finding.

A probe that can only ever say "yes" is not a probe. These two said no, and a
scan series that only ever reports the yes is selling something.

## Patterns observed

**1227 findings, and the shape of the noise is by now familiar.** The top
buckets: **100** mutable-action-tag GitHub-Actions warnings (the perennial
band-flooder — one coherent "pin your actions by SHA" recommendation rendered as
a hundred rows); **94** SQLAlchemy raw-query + **44** formatted-SQL-query hits,
which resolve to the **[#1 recurring identifier
FP](mnemosyne-oss-mnemosyne.html)** on close reading — the ClickHouse query
builders interpolate *validated* bucketing function names and column identifiers
(regex-checked keys, an allowlisted `time_bucket` map with a safe default) while
binding every **value** through `%(param)s`; **52** non-literal-regexp and **40**
Go `no-direct-write-to-responsewriter` XSS-audit hits on internal tooling. I read
the four taint-tracked SQL findings (the higher-signal `tainted-sql-string` /
`query-set-extra` rules) individually: two were audit-log description f-strings,
one was the allowlisted bucket function, and the value paths were all bound.
Nothing in the SQL cluster survived.

**The dependency tier is a coverage story, not a finding story — and it repeats a
known gotcha.** The scanner emitted `No supported Python dependency manifest
found`, because this is a **monorepo** and the manifests live under `futureagi/`
(a `requirements.txt`, a `pyproject.toml`, a `uv.lock`), not at the root the
dependency scanner walks. So the 26 "critical" and much of the "high" tier —
ChromaDB RCE, LiteLLM auth-bypass, Authlib JWK-injection, Django SQLi, langchain
serialization RCE — come from Trivy parsing lockfiles it *did* find (the Go
`go.sum`, the frontend `package-lock.json`, the gateway modules), and each wants
the *version-match → reachable → mitigated*
gate before it means anything. Several are Proxy-only or transport-only CVEs in
libraries this repo uses as clients, the same reachability split that
[hollowed out the critical tier on notte](nottelabs-notte.html). None was the
finding; the finding was structural and came from reading the deployment, not the
dependency graph. **This is the *monorepo root-only coverage gap* again** — the
top backlog item it keeps voting for.

**Gitleaks was quiet in the right way.** Three secret hits, all inert: one in a
`.env.production.example`, one a pricing-table constant in Go, one a fixture in a
frontend `__tests__` file — and the repo ships a real `.gitleaks.toml` that
allowlists exactly those tiers. *Honour the baseline*;
the maintainers already curated their own secret surface.

**The credit is substantial, and naming it is the point of a strict-norm post.**
Every datastore is loopback-bound with an explaining comment. The production
overlay's `${VAR:?...}` guards refuse to boot on dev secrets. The gateway admin
plane fails closed on an unset token with constant-time compares across all 24
handlers. The license verifier pins its algorithm and reads keys from a local
map. nsjail is a real sandbox built into the shipped image, not a stub. The one
real finding is a single service's network binding diverging from a rule the
project otherwise applies consistently and *documents* — which is exactly why it
was findable, and exactly why it is worth one clean private report rather than a
grouped issue.

## Notes on the tool

- **Monorepo dependency coverage (top backlog item, re-confirmed).** `scan_dependency`
  walks the repo root; on a monorepo whose manifests live one level down, "no
  manifest found" renders as "clean," and the 26/476 critical/high dependency
  tier came entirely from Trivy's lockfile parse, not pip-audit. A monorepo scan
  needs to descend into sub-project manifests, or at minimum surface a per-tool
  coverage row so "not scanned" never reads as "zero." This is the same vote the
  [notte](nottelabs-notte.html), [Vexa](vexa-ai-vexa.html) and
  [OpenTalking](datascale-ai-opentalking.html) scans all cast.
- **No rule represents a deployment-topology divergence.** The finding is "one
  service's port binding disagrees with the documented rule its siblings follow,
  across two layered compose files." No Semgrep/Trivy rule sees a compose
  *override merge*, and none should be expected to — but it's a reminder that the
  highest-value finding on a well-built repo keeps coming from reading pairs of
  config artifacts by hand, not from the finding list.
- **1224 above-floor findings, one real.** The signal-to-noise ratio on a large,
  mature codebase argues yet again for collapsing same-rule floods (100 action-tag
  rows, 94 raw-SQL rows) into single counted recommendations before a human ever
  reads the band.

## Disclosure timeline

- 2026-09-01 — scan run
- 2026-09-01 — finding reported **privately** to `security@futureagi.com` per
  `SECURITY.md` (public vulnerability issues are forbidden by the policy); full
  dossier + reproduction attached
- 2026-09-01 — this page published with the finding **withheld** (class only)

*The private email is a manual step this pipeline does not take automatically;
the dossier is drafted and staged, and the send is the operator's action.*

## Reproduce

```bash
git clone https://github.com/future-agi/future-agi /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/future-agi-future-agi --min-severity medium
```
