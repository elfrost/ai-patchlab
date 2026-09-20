---
layout: default
title: "hydropix/TranslateBooksWithLLMs: security scan"
date: 2026-09-19
---

# hydropix/TranslateBooksWithLLMs — security scan

**Repository:** [hydropix/TranslateBooksWithLLMs](https://github.com/hydropix/TranslateBooksWithLLMs)
**Commit scanned:** `1147b27`
**Scan date:** 2026-09-19
**Disclosure status:** withheld — reported privately via GitHub PVR ([GHSA-g7qf-f9xp-wqmp](https://github.com/hydropix/TranslateBooksWithLLMs/security/advisories/GHSA-g7qf-f9xp-wqmp), triage). The finding is described here at class level only; the exact endpoint set and the working exploit stay withheld until the advisory resolves.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 9 |
| Medium | 44 |
| Low | 0 |
| Info | 2 |

**Total findings:** 55 above the medium floor (2 are scan-coverage meta findings). One real, reported privately; **zero of the 53 tool findings survived curation.**

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `ran` | Ran without reporting a coverage problem. |
| `ai-security-review` | `not_run` | AI security review is disabled (ADR-010) |

**Coverage complete:** no. Semgrep reported 17 errors, **0 of them rule timeouts** — every one is a syntax / partial-parse error on a *non-Python* file: three benchmark YAML data files (`benchmark/…/languages/*.yaml`), four GitHub Actions workflows, the `deployment/Dockerfile`, and the `translation_interface.html` template. **No first-party Python module was skipped** — which matters, because the real finding lives in the Python application code, and that code was fully examined. This is the opposite of a coverage blind spot: the tool opened the app and found nothing, and the gap is in config/data files a Python rule could not parse anyway.

## The finding (class only)

The one real issue is **not** in the finding list any tool produced. It is a property of the app's authentication design, and it is worth reading precisely because the maintainer **did the hard part right**.

This is a local Flask + Socket.IO app that binds `127.0.0.1` by default. Issue #210 hardened it against the obvious drive-by attack — the wildcard CORS is gone, and a per-process, 256-bit token (`X-API-Token`) now gates every `/api/` route and the WebSocket handshake. Against an ordinary web page you visit, that is **sound**: the token comparison is constant-time, the token is generated fresh per process and never persisted, and a foreign origin can neither read it nor read API responses. I confirmed the gate holds — an unauthenticated cross-origin call gets a clean `401`.

The class, stated without a recipe: **a correct per-session-token defense with no `Host`-header validation, so the route that *delivers* the token is readable under DNS rebinding.** The token has to be handed to the legitimate single-page app somehow; it is embedded in the HTML of the index route, which is (necessarily) exempt from the token gate. Nothing in the server validates the `Host` header, so after a DNS rebind the victim's browser — now sending the attacker's own domain as `Host` but connected to `127.0.0.1` — makes a **same-origin** read of that page, lifts the token, and drives the whole authenticated surface cross-origin. It is the [claude-tap](scans/liaohch3-claude-tap.html) desktop-loopback shape from a new angle: there a correct rebinding guard was wired to the wrong *subset of routes*; here the token defense is wired to *all* the right routes, but its own credential-delivery channel is reachable because the one primitive that would stop rebinding — a `Host` check — is absent. The [jupyter-mcp](scans/datalayer-jupyter-mcp-server.html) inverse again: same ingredients, opposite outcome, and the whole difference is one missing check.

What made it reportable rather than theoretical: it was **verified against the real server with a control**. A request bearing a foreign `Host` returns the token-carrying page (it could have returned a 400/421 and did not); the same request *without* the token returns `401` (proving the gate is genuinely enforced and that token-knowledge is the only barrier); and the stolen token then authorizes the API. The probe could have said no at two points and said yes at both. And the fix is one the project has **already written the hard half of** — its LLM-endpoint SSRF guard ships an `is_local_host()` predicate that accepts loopback, LAN, Docker, mDNS and tailnet names and rejects a public FQDN; the same predicate, applied syntactically to the request `Host` (never *resolving* it — the attacker controls that resolution), closes the channel without breaking the LAN/Docker access the project deliberately supports. The report proposes exactly that, so it costs no threat-model argument.

## Patterns observed

**This is one of the better-defended local apps in the series, and the finding is a single missing primitive, not sloppiness.** The evidence is everywhere in the auth layer. The LLM-endpoint validator is genuinely careful: it permits the operator's own network on purpose, documents *why* in a long module docstring, and then enforces the crucial companion rule at every call site — an endpoint the client chooses is treated as an override and the server's stored API key is **never** paired with it, so the app cannot be turned into a credential-exfiltration relay (`allow_env_fallback=False`, applied in four blueprints, with the sentinel resolution centralised after a real past bug from copy-paste divergence). The file routes resolve-and-contain with `Path.resolve()` + `relative_to`, not a string `startswith`, so path traversal on read/delete is closed correctly. The WebSocket handshake checks the same token. None of that is common in a hobbyist-facing self-hosted tool.

The finding is the [contract-versus-artifact](scans/vexa-ai-vexa.html) shape with a [docstring oracle](scans/hkuds-openopc.html): the auth module states plainly that *"same-origin delivery means a foreign page cannot read"* the token and that *"a cross-origin attacker can neither read the token nor forge the custom header."* Both clauses are true under the same-origin policy and **false under rebinding**, and there is no code that makes them true — the claim rests entirely on a browser invariant the attack is designed to break. When a security function documents the property it guarantees, that documentation is a free test to run against the code, and here it points straight at the gap the finding occupies.

## Notes on the tool

**Zero of the 53 tool findings were real, and the curation is the usual catalogue.** The nine Highs: six are the [SQL-identifier false positive](scans/mnemosyne-oss-mnemosyne.html) on its recurring path — every `UPDATE … SET {', '.join(assignments)}` builds its fragments from hardcoded `"col = ?"` literals or schema-derived column names, with every value bound as `?` (the `DELETE … IN (…)` even carries a comment explaining the placeholder count is `len(ids)` and the values are parameters); two are `run-shell-injection` in CI, but one is `${{ github.base_ref }}` on a plain `pull_request` trigger and the other `${{ github.ref_name }}` on a `workflow_call`, neither an untrusted-event context — the [trigger decides the severity](scans/lightseekorg-tokenspeed.html); and the last is Trivy's "image runs as root" on the Dockerfile, real hardening advice, not a vulnerability. The 44 mediums are the same texture: 26 mutable-action-tag rows (CI hygiene), four `direct-use-of-jinja2` with `autoescape=False` in an **offline benchmark-wiki generator** rendering author-controlled data to local HTML, two SHA-1 hits that are a **truncated benchmark evaluation ID** (`make_eval_id`, non-crypto), a `secure`-cookie flag on a locale cookie that holds the string `"en"` over localhost HTTP, two client-side prototype-pollution hits on the SPA's own dotted-key state store, and container/SRI hardening. Gitleaks found nothing. pip-audit and Trivy agreed on the dependency surface with **no advisories** across the 55 resolved packages, and the `dependency-scan-unaudited-lockfile` meta-finding did **not** misfire this time (there is no orphaned lockfile — `requirements.txt` is the only manifest, and it was read).

The tool's real limitation here is the one it has every time the finding is architectural: **no rule can represent "a correct token defense with no `Host` check."** The absence of a validation is not a pattern to match, and the composition — token-exempt index route + no Host allowlist + predictable loopback port — spans three files that are each individually fine. That is the sixteenth-or-so time in this series the real finding was invisible to the scanners and visible only by reading the auth boundary against the app's own documentation.

## Disclosure timeline

- 2026-09-19 — scan run; finding verified against the running server (with negative and positive controls)
- 2026-09-19 — reported privately via GitHub PVR ([GHSA-g7qf-f9xp-wqmp](https://github.com/hydropix/TranslateBooksWithLLMs/security/advisories/GHSA-g7qf-f9xp-wqmp), triage)
- 2026-09-19 — public post (this page), finding withheld at class level pending the advisory

## Reproduce

```bash
git clone https://github.com/hydropix/TranslateBooksWithLLMs /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/hydropix-translatebookswithllms --min-severity medium
```

---

## More from this series

- **Next scan:** [TencentCloud/Octop](tencentcloud-octop.html) — 2026-09-20, 1 real — withheld
- **Previous scan:** [experientiallabs/experiential](experientiallabs-experiential.html) — 2026-09-15, 1 real — withheld
- [Every scan in the series]({{ '/' | relative_url }}) — 107 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 24 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — 40 of them, published as they were
