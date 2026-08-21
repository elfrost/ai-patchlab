---
layout: default
title: "homeassistant-ai/ha-mcp: security scan"
description: "Security scan of homeassistant-ai/ha-mcp: 65 findings, zero real in-scope items; a strict-norm repo whose maintainer published a precise threat model"
date: 2026-05-29
---

# homeassistant-ai/ha-mcp — security scan

**Repository:** [homeassistant-ai/ha-mcp](https://github.com/homeassistant-ai/ha-mcp) — 3.2k★, MIT, an (unofficial) Home Assistant MCP server that exposes HA control to MCP clients over stdio / web / SSE / OAuth.
**Commit scanned:** `7352ce88ef59` (HEAD of `master` at scan time)
**Scan date:** 2026-05-29
**Disclosure status:** **Post-only — no issue filed.** ha-mcp ships a real, detailed `SECURITY.md` with an explicit threat model and a private reporting channel (a strict-norm repo by our [filing methodology](dstackai-dstack.html#maintainer-response-and-lessons)). Curation found nothing real and in-scope, so there was nothing to disclose privately and no grounds for a public issue. This write-up is commentary only.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 51 |
| Medium | 13 |
| Low | 0 |
| Info | 0 (filtered) |

**65 total findings. After curation: zero real, in-scope, exploitability-shaped items. Every finding is either a test fixture, an intentional public demo credential, a finding the maintainer's published threat model explicitly addresses as by-design, CI/container hardening outside the stated runtime scope, or a static-analysis false positive.**

This is the most interesting *clean* scan in the series so far — not because the codebase is small (it isn't; ~8.5 MB of Python), but because the maintainer **published a precise threat model first**, and the scan confirms the code matches it. Scanning a repo like this is the clearest demonstration of why curation, not raw tool output, is the product: the scanner's "1 critical, 51 high" headline is, on inspection, entirely accounted for.

## Reading the scan against a published threat model

ha-mcp's [`SECURITY.md`](https://github.com/homeassistant-ai/ha-mcp/blob/master/SECURITY.md) states up front what is and isn't a vulnerability. Several of those statements pre-empt exactly the rules that fired:

| Scanner flagged | Their threat model says | Verdict |
|---|---|---|
| `exec-detected` in `src/ha_mcp/utils/python_sandbox.py:386` | "`python_transform` expressions are trusted code from a trusted client. The sandbox prevents accidental mistakes, not an adversarial party" — with an explicit "not a security boundary" note in the file | **By-design** |
| 7× `insecure-websocket` (`src/ha_mcp/client/websocket_client.py`) | "Local network is the trusted zone for standard mode" — `ws://` to a LAN Home Assistant is the intended connection | **By-design** |
| 1× `directly-returned-format-string` in `homeassistant-addon-webhook-proxy/mcp_proxy/oauth.py:184` | The function is a base-URL *builder* (`return f"{scheme}://{host}"`), not an HTML view; its docstring documents the Host-header-poisoning mitigation (operator `public_base_url` wins) | **FP** (not reflected XSS) |

Their `SECURITY.md` even enumerates the **in-scope** classes: auth bypass, OAuth-mode XSS/SSRF/open-redirect/credential-exfil on the consent or token endpoint, unintended info disclosure via API responses, privilege escalation in the MCP tool surface, and dependency vulns with a credible exploit path. I curated specifically for those — and the scan surfaced none of them.

## The "1 critical" and the secrets, curated

### The critical is a false positive

**Trivy, `Dockerfile:68` — "secrets passed via build-args or envs".** The flagged lines are:

```dockerfile
ARG BUILD_VERSION=""
ENV HA_MCP_BUILD_VERSION=${BUILD_VERSION}
```

`BUILD_VERSION` is a dev version string (e.g. `7.3.0.dev390`), surfaced in startup logs and bug reports — not a secret. Trivy's rule fires on any `ARG → ENV` propagation; the content here is benign and documented in a comment right above. **FP.**

### All 26 "secrets" are fixtures, docs, or an intentional demo token

| Where | What | Verdict |
|---|---|---|
| `tests/initial_test_state/.storage/auth*` (12) | Home Assistant test-state fixtures | **FP** — fixture auth store |
| `tests/.env.test`, `tests/test_constants.py`, `tests/addon/...`, `tests/src/unit/...` | Test JWTs / keys | **FP** — test constants |
| `tests/src/unit/test_tools_bug_report.py:573` — a `ghp_…` GitHub PAT | Inside `test_redacts_key_value_credentials`, the case `("token=ghp_AbCdEf…", "ghp_AbCdEf")` | **FP — and a security *feature* under test**: it asserts the bug-report tool *redacts* tokens |
| `src/ha_mcp/config.py:27` — `DEMO_TOKEN` (a real JWT) | Explicitly labelled token for a **public** demo server (`login: mcp/mcp, resets weekly`) | **By-design** — intentional throwaway public-sandbox credential |
| `site/src/layouts/Layout.astro`, `homeassistant-addon-webhook-proxy/DOCS.md` | Docs-site key / doc examples | **FP** — documentation |

The `github-pat` hit is the nicest detail in the scan: gitleaks flagged a dummy token that exists *only* to test the project's own credential-redaction logic.

## The genuinely-real-but-out-of-scope tail

These are real best-practice items, but they sit outside ha-mcp's stated runtime threat model (they're CI / container packaging, not the MCP/OAuth attack surface the `SECURITY.md` scopes):

- **12× `run-shell-injection`** in `.github/workflows/*` — the recurring `${{ }}`-into-`run:` class. Standard `env:`-indirection fix. Worth doing, but it's CI hardening, and filing it on a strict-norm repo as a grouped issue is exactly what the [dstack lesson](dstackai-dstack.html#maintainer-response-and-lessons) says not to do.
- **3× Dockerfile `missing-user` + 3× Trivy "image user should not be root"** — container runs as root; add a non-root `USER`. Packaging hardening.

## Patterns observed

**A published threat model is the highest-leverage thing a maintainer can do to make a security scan productive.** ha-mcp's `SECURITY.md` turned what would otherwise be a 65-finding triage marathon into a 20-minute confirmation pass: most "scary" findings had a pre-written, specific, *credible* by-design rationale. This is the opposite of the [HolmesGPT](holmesgpt-holmesgpt.html) 2,143-finding deluge — same "mostly noise" outcome, but here the maintainer did the explaining in advance.

**Strict-norm + nothing-in-scope is the cleanest case for post-only.** No public issue (the repo signals per-vuln norms), and no private disclosure either (nothing in-scope was real). The honest output is a write-up that engages seriously with their threat model — which is more respectful, and more useful to readers, than manufacturing an issue to look productive.

**This scan validates the two data-driven scanner changes shipped on 2026-05-28.** The `logger-credential-leak` rule fired 7× and every hit landed at **low** confidence (its new downgrade — 6/6+ FPs across the series), correctly deprioritized. `--ignore-samples` was on by default. Neither changed the verdict, but both behaved as designed on a real, large target.

## Notes on the tool

- **Gitleaks on Home Assistant test fixtures is a reliable FP generator.** The `.storage/auth*` files are HA's own auth-store format, full of high-entropy fixture values. This is the same fixture-secret shape as [openllmetry's VCR cassettes](traceloop-openllmetry.html) — a `tests/fixtures/**` default-suppression (alongside the new `--ignore-samples`) would zero out 20+ of these.
- The `directly-returned-format-string` Flask rule is a useful reminder that "returns an f-string" is not "renders HTML" — the rule can't tell a URL-builder from a view, which is precisely the judgment curation supplies.

## Disclosure timeline

- **2026-05-29** — Scan run at commit `7352ce88ef59`; findings curated against the repo's published `SECURITY.md` threat model. Quality gate: no real in-scope item → no issue, no private report. Post-only.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/homeassistant-ai/ha-mcp" \
  --reports-dir reports/homeassistant-ai-ha-mcp \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
