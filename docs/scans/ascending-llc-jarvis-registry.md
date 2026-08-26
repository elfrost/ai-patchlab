---
layout: default
title: "ascending-llc/jarvis-registry: security scan"
description: "Security scan of ascending-llc/jarvis-registry: 235 findings at medium+, one real horizontal-authorization gap disclosed privately (detail withheld), and a credentialed-CORS allowlist that turns out to be inert."
date: 2026-08-26
---

# ascending-llc/jarvis-registry — security scan

**Repository:** [ascending-llc/jarvis-registry](https://github.com/ascending-llc/jarvis-registry) — 2.8k★, Apache-2.0, an enterprise MCP/A2A gateway that brokers per-user OAuth credentials to downstream tool servers. Commercially backed (Ascending LLC).
**Commit scanned:** `3f7601248487` (HEAD of `main` at scan time)
**Scan date:** 2026-08-26
**Disclosure status:** **Private.** The project's SECURITY.md asks explicitly that security issues go to `security@ascendingdc.com` and that no public GitHub issue be opened. One Medium-severity finding was written up and routed to that address; the technical detail is **withheld from this post**, and only the finding *class* appears below. This page will be expanded once the maintainers resolve, or after a 90-day window.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 4 |
| High | 102 |
| Medium | 126 |
| Low | 0 |
| Info | 3 (filtered) |

**235 findings at `--min-severity medium`. After curation: one real defect, and it is a horizontal-authorization gap that no scanner flagged.** Everything the scanners *did* flag retired — including all four criticals and the single largest family — for reasons given in full below. This is a genuinely well-built codebase; the interesting result is not the headline count but that the scariest-looking finding died on verification, and the one that survived came from reading two adjacent route handlers against each other.

## The finding (class only, detail withheld)

**Class:** missing object-level authorization on an authenticated read endpoint — CWE-639, *Authorization Bypass Through User-Controlled Key* (horizontal IDOR).

The shape, without the specifics: two sibling handlers in the same router return per-user state derived from the same identifier. One of them takes the caller's identity and enforces an ownership check against that identifier before answering. The other — matched by the same coarse permission rule — takes no caller identity at all and performs no ownership check. The identifier is deterministic rather than secret, and the permission that gates the endpoint is held by every role the project defines, down to the read-only one.

**The intra-repo differential is what makes this a defect rather than a design choice.** The guarded sibling proves the project's own intended contract: this class of identifier is *supposed* to be checked against the caller. One handler implements that contract and its neighbour does not. That asymmetry is not something a rule can see — both handlers are individually well-formed FastAPI code — but it is decisive, because the codebase itself supplies the control.

A concrete patch, written against the repo's existing dependency-injection idiom and matching the guarded sibling line for line, went out with the private report.

## What the scanners flagged — and why none of it survived

### 21× GitHub Actions shell injection (`high`) — not exploitable, wrong trigger

Semgrep's `run-shell-injection` fired 21 times on `${{ github.* }}` interpolation inside `run:` steps. The rule is right about the pattern and wrong about the risk **here**, because the risk is a function of the trigger, not the interpolation:

| Trigger | Workflows | Outside contributor can reach secrets? |
| --- | --- | --- |
| `pull_request` | `lint.yml`, `test.yml` | No — fork PRs get a read-only token and no secrets |
| `push` | `docs.yml`, `gitnexus-index.yml` | No — requires write access already |
| `workflow_call` | `build-images-reusable.yaml` | No — invoked by trusted callers |
| `workflow_dispatch` / `release` | `create_release.yaml`, `deploy.yaml`, `tag_build_images.yaml`, `release_changelog.yaml` | No — requires write access already |
| **`pull_request_target`** | **none** | — |

There is no `pull_request_target` anywhere in the repository. That single fact retires the entire family: injection into a workflow that never runs privileged against untrusted code buys an attacker nothing they did not already have. Worth fixing as hygiene (`env:` indirection is one line), not worth a security ticket.

### 52× mutable action tags (`medium`) — the series' most common class

`actions/checkout@v4` and friends referenced by mutable tag rather than pinned SHA. Real supply-chain hygiene, low priority, and the single most frequent finding across this entire scan series. One pinning pass closes it.

### 4× LiteLLM CVEs including 2 criticals — declared, never imported

Trivy's four highest-severity hits — SQL injection in proxy key checks, Host-header auth bypass, command execution via MCP stdio, API-key privilege escalation — are all **LiteLLM Proxy-server** vulnerabilities. This project declares `litellm>=1.50.0` in `registry/pyproject.toml` and then **never imports it**: a repository-wide grep for `litellm` outside the lockfile returns exactly one line, the dependency declaration itself. No proxy is started in `docker-compose.yml`. The lock pins a vulnerable 1.83.0 and should be bumped as routine dependency maintenance, but the affected surface is not built here and the reachable-here answer is no.

This is the third gate of the series' standing checklist doing its job: version-match → **reachable?** → mitigated in-app? A raw CVE table would have reported two criticals against a security gateway. Both are noise.

### ~40 npm advisories (axios, brace-expansion, js-yaml, ws, postcss, webpack-dev-server, …)

Frontend build- and dev-time dependencies, overwhelmingly denial-of-service. `webpack-dev-server` in particular does not ship to production. Routine `npm audit fix` territory.

### 16× "secret detected" — all false positives (credit the defense)

| Location | Count | What it actually is |
| --- | ---: | --- |
| `docs/*.md` (setup guide, API reference, JWT vending, design docs) | 11 | illustrative example output — `# You'll see output like:` |
| `scripts/seed_mongodb.py` | 5 | fixture rows: `sk_test_xyz789012345678901234567890abcdefgh` |

The repo ships a **`tartufo.toml`** with per-pattern exclusions and a *written reason on every one* ("sample env template with placeholder values", "OpenAI model name is not credential"). That is a maintained secrets baseline, not a rubber stamp, and honouring it collapses the whole cluster to zero.

One hygiene note did come out of this: `docs/complete-setup-guide.md` prints concrete, random-looking Keycloak client secrets as illustrative output. They are not live, but they read exactly like live ones, and a reader following the guide by copy-paste is the failure mode. Placeholders would cost nothing.

### 12× `logger-credential-leak` — the series' most reliable false positive

Every one is a log line that mentions a credential-shaped *word* while interpolating a username, a source id, or an HTTP status:

```python
logger.exception("Failed to refresh GitHub token for skill sync source %s", source_id)
logger.info("Rotated refresh token for user: %s", user_info["username"])
```

No credential value is logged in any of the twelve. This rule's running true-positive rate across the series remains approximately zero.

### 1× `unverified-jwt-decode` (`high`) — by design, and the design is good

This one deserved the look it got, because an unverified JWT decode inside an auth gateway is exactly where a real bypass would live. It is not one. The helper is documented with an explicit *"Do NOT use the returned claims to make authorization decisions"*, and — the part that matters — **both of its callers honour that**. Each uses the unverified claims only to *select* which issuer or which validator to route to, and then performs full cryptographic verification before anything is trusted. Verify-then-branch, not branch-then-verify.

The verification path underneath is stronger than most: the signing algorithm is pinned to RS256, the key id is pinned and foreign-`kid` tokens are rejected before decoding, issuer and audience are both enforced, and the two token classes the gateway mints are separated by an explicit `token_class` claim with a positive equality check on each path — so a browser session token cannot be replayed as an agent token, or vice versa. The comments explain *why* each check is positive rather than an exclusion. Credit where it is due.

## The finding that looked real and wasn't

The most instructive result of this scan is a finding that survived four rounds of verification and then died on the fifth.

The registry's CORS middleware allows origins by regex:

```
https?://(localhost(:[0-9]+)?|.*\.compute.*\.amazonaws\.com(:[0-9]+)?)
```

paired with `allow_credentials=True`. That second alternative is broader than it looks: `ec2-<ip>.compute-1.amazonaws.com` is the *public DNS name every EC2 instance receives*, so on its face the allowlist admits not "our deployment" but **every EC2 instance on the internet** — a credentialed cross-origin grant available to anyone who can start a `t2.micro`.

Rather than file that, it went through the differential against the real library:

```
starlette 1.6.0 — is_allowed_origin() uses regex.fullmatch()

ALLOWED  http://ec2-3-91-22-7.compute-1.amazonaws.com           creds=true
ALLOWED  https://ec2-3-91-22-7.eu-west-1.compute.amazonaws.com  creds=true
ALLOWED  http://localhost:3000                                  creds=true
denied   https://evil.example.com
denied   https://x.compute.y.amazonaws.com.evil.com
```

The probe **can** return no, and does — the regex is anchored and the obvious suffix trick fails. So the over-broad grant is real, and confirmed against the actual library rather than assumed.

And then it turns out not to matter. Every cookie this application sets — session, refresh, CSRF, and all four ephemeral OAuth-flow cookies — is `SameSite=Lax`. A cross-site `fetch()` from an attacker's EC2-hosted page therefore carries **no session cookie at all**, and `amazonaws.com`'s compute domains are on the Public Suffix List, so two EC2 hostnames are genuinely different *sites* rather than siblings. The credentialed grant is inert against the only principal that could have been stolen. Writes are independently protected by an HMAC double-submit CSRF middleware that fails closed whenever a session cookie is present.

The honest conclusion: **the regex should still be tightened** — it is far broader than its author intended, and it is one `SameSite=None` away from being a real cross-origin credential leak — but it is a hardening item today, not a vulnerability, and reporting it as one would have been wrong. This is the same "wildcard CORS + credentials" class this series has filed as a genuine finding against five other projects. Here the mitigation gate caught it. That gate exists precisely so the sixth one doesn't get filed on pattern-match alone.

*(One curiosity, recorded but not claimed: the unanchored `.*` also matches `https://evil.com/x.compute.y.amazonaws.com`, because `.` matches `/`. No browser will ever put a path in an `Origin` header, so this is not reachable — but it shows how much slack the pattern has.)*

## Also worth a line

- **`GF_SECURITY_ADMIN_PASSWORD=admin`** on the Grafana sidecar in `docker-compose.yml`, published to `${GRAFANA_PORT:-3000}` on all interfaces. It sits behind `profiles: [full]`, so a default `docker compose up` never starts it — which is why this is a note rather than a finding. Anyone running the full profile on a reachable host is publishing admin/admin.
- **`Access-Control-Allow-Origin: *`** in `frontend/nginx_http_only.conf`, which the frontend entrypoint installs unconditionally. No `Allow-Credentials` accompanies it, so no cookie ever rides along and the exposure is limited to what an anonymous caller could already fetch. Low.
- **Semgrep partial coverage:** 8 rules timed out, including two on `auth-server/src/auth_server/providers/entra.py` — one of the most security-relevant files in the repository. That file was read by hand as a result, and it is clean. This is exactly why the scanner emits a coverage meta-finding instead of letting a timeout render as silence.

## Patterns observed

Two things stand out about this codebase, and they pull in opposite directions.

The **architecture is default-deny in both layers**, which is unusual and correct. The auth middleware carves out an explicit list of public paths and authenticates everything else; the scope middleware then logs `"No rules match — denying"` and returns 403 rather than falling open. Most projects in this series get at least one of those backwards. Here the framework does its job so well that a route-inventory sweep for "handlers missing an authentication dependency" returned thirty-three candidates and **thirty-two of them were false alarms** — they simply obtain the caller through a differently-named dependency and then enforce a per-object ACL check. The sweep had to be rewritten to account for every identity idiom in the repo before it said anything true.

Which is the lesson: **on a codebase this disciplined, a name-matched sweep is nearly all noise, and the one survivor is the whole result.** The finding was not "this endpoint has no auth" — it has authentication, and RBAC, and both work. It was "this endpoint authenticates the caller and then never asks whether the caller owns the thing it is about," which is only visible by reading it against the sibling handler that does ask.

The other pattern is the CORS near-miss. Four independent verification steps all pointed at a real finding; the fifth — grep for the mitigation before flagging — retired it. That ordering is not optional, and it is the difference between a report a maintainer acts on and a report that costs them an afternoon.

## Notes on the tool

- **`run-shell-injection` needs trigger awareness.** Twenty-one high-severity findings, all retired by one grep for `pull_request_target`. The rule cannot currently distinguish "privileged workflow materializing untrusted code" from "fork PR running with a read-only token" — the exact distinction that decides whether the finding exists. A trigger-aware severity split would be the highest-value rule change this scan suggests.
- **`logger-credential-leak` fired 12 more times, 12 more false positives.** A downgrade to `low` is past due.
- **Object-level authorization is structurally invisible to every scanner in the stack**, and this is now a recurring shape: the defect is not a missing check but an *inconsistent* one, provable only against a sibling in the same file. The tooling backlog item is not a rule — it is that "tabulate sibling handlers that share an identifier and diff their guards" belongs in the manual pass.
- **Credit-the-defense paid again**, twice: `tartufo.toml` collapsed the secrets cluster, and one `SameSite` grep collapsed the CORS finding. Both were a single command.

## Disclosure timeline

- **2026-08-26** — Scan run at commit `3f7601248487`; 235 findings curated; the CORS candidate verified against Starlette 1.6.0 and retired on the `SameSite` gate; the authorization gap confirmed against the repo's own scope configuration and its guarded sibling handler.
- **2026-08-26** — Report routed privately to `security@ascendingdc.com` per the project's SECURITY.md, with a concrete patch. Public detail withheld.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/ascending-llc/jarvis-registry" \
  --reports-dir reports/ascending-llc-jarvis-registry \
  --min-severity medium --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) install separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme). The scanner output reproduces the 235 findings above. The one finding that matters is not among them: it came from reading two adjacent route handlers against each other, and its detail stays with the maintainers.
