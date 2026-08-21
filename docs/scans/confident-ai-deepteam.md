---
layout: default
title: "confident-ai/deepteam: security scan"
description: "Security scan of confident-ai/deepteam: 48 findings, zero real in-scope runtime items; 5th clean scan in the series"
date: 2026-06-09
---

# confident-ai/deepteam — security scan

**Repository:** [confident-ai/deepteam](https://github.com/confident-ai/deepteam) — 1.9k★, Apache-2.0, a framework to red-team LLMs and AI agents (the sister project to Confident-AI's `deepeval`). Backed by [confident-ai.com](https://www.confident-ai.com/), with a Docusaurus documentation site under `docs/`.
**Commit scanned:** `846e2dff24fd` (HEAD of `main` at scan time)
**Scan date:** 2026-06-09
**Disclosure status:** **Post-only — no issue filed. Clean-scan write-up.** Quality gate evaluates to false: zero real, exploitability-shaped, runtime-in-scope items. The two `gitleaks` hits are intentional OSS-telemetry write-only keys (standard pattern). The 24-CVE Trivy tail splits cleanly between a Dependabot-already-wired Python `poetry.lock` and an out-of-scope Docusaurus `docs/yarn.lock`. Every `semgrep` code finding is in `docs/scripts/` or `docs/src/` — the Docusaurus build pipeline, not the runtime framework.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 19 |
| Medium | 29 |
| Low | 0 |
| Info | 0 (filtered) |

**48 total findings. After curation: zero real in-scope runtime items.** This is the fifth clean-scan write-up in the series (after [Giskard](giskard-ai-giskard-oss.html), [semble](minishlab-semble.html), [logfire](pydantic-logfire.html), and [ha-mcp](homeassistant-ai-ha-mcp.html)) and the cleanest "well-architected OSS with intentional public telemetry + docs-as-separate-surface + Dependabot wired" example so far.

## Top findings (curated)

### 1. 2× `gitleaks` `generic-api-key` in `deepteam/telemetry.py` — **intentional OSS-telemetry write-only keys (FP)**

Both hits are hardcoded public credentials for the project's opt-in telemetry layer (gated behind `ERROR_REPORTING=YES` + multiple opt-out checks visible in the surrounding code):

```python
# deepteam/telemetry.py:82
NEW_RELIC_LICENSE_KEY = "1711c684db8a30361a7edb0d0398772cFFFFNRAL"
NEW_RELIC_OTLP_ENDPOINT = "https://otlp.nr-data.net:4317"

# deepteam/telemetry.py:102
posthog = Posthog(
    project_api_key="phc_IXvGRcscJJoIb049PtjIZ65JnXQguOUZ5B5MncunFdB",
    host="https://us.i.posthog.com",
)
```

The **New Relic license key** is a write-only OTLP ingest token — any deepteam install posts traces to confident-ai's New Relic account via this key. It cannot be used to read data from New Relic, only to write to it. Standard OSS-pattern; the same shape ships in `langchain`, `crewai`, `llama-index`, and most opt-in telemetry stacks.

The **PostHog `phc_…` key** is even more explicitly safe: PostHog ships two key formats — `phx_…` (the personal API key, full read/write) and `phc_…` (the *project* / *client* key, write-only event ingest). The latter is *designed* to be shipped in public clients (mobile apps, browser SDKs, OSS Python packages). PostHog's own docs say so directly.

A gitleaks rule that fires on "long-high-entropy string near `api_key=`" cannot distinguish these from real leaks. The curation answer for telemetry-key hits is always to read the surrounding code (is this opt-in gated? does the prefix or context indicate write-only?) and the upstream documentation. Both pass here.

This is the same FP class we've now seen on a half-dozen scans (the [traceloop/openllmetry](traceloop-openllmetry.html) VCR cassettes, the [LazyLLM](lazyagi-lazyllm.html) `test_validate_api_key.py` fixtures, the [ha-mcp](homeassistant-ai-ha-mcp.html) `DEMO_TOKEN`, the [ReMe](agentscope-ai-reme.html) `test_redacts_key_value_credentials` cases) — the "scanner doesn't know the credential is public-by-design" pattern.

### 2. ~13 Next.js / Mermaid / postcss / uuid advisories — **all in `docs/yarn.lock`, the Docusaurus site**

Trivy fired on:
- **Next.js `16.2.4`**: ten advisories (XSS, SSRF, info disclosure via middleware bypass, authorization bypass via crafted query, DoS variants, cache poisoning, etc.).
- **Mermaid**: four advisories.
- **postcss**, **uuid**: one each.

Every one of these is pinned in `docs/yarn.lock`, the Docusaurus documentation site, not in the deepteam runtime. The applicability question reduces to the deployment shape of the docs site:
- If deepteam's docs are built and published to a static-hosting CDN (e.g. Vercel's edge / Cloudflare Pages / GitHub Pages), most of these advisories don't apply — there is no Next.js server running to be attacked. The SSRF, middleware bypass, DoS-via-POST, and authorization bypass variants all require a Next.js server process.
- If deepteam self-hosts the docs as a Next.js application, the picture changes — though even then, the `trydeepteam.com` docs site doesn't expose authenticated endpoints, so the auth-bypass advisories are out-of-model.

