---
layout: default
title: "Ontos-AI/knowhere: security scan"
description: "Security scan of Ontos-AI/knowhere: 129 findings at medium+, one real missing-authentication gap on an internal webhook disclosed privately (detail withheld), and a 68-CVE dependency table that all resolves to a single lockfile."
date: 2026-08-28
---

# Ontos-AI/knowhere — security scan

**Repository:** [Ontos-AI/knowhere](https://github.com/Ontos-AI/knowhere) — 2.7k★, Apache-2.0, a document-ingestion pipeline ("the memory layer between complex, dirty documents and AI agents") with a managed API at knowhereto.ai. Active two-maintainer team; a FastAPI/SQLAlchemy monorepo (`apps/api`, `apps/worker`, `packages/shared-python`).
**Commit scanned:** `b051c0813819` (HEAD of `main` at scan time)
**Scan date:** 2026-08-28
**Disclosure status:** **Private.** The project's SECURITY.md asks that vulnerabilities not be filed as public issues with exploit details, and — since GitHub Private Vulnerability Reporting is disabled here — that they be sent to the maintainers privately. One Medium-severity finding was written up and is being routed that way; the technical detail is **withheld from this post**, and only the finding *class* appears below. This page will be expanded once the maintainers resolve, or after a 90-day window.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 0 |
| High | 47 |
| Medium | 82 |
| Low | 0 |
| Info | 3 (filtered) |

**129 findings at `--min-severity medium`. After curation: one real defect — a missing-authentication gap on an internal webhook — and it is not in the list the scanners produced.** The 68-row dependency table, the 24 SQL findings, the workflow-injection cluster and the wildcard-CORS flag all retired on verification, for the reasons below. This is a carefully built codebase: the auth layer, the SSRF guard on outbound subscription confirmation, and the path-confinement on file serving are all done right. The one gap is a webhook whose signature checks were stubbed out and never wired in.

## The finding (class only, detail withheld)

**Class:** missing authentication on a state-changing internal webhook — CWE-306, with
CWE-347 (improper signature verification) in the supporting code.

The shape, without the specifics: a storage-event webhook advances document-ingestion jobs.
It is mounted on the public API router — the `/internal` in its path is a tag, not a network
boundary, and the deployment docs publish its live URL. The dispatcher offers three
provider-specific branches, each nominally gated by a signature or token check. But the
verifier for the production provider is **never called** (and is a `return True` stub in any
case); a second provider's verifier is an unimplemented `return True` stub; and the third's
token check is conditional on the request in a way the caller controls, so it too can be
sidestepped. The net effect is that the endpoint authenticates nothing on the path a real
deployment uses.

**What makes this a defect rather than a design choice is the codebase's own contract.** Every
mutating route elsewhere in this API — create/archive documents, create jobs, manage API keys,
manage billing, manage webhook secrets — carries an explicit `Depends(require_write_permission)`
guard. I tabulated all 40-odd routes across v1 and v2; the write guard is applied with total
consistency everywhere *except* this webhook. The project clearly intends state changes to be
authenticated. This endpoint changes state and isn't. That asymmetry is not something a rule
can see — each branch is individually well-formed FastAPI — but it is decisive, because the
codebase itself supplies the standard.

The finding was verified by execution — a differential that shows a *wrong* credential being
correctly rejected while an *absent* one is silently accepted — and a concrete fix (call a
verifier on every branch, fail closed on the fall-through, delete the stubs) went out with the
private report.

## What the scanners flagged — and why none of it survived

### 68 dependency CVEs (Trivy) — one lockfile, wearing two hats

Trivy's headline was 68 vulnerabilities (13 High) against `apps/worker/requirements.txt`:
Pillow, pypdf, aiohttp, starlette, PyJWT, urllib3, cryptography and friends. The first
instinct is a two-install-paths story — the repo also ships `uv.lock`, which Trivy scanned
separately and found **clean** (0 vulns). But the disagreement is an artifact, not a divergence:
`apps/worker/requirements.txt` is a `uv export` of the very same lock (`# uv export --no-hashes
--no-dev -o requirements.txt` in its header), and both `Dockerfile.api` and `Dockerfile.worker`
install from `pyproject.toml` + `uv.lock` via `uv` — **neither Dockerfile ever reads
`requirements.txt`.** Trivy resolves the pinned `==` floors in the exported file and matches
advisories; Trivy's `uv.lock` parser resolves the same versions but did not surface the same
advisories in this run. Same bytes, two verdicts.

That does *not* make the CVEs fictional — the versions are real and shipped — but it reframes
them: this is one routine "bump the lockfile" task, not a security incident, and every one of
the 68 has a fix version available. The two I chased into the code because they touch this
app's actual trust boundaries both retired:

- **PyJWT algorithm-confusion (CVE-2026-48526, forge an HS256 token with the public key).**
  The verifier here *does* list `HS256` alongside `RS256`/`EdDSA` in one allowlist while
  resolving asymmetric JWKS keys — the classic confusion setup. But it passes the *unwrapped*
  `signing_key.key` (a `cryptography` key object), and PyJWT's `HMACAlgorithm.prepare_key`
  rejects asymmetric key objects — a guard that predates the CVE, whose actual vector is passing
  the *PyJWK wrapper*. Not reachable here. Bump PyJWT anyway for the detached-JWS DoS and the
  allowlist-bypass fixes, but the auth path is not exploitable.
- **Starlette Host-header / UNC-path SSRF (CVE-2026-48818, -48710).** The UNC vector is
  Windows-only `StaticFiles`; this runs on Alpine/Linux containers. Bump on the next cycle.

### 24 SQL findings (`sqlalchemy-execute-raw-query`, `avoid-sqlalchemy-text`, `formatted-sql-query`) — parameterized, or migrations

The recurring cluster of this whole series. Ten of the 24 are in Alembic migrations and the
test-contract harness — DDL with no user input, the standard false-positive tier. The eight in
live retrieval/telemetry code (`nav_knowhere.py`, `channels.py`, `aggregates.py`) f-string only
*identifiers* and *SQL structure* into the query — column names, `POSITION(...)` expressions, a
window-start clause — while every *value* is bound (`%s` / `:param`). The one that could have
been real, `search_field` interpolated into a `WHERE` clause, is gated by an explicit allowlist
that `raise`s on anything outside `{"content_search_text", "path_search_text"}`
(`channels.py:295`). Verified real defense, not luck.

### 3 GitHub Actions shell-injection (`high`) — wrong trigger

`run-shell-injection` fired on `${{ github.event_name }}` and step-output interpolation inside
`run:` steps in `build-images.yml`. That workflow triggers on `push` to `staging`, `release`,
and `workflow_dispatch` — all of which already require write access. There is no
`pull_request_target` anywhere in the repo, and the interpolated values are the event name and
internal step outputs, not attacker-controlled PR content. `env:` indirection is worth doing as
hygiene; it is not a security ticket.

### 30 mutable action tags (`medium`) — the series' most common class, again

`actions/checkout@v4` and friends by mutable tag rather than pinned SHA. Real supply-chain
hygiene, low priority, one pinning pass closes it. It is the single most frequent finding across
this entire scan series.

### 1 wildcard CORS with credentials (`medium`) — inert, because there are no cookies

`cors.py` sets `allow_origins=["*"]` with `allow_credentials=True` — normally the exact
credentialed-CORS smell. But this API carries **no cookies**: a repo-wide grep for
`cookie`/`set_cookie`/`SameSite` returns nothing, and authentication is `Authorization`-header
only (API key or Dashboard JWT). A browser will not attach an `Authorization` header
cross-origin on the strength of a CORS grant, so the wildcard buys an attacker nothing here.
Worth scoping the origins before any cookie-based session is ever introduced — reported as
hardening, not a vulnerability.

### 2 dynamic imports, 1 SHA-1 — all benign

`importlib.import_module()` in the http and redis packages resolves only through a hardcoded
`_EXPORT_MODULES` dict (a lazy-export `__getattr__` idiom), never user input. The SHA-1 is a
cache-filename digest in `page_pdf_crop.py`, not a signature. Both are semgrep's audit rules
doing their job and both are false positives in context.

## Patterns observed

This is the well-built-codebase case, and the interesting part is *where* the one gap sat. The
authentication design is good: a single `require_write_permission` dependency, applied to every
state-changing route with a consistency you could set a watch by; a JWT verifier that
structure-checks before it trusts, unwraps its JWKS keys to defeat algorithm confusion, and
pins an explicit algorithm allowlist; an outbound-URL validator with IP pinning that closes the
SSRF on subscription confirmation; path confinement that resolves-then-checks-containment
against a hardcoded allowlist. A reader who scores this API on its authenticated surface comes
away impressed.

The gap was in the plumbing next to the impressive machine — a webhook that speaks to storage
providers, where the verification functions had been scaffolded (`verify_sns_signature`,
`verify_oss_signature`) and then left as `return True` stubs, one of them with a
`# TODO: implement` still in place, and one of them never called at all. The lesson that keeps
recurring in this series: the vulnerability is rarely in the part the authors were thinking hard
about. It is in the boring inbound path they scaffolded, meant to come back to, and shipped. The
way you find it is not a better rule; it is tabulating every handler of a given kind and asking
which one differs from its siblings — here, the one inbound state-changer with no guard among
forty that have one.

## Notes on the tool

- **The two-install-paths heuristic needs a third outcome: "same lockfile, two representations."**
  AI PatchLab's `dependency-scan-unaudited-lockfile` meta-finding correctly flagged that
  `uv.lock` exists and pip-audit could not read it — but the sharper truth here was that
  `requirements.txt` is a *derived export* of that same lock, so the "two paths" framing
  over-warns. A future check could diff the exported pins against the lock and, when they match,
  say "one dependency set, two files" instead of implying divergence. Backlog item.
- **Windows long-path clone failure.** `scanner/git_source.cloned_repo` clones without
  `core.longpaths=true`; this repo's deep `demo_documents/**/page_citation_assets/` tree
  overran `MAX_PATH` and the checkout failed with "unable to checkout working tree", leaving no
  report. Re-running the clone with `git -c core.longpaths=true` fixed it. The cloner should set
  that config unconditionally on Windows. Backlog item.
- Semgrep coverage was clean this run — the 42 reported errors were all `PartialParsing` on
  non-Python files (a workflow YAML, an HTML doc, a shell script), not skipped Python.

## Disclosure timeline

- 2026-08-28 — scan run; one Medium finding curated and verified by execution.
- 2026-08-28 — private disclosure drafted for the maintainers (PVR disabled; routed to the
  maintainer contact per SECURITY.md's fallback). Detail withheld from this page.

## Reproduce

```bash
git -c core.longpaths=true clone https://github.com/Ontos-AI/knowhere /tmp/knowhere
python scanner/run_scan.py --repo /tmp/knowhere --reports-dir ./reports/ontos-ai-knowhere \
  --min-severity medium --ignore-samples
```
