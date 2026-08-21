---
layout: default
title: "harbor-framework/harbor: security scan"
description: "Security scan of harbor-framework/harbor: 570 findings, and the count means almost the opposite of what it looks like: 464/570 (81%) and all 10 criticals are"
date: 2026-06-15
---

# harbor-framework/harbor — security scan

**Repository:** [harbor-framework/harbor](https://github.com/harbor-framework/harbor) — 2.5k★, Apache-2.0, a framework for running agent evaluations across benchmarks. A monorepo: harbor's own core (`src/harbor/`, `packages/`) plus **84 vendored benchmark adapters** under `adapters/*`, each a packaged upstream benchmark (swe-bench, gaia2, mmau, swesmith, …) with its own `uv.lock` and Dockerfile environment.
**Commit scanned:** `387625f07b4b` (HEAD of `main` at scan time)
**Scan date:** 2026-06-15
**Disclosure status:** Public courtesy issue filed — a single *structural* question about the sandbox-isolation threat model for vendored environments, not a 570-finding enumeration. Harbor's own core is well-built; the entire critical surface lives in the vendored benchmark adapters.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 10 |
| High | 333 |
| Medium | 227 |
| Low | 0 |
| Info | 0 (filtered) |

**570 findings — and the number means almost the opposite of what it looks like.** An ownership split is the entire story: **464 of 570 findings (81%) are in vendored `adapters/*`** (84 packaged upstream benchmarks), and **all 10 criticals are vendored adapter dependencies** (`adapters/*/uv.lock`). Harbor's own code (`src/harbor/` + `packages/`, 34 findings) has **zero criticals** and — on inspection — does the dangerous things correctly. The headline "10 critical / 333 high" is a property of the benchmark environments harbor bundles, not of harbor.

## Harbor's own core: built right

Before the vendored pile, the part that matters most — harbor's own code — is clean on every pattern that fired:

- **Tar extraction uses `filter="data"` everywhere.** All `tarfile.extractall` calls in `src/harbor/` (`environments/base.py:838,938`, `environments/tar_transfer.py:72`, `download/downloader.py:177`) pass `filter="data"` — the Python 3.12 safe-extraction mode that blocks the [CVE-2007-4559](pixeltable-pixeltable.html) path-traversal / symlink class. `downloader.py` even carries an explanatory comment. This is the sandbox/environment-transfer layer — exactly where you'd worry about malicious tarballs — and it's done correctly. (Contrast with [pixeltable](pixeltable-pixeltable.html), where the same rule fired on an *unguarded* call.)
- **The two "secrets" in core are Supabase publishable keys.** `src/harbor/auth/constants.py:7` and `registry/client/harbor/config.py:11` hold `sb_publishable_…` keys. Supabase's `sb_publishable_` prefix (the public "anon" key) is *designed* to ship in client code — it's gated by Row-Level Security on the backend, not a secret. Same intentional-public-credential class as [deepteam's PostHog `phc_` key](confident-ai-deepteam.html). FP.
- **The core `shell=True` is the by-design sandbox-execution layer.** `environments/singularity/server.py:140` (`shell=True, executable="/bin/bash"`) runs commands inside a Singularity HPC container; `packages/rewardkit/.../criteria/_command.py:23` runs an operator-defined reward command with a `timeout=30`. An eval harness running commands inside its sandboxes is the entire point — this is the [agent-execution-by-design class](vrsen-agency-swarm.html), bounded here by the container boundary and a timeout.

So harbor-core earns a clean bill on the exploitability-shaped patterns. That reframes the other 536 findings.

## The vendored surface: where the criticals actually are

All 10 criticals live in `adapters/*/uv.lock` — the pinned dependency sets of vendored upstream benchmarks:

| CVE | Package | Adapter(s) | Class |
|---|---|---|---|
| [CVE-2026-7304](https://github.com/advisories?query=CVE-2026-7304) | `sglang` | swesmith | **Unauthenticated RCE** via `--enable-custom-logit-processor` |
| [CVE-2026-3059](https://github.com/advisories?query=CVE-2026-3059) | `sglang` | swesmith | Multimodal-generation vuln |
| [CVE-2026-3060](https://github.com/advisories?query=CVE-2026-3060) | `sglang` | swesmith | Encoder parallel-disaggregation vuln |
| [CVE-2026-42208](https://github.com/advisories?query=CVE-2026-42208) | `litellm` | ml_dev_bench, mlgym-bench, mmau | Proxy SQL data access (proxy-surface — see [reachability note](q00-ouroboros.html#patterns-observed)) |
| [CVE-2025-14009](https://github.com/advisories?query=CVE-2025-14009) | `nltk` | dacode, kramabench | Zip Slip → code execution |
| — | Dockerfile | cooperbench ×2 | Multiple `ENTRYPOINT` instructions |

Plus the high/medium tail: **86 "image runs as root"** Dockerfile findings spread across ~40 adapter environments, 35 `apt-get` missing `--no-install-recommends`, 20 `:latest`-tag pins, a `urllib3`/`aiohttp`/`requests`/`starlette` web tail, 14 `pickle.load` sites (all in vendored adapter code), and 10 `tarfile-extractall` (the vendored ones, where the core ones were already `filter="data"`-guarded).

The structural reality: **harbor vendors 84 third-party benchmark environments, and inherits each one's dependency drift and container-hygiene debt.** These environments run *inside harbor's eval sandboxes* — which, for an agent-evaluation harness, is a trust boundary that runs arbitrary agent code by design. So the applicability of "an unauthenticated SGLang RCE in swesmith's env" depends entirely on harbor's isolation model: if the sandbox is the security boundary and a benchmark environment is assumed potentially-hostile, these are contained; if anything trusts a benchmark env's integrity, they're a real escalation surface. **That's the one question worth asking the maintainers** — and it's what the courtesy issue leads with, rather than enumerating 570 findings (the [dstack-rejection failure mode](dstackai-dstack.html#maintainer-response-and-lessons)).

## Patterns observed

**"570 findings, 10 critical" is the most misleading raw headline in the series — and ownership analysis is what corrects it.** This scan is the strongest argument yet that the raw scanner count is not just an over- or under-count (the [SCA-reachability](q00-ouroboros.html) and [completeness-sweep](54yyyu-zotero-mcp.html) lessons) but can be *misattributed*: 81% of findings and 100% of criticals belong to vendored third-party code, not to the project being scanned. A curated report that didn't separate `src/harbor/` from `adapters/*` would have told harbor's maintainers they have 10 critical vulnerabilities — when their own code has none. The first curation step on any monorepo must be an **ownership split** (first-party vs vendored/third-party paths), before any severity reasoning.

**An eval harness's vendored benchmark environments are a genuinely novel surface shape.** Unlike a `docs/` lockfile ([deepteam](confident-ai-deepteam.html)) or an `examples/` subtree ([Klavis](klavis-ai-klavis.html)) — which are out-of-runtime — these vendored environments *are run*, but inside a sandbox whose entire purpose is to contain untrusted agent behaviour. The right framing isn't "out of scope" (they execute) nor "in scope" (they're third-party and sandboxed) — it's "what does your isolation model assume?" This is a threat-model question, not a finding, and it's the highest-value thing a security review adds on a target like this.

**Harbor-core is a second "what right looks like" reference for tar extraction.** Where [pixeltable](pixeltable-pixeltable.html) had an unguarded `extractall` (a real finding) and [zotero-mcp](54yyyu-zotero-mcp.html) had a hand-rolled member-validation guard, harbor uses the modern `filter="data"` everywhere — the cleanest of the three approaches, with a comment explaining why. The recurring `tarfile-extractall-traversal` rule has now fired across the full spectrum from "exploitable" to "exemplary," which is the entire case for reading the call site rather than the rule count.

## Notes on the tool

- **The 2026-06-11 UTF-8 fix was load-bearing here**: harbor is a 9.4 MB-Python monorepo and the scan would previously have been at risk of the cp1252 crash. `reports/harbor-framework-harbor/raw/semgrep.json` came back at 645 KB (healthy) with zero scanner meta-errors; the count is real, not a silent truncation.
- **The single most valuable scanner refinement this scan suggests is an ownership/vendored-path dimension.** A scanner that tagged each finding `first-party` vs `vendored` (heuristics: `adapters/`, `vendor/`, `third_party/`, `*/template/environment/`, a path containing its own `uv.lock`/`package.json` distinct from the repo root) would turn "570 findings, 10 critical" into "34 first-party (0 critical), 536 vendored (10 critical)" automatically — the exact split that took manual path analysis here. This is a higher-leverage feature than any single rule.
- The `litellm` criticals are once again Proxy-surface ([the recurring note](q00-ouroboros.html#patterns-observed)); whether the vendored benchmark envs run the LiteLLM Proxy is a per-adapter question, further bounded by the sandbox.

## Disclosure timeline

- **2026-06-15** — Scan run at commit `387625f07b4b`; `semgrep.json` verified healthy (645 KB). Ownership analysis: 464/570 findings and 10/10 criticals in vendored `adapters/*`; harbor-core (34 findings) clean on every exploitability-shaped pattern (tar `filter="data"`, Supabase publishable keys, by-design sandbox subprocess).
- **2026-06-15** — Public courtesy issue [#1929](https://github.com/harbor-framework/harbor/issues/1929) filed on harbor-framework/harbor with the single structural question (sandbox-isolation threat model for vendored benchmark environments, with the SGLang unauthenticated-RCE pin + run-as-root Dockerfiles as the concrete example), and a credit to the well-built core. No 570-finding enumeration.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/harbor-framework/harbor" \
  --reports-dir reports/harbor-framework-harbor \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