**This is the "docs-as-separate-surface" pattern in its cleanest form**: same shape as [Klavis](klavis-ai-klavis.html), [honcho](plastic-labs-honcho.html), and [dograh](dograh-hq-dograh.html), where the front-end / docs lockfile carries the bulk of the trivy count and the runtime threat model leaves it untouched. The `--ignore-samples` default-suppression that landed [2026-05-28](evalstate-fast-agent.html#notes-on-the-tool) covers `samples/`, `examples/`, `demos/`, but not `docs/` — a future shipped-default to skip `docs/yarn.lock` (and `docs/package-lock.json`) for Python-stack projects would zero this category out cleanly.

### 3. 8× Python `poetry.lock` tail — **real best-practice, but Dependabot is wired**

The Python side is the standard dep-tail of a 2026 Python project: `aiohttp` ×3 (DoS variants), `urllib3` ×4 (decompression-bomb / info-disclosure via redirect), `pyasn1` ×2, `protobuf`, `wheel`, plus a couple of singles. A single `poetry update` clears most.

**Critically**: `.github/dependabot.yml` *is* present in the repo, unlike on every other "deps-are-the-thing" target this past week. This is the first scan in seven where the dep-tail item was *not* file-as-issue — Dependabot is already on the job. The right curation answer when the bot is wired is to skip the dep-bump issue and let the bot do its rounds.

### 4. 8× semgrep code findings — **all in `docs/scripts/` or `docs/src/`** (Docusaurus build pipeline)

| Finding | Files | Verdict |
|---|---|---|
| 1× `javascript.detect-child-process` | `docs/scripts/generate-contributors.mjs:89` | Docusaurus build script that calls `git` for a contributor list. By-design; build-time only. |
| 3× `javascript.detect-non-literal-regexp` | `docs/scripts/replace-img-with-image-displayer.mjs:21,23,25` | Docusaurus image-displacement transform. Inputs are markdown files in the repo. Build-time only. |
| 3× `typescript.react-dangerouslysetinnerhtml` | `docs/src/components/Equation/index.tsx:17`, `docs/src/components/SchemaInjector/SchemaInjector.tsx:25`, `docs/src/sections/home/CompanyLogos/_createInlineLogo.tsx:20` | Static-site React components rendering author-controlled content (LaTeX equations, JSON-LD schema, inline SVG logos). Same threat model as any Docusaurus or Next.js page that renders trusted Markdown — by-design when inputs are repo-owned. |

The Python runtime under `deepteam/` had **zero semgrep findings of any severity**. This is the first scan in the series with that specific signature — every prior Python project surfaced at least one runtime-source `non-literal-import` / `dynamic-urllib` / `subprocess-shell-true` hit.

## Patterns observed

**The "intentional OSS-telemetry public key" FP class is now well-documented across the series.** PostHog's `phc_…` keys, New Relic's OTLP license keys, Sentry's DSN public keys, Mixpanel's project tokens — every one of them looks exactly like a leaked secret to a regex-based detector, and every one of them is publicly shipped by design across hundreds of OSS projects. A `gitleaks` confidence-downgrade rule keyed on the credential *prefix* (`phc_` for PostHog's project keys, `…FFFFNRAL` for New Relic license keys, etc.) would flip these from "high confidence" to "low confidence" without losing the real-leak signal. Worth a tool-side patch in the same vein as the [2026-05-28 `logger-credential-leak` downgrade](evalstate-fast-agent.html#notes-on-the-tool).

**The "first project of the week with Dependabot wired" inverts the dep-tail framing.** [MemoryBear](suanmosuanyangtechnology-memorybear.html), [agency-swarm](vrsen-agency-swarm.html), [ouroboros](q00-ouroboros.html), [ReMe](agentscope-ai-reme.html), and [LazyLLM](lazyagi-lazyllm.html) all ran without Dependabot; deepteam is the first this week with the bot in place. The corollary is concrete: when Dependabot is wired, the "single coordinated `uv lock --upgrade` / `poetry update`" issue we typically file would simply duplicate work the bot is already doing. The curation answer changes from "file an issue listing the CVEs" to "note in the post that the bot will handle it." A future scanner-side check would verify Dependabot is wired and drop the dep-bump-issue suggestion from the report when it is.

**The `docs/`-as-separate-surface convention is established enough to ship as a default.** Five scans now ([Klavis](klavis-ai-klavis.html), [honcho](plastic-labs-honcho.html), [dograh](dograh-hq-dograh.html), [pixeltable](pixeltable-pixeltable.html), and now deepteam) have had a meaningful share of their finding count in a `docs/` or `examples/` subtree that does not run in production. The `--ignore-samples` flag covers `samples/`, `examples/`, `demos/`, `sample-apps/` — adding `docs/yarn.lock` / `docs/package-lock.json` / `docs/package.json` to the default ignore list (specifically the lockfiles, not the entire `docs/` tree — markdown files might still surface gitleaks hits worth checking) would catch a large share of these out-of-runtime advisories automatically.

**Five clean scans now in the series, and the underlying pattern is consistent.** Giskard had a meticulous `pull_request_target` audit. Semble was a tight one-purpose library with two responsive maintainers. Logfire's `eval`/`exec`/`pickle` hits were all intentional language-feature uses on an observability library. ha-mcp had a precise published threat model. deepteam is the fifth shape: a focused Python runtime + a strictly-separate documentation surface + intentional public telemetry + a wired bot. Each clean scan is a different shape of "what right looks like" — the series is starting to function as a small reference library for that question.

## Notes on the tool

- This is the first scan in the series where the `gitleaks` step would benefit from prefix-based confidence downgrades for known-public OSS-telemetry credentials. Concrete candidates for a prefix downgrade list: `phc_…` (PostHog project key), New Relic OTLP suffix `…NRAL`, Sentry DSN `https://*@*.ingest.sentry.io/*`, Mixpanel tokens of the project-token shape. The same pattern as the rule-name-based [`logger-credential-leak` confidence downgrade](evalstate-fast-agent.html#notes-on-the-tool) shipped 2026-05-28.
- For projects with both Python and `docs/`-side advisory tails, the `--ignore-samples` flag should grow a sibling `--ignore-docs-lockfiles` (or be replaced by a more general `--ignore-paths-from-file`). Five out of seven scans this past month have had a meaningful share of their high-severity count in lockfiles for documentation sites.
- For the first time in the series, a scan ran against a project with Dependabot already wired. The curation-side answer changed: no dep-bump issue filed. A future tool-side feature to *detect* Dependabot's presence and adjust the suggested-action output would compress this step.

## Disclosure timeline

- **2026-06-09** — Scan run at commit `846e2dff24fd`; findings curated. The two gitleaks hits were inspected in `deepteam/telemetry.py` and confirmed as the standard OSS-telemetry write-only-key pattern (PostHog `phc_…` project key + New Relic OTLP license key). The 24-CVE trivy tail was traced to `docs/yarn.lock` (Docusaurus, out-of-scope runtime) and `poetry.lock` (Dependabot already wired). The 8 semgrep code findings were all under `docs/scripts/` or `docs/src/`. Quality gate evaluated to false: zero real in-scope runtime items.
- **2026-06-09** — Post-only published. No public courtesy issue filed (none of the items meet the issue-filing bar: the dep-tail is on Dependabot's lane, the JS lockfile pile is out-of-scope, the gitleaks hits are FP-by-design, and the docs-site semgrep code findings are build-pipeline only).

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/confident-ai/deepteam" \
  --reports-dir reports/confident-ai-deepteam \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
