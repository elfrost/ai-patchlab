---
layout: default
title: "dograh-hq/dograh: security scan"
date: 2026-05-21
---

# dograh-hq/dograh — security scan

**Repository:** [dograh-hq/dograh](https://github.com/dograh-hq/dograh) — 2.5k★, BSD-2-Clause, an open-source voice-agent platform (Python API backend + Next.js UI).
**Commit scanned:** `21951eca18cd` (HEAD of `main` at scan time)
**Scan date:** 2026-05-21
**Disclosure status:** ✅ **Resolved.** Issue [#338](https://github.com/dograh-hq/dograh/issues/338) closed COMPLETED on 2026-05-27. Maintainer [@nuthalapativarun](https://github.com/nuthalapativarun) authored four PRs covering each item; three merged ([#356](https://github.com/dograh-hq/dograh/pull/356) `OSS_JWT_SECRET` fail-closed, [#360](https://github.com/dograh-hq/dograh/pull/360) api container non-root, [#361](https://github.com/dograh-hq/dograh/pull/361) Next.js upgrade in `evals/visualizer/`), one closed without merging ([#357](https://github.com/dograh-hq/dograh/pull/357), duplicate-lockfile — likely a different approach chosen).

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 41 |
| Medium | 28 |
| Low | 0 |
| Info | 0 (filtered) |

**69 total findings. After curation: one dominant real cluster (an outdated Next.js across two front-ends), three smaller best-practice items, and ~8 false positives.**

dograh is a right-sized target: a focused two-component codebase (Python `api/` + Next.js `ui/`, plus an `evals/visualizer/` tool), and the scan tells a clean single-headline story rather than burying it. It's also one of the most responsive repos in the series — issues closed within days, external PRs merged within 24 hours — which is exactly the kind of project where a courtesy issue is most likely to land.

## Top findings (curated)

### 1. Outdated Next.js across `ui/` and `evals/visualizer/` — ~45 findings, one root cause

**Tool:** Trivy (high/medium confidence — named advisories)
**Verdict:** **Real — a single dependency upgrade clears the whole cluster.**

The `next` package is pinned to a vulnerable version in three lockfiles (`ui/package-lock.json`, `evals/visualizer/package-lock.json`, `evals/visualizer/pnpm-lock.yaml`). Trivy surfaces the full advisory set against that version. The sub-classes, roughly in descending order of concern:

- **Middleware / proxy bypass** (multiple advisories: Pages Router i18n, App Router segment-prefetch, dynamic route parameter injection, plus an "incomplete fix follow-up"). This is the most serious class — Next.js middleware is frequently where auth/authorization checks live, and a middleware bypass can mean an unauthenticated request reaching a protected route. For a voice-agent platform whose UI fronts campaign and contact data, that's directly in the threat path.
- **SSRF via WebSocket upgrades.**
- **Several DoS variants** (connection exhaustion with Cache Components, Server Components, Image Optimization API).
- **XSS variants** (`beforeInteractive` scripts, CSP-nonce App Router).
- **Cache poisoning in React Server Component responses.**

None of these is a dograh code bug — they are all the standard Next.js advisory backlog that accumulates when the framework pin drifts. The fix is a single `next` upgrade per front-end to the current patched release, then a re-lock. Given dograh ships the UI as a container image (`dograhai/dograh-ui`), the upgrade also needs an image rebuild to actually reach deployments.

### 2. `evals/visualizer/` ships two lockfiles — `package-lock.json` *and* `pnpm-lock.yaml`

**Verdict:** **Real hygiene issue — drift hazard.**

The `evals/visualizer/` directory carries both an npm lockfile and a pnpm lockfile. Whichever one a given developer's (or CI's) package manager honours, the other silently goes stale — and the scan confirms it: the Next.js advisories fire against *both* lockfiles, which means both are present and both are out of date. Pick one package manager for the sub-project, delete the other lockfile, and the dependency surface stops being ambiguous.

### 3. `docker-compose.yaml:180` — `OSS_JWT_SECRET` defaults to `ChangeMeInProduction`

**Verdict:** **Self-aware placeholder, but still a fail-open footgun.**

```yaml
OSS_JWT_SECRET: "${OSS_JWT_SECRET:-ChangeMeInProduction}"
```

The `${VAR:-default}` shape means a deployment that never sets `OSS_JWT_SECRET` silently runs with the secret literally being the string `ChangeMeInProduction` — a value committed in a public repo. Anyone can then forge JWTs against that deployment. The naming shows the maintainer is aware of the risk, which is good — but a self-documenting placeholder is not the same as a guardrail. The robust pattern is to *not* provide a default and fail fast at startup:

```yaml
# compose: require the var, no default
OSS_JWT_SECRET: "${OSS_JWT_SECRET:?OSS_JWT_SECRET must be set}"
```

`${VAR:?message}` makes `docker compose up` abort with the message if the variable is unset — the deployment fails loudly instead of silently running with a known-public signing key. Same class as the [PraisonAI SurrealDB `root/root` finding](mervinpraison-praisonai.html), which was [fixed by raising on missing credentials](https://github.com/MervinPraison/PraisonAI/pull/1677).

### 4. `api/Dockerfile` — missing `USER`, missing `--no-install-recommends`

**Verdict:** **Minor best-practice.**

The API container runs as root (no `USER` directive) and its `apt-get install` omits `--no-install-recommends`. The first is the standard container-hardening item flagged on several prior scans; the second is image-hygiene (smaller image, fewer packages, smaller attack surface). Both mechanical.

### 5-N. False positives

| Finding | Verdict |
|---|---|
| 6× "secret detected" in `docs/**/*.mdx` | **FP** — API-reference documentation showing example `Authorization` headers / token placeholders |
| 2× `POSTHOG_API_KEY` / `POSTHOG_KEY` = `phc_ItizB1dP6yv7ZYobbcqrpxTdbomDA8hJFSEmAMdYvIr` | **FP** — PostHog `phc_` public project key, write-only event ingestion, designed to be shipped. Same FP class as [openllmetry](traceloop-openllmetry.html), [PraisonAI](mervinpraison-praisonai.html), [Giskard](giskard-ai-giskard-oss.html) |

## Patterns observed

**One headline, cleanly told.** After [Klavis' 1,556-finding monorepo sprawl](klavis-ai-klavis.html), dograh is the contrast case: a focused codebase where the scan produces a single actionable headline (upgrade Next.js) plus a short tail. This is what a "right-sized" target looks like — the curation isn't a fight against volume, it's a quick separation of one real cluster from a handful of best-practice items. The [target-selection refinement](https://github.com/elfrost/ai-patchlab) that picked dograh — bias toward responsive, focused repos over sprawling ones — produced exactly the scan it was supposed to.

**Front-end framework drift is its own dependency-hygiene category.** Where [guardrails' finding](guardrails-ai-guardrails.html) was a Python dep (`litellm`) and [Klavis' was npm sprawl across 50 servers](klavis-ai-klavis.html), dograh's is a single framework — Next.js — whose advisory cadence is unusually high. Next.js ships security releases often; a pin that's a few minor versions behind accumulates a long advisory list fast. The middleware-bypass sub-class in particular is worth treating as higher-priority than the DoS variants, because middleware is where authorization decisions commonly sit.

**The `ChangeMeInProduction` default is a good intention one step short of a guardrail.** It's genuinely better than a silent random-looking default (the developer reading the compose file *sees* the warning). But `${VAR:-default}` still fails *open* — an unset variable produces a running service with a public key. `${VAR:?message}` fails *closed*. The one-character difference (`:-` vs `:?`) is the whole security property.

## Notes on the tool

- **Cross-lockfile dependency deduplication** remains the top backlog item — the Next.js advisory set is reported once per lockfile (×3 here, ×59 on Klavis). "1 advisory → N affected lockfiles" is the right shape.
- The `.aipatchlabignore` feature was not needed on this scan — at 69 findings the report is small enough to triage directly. Worth noting as a data point: path-suppression earns its keep on monorepos, not on focused repos.

## Disclosure timeline

- **2026-05-21** — Scan run at commit `21951eca18cd`, findings curated.
- **2026-05-21** — Public courtesy issue filed on dograh-hq/dograh. All findings trace to published CVEs or best-practice patterns; no private coordination required.

## Resolution

Six days from issue filed to all PRs merged. The fix breakdown:

- **[PR #361](https://github.com/dograh-hq/dograh/pull/361)** — `evals/visualizer/package.json` upgraded `next` from `16.1.4` to `16.2.6` and regenerated `pnpm-lock.yaml`, clearing the middleware-bypass, SSRF, DoS, and reflected-XSS advisories on that surface. (The `ui/` Next.js upgrade is not addressed by this PR — that lockfile is still on the older version and remains a follow-on item.)
- **[PR #360](https://github.com/dograh-hq/dograh/pull/360)** — Added a `dograh` system user in `api/Dockerfile` so uvicorn, arq workers, and the ARI manager all run non-root. The PR body explicitly notes "Running as root unnecessarily increases the blast radius of any container escape or RCE vulnerability" — same framing we recommended.
- **[PR #356](https://github.com/dograh-hq/dograh/pull/356)** — `docker-compose.yaml` switched from `${OSS_JWT_SECRET:-ChangeMeInProduction}` to `${OSS_JWT_SECRET:?...}` so the stack now aborts at startup if the variable is unset. Exact fix-pattern from the issue.
- **[PR #357](https://github.com/dograh-hq/dograh/pull/357)** — Closed without merging. The PR proposed removing the redundant `package-lock.json` from `evals/visualizer/` (since the directory has `pnpm-workspace.yaml`). Likely the maintainers chose a different reconciliation; the duplicate-lockfile cleanup may have been handled differently or deferred.

Three PRs merged within hours of being opened, the JWT-secret fix-closed pattern adopted verbatim from the recommendation, and the maintainer (`nuthalapativarun`) authored each PR with a clear summary explaining the security rationale. Combined with the resolved [gptme #2399](gptme-gptme.html) and [PraisonAI #1677](mervinpraison-praisonai.html), this is the **third confirmed resolution** in the series — and the first one with a partial outcome (one PR not merged) worth noting honestly rather than papering over.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/dograh-hq/dograh" \
  --reports-dir reports/dograh-hq-dograh \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
