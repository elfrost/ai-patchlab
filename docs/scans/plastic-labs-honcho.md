---
layout: default
title: "plastic-labs/honcho: security scan"
description: "Security scan of plastic-labs/honcho: 315 findings, real cluster on the MCP server's Hono framework (~9 CVEs incl"
date: 2026-05-25
---

# plastic-labs/honcho — security scan

**Repository:** [plastic-labs/honcho](https://github.com/plastic-labs/honcho) — 4.2k★, AGPL-3.0, a memory library for stateful AI agents — server, MCP integration, multi-language SDKs, and a docs site, all in one monorepo.
**Commit scanned:** `7470866d1284` (HEAD of `main` at scan time)
**Scan date:** 2026-05-25
**Disclosure status:** Public courtesy issue filed on the honcho repo. Every finding traces to a published CVE or a best-practice pattern — no private coordination required.

## Summary

| Severity | Count (raw) | Count (after ignore-file) |
| --- | ---: | ---: |
| Critical | 1 | 1 |
| High | 226 | 37 |
| Medium | 88 | 48 |
| Low | 0 | 0 |
| Info | 0 (filtered) | 0 (filtered) |

**315 raw findings → 86 after suppressing `migrations/**` and `examples/**`. After curation: one cluster on the MCP server's TypeScript framework (Hono advisories), a vulnerable docs-site lockfile incl. a critical CVE, four workflow-injection patterns, and one real-source SQL-identifier site.**

honcho is structurally interesting: three independent dependency trees — `mcp/bun.lock` (TypeScript MCP server), `docs/bun.lock` (the Mintlify-style docs site), and the main Python `uv.lock` — each managed separately, each with its own drift. After two prior scans where the migration-script SQL class dominated raw counts ([Upsonic](upsonic-upsonic.html) and [PraisonAI](mervinpraison-praisonai.html)), honcho's Alembic migrations contributed 196 of the same-pattern findings, all suppressed in the ignore-file as low-realistic-risk. The remaining 86 are the actionable surface.

## Top findings (curated)

### 1. Hono framework CVEs in `mcp/bun.lock` — the MCP server's runtime stack

**Tool:** Trivy (high/medium confidence — named advisories)
**Verdict:** **Real — the MCP server is a deployed surface.**

honcho's MCP server is a TypeScript application built on [Hono](https://hono.dev/). Trivy surfaces ~9 advisories against the pinned `hono` and `@hono/node-server` versions, in approximate descending order of concern:

- **`@hono/node-server` — authorization bypass for protected static paths via encoded slashes in Serve Static Middleware.** This one is directly auth-bypass-shaped: a request with `%2F`-encoded path segments can reach static files that were supposed to be gated.
- **Hono — arbitrary file access via `serveStatic`** (separate from the encoded-slash variant above).
- **Hono — SSE Control Field Injection via CR/LF in `writeSSE()`** — relevant if the MCP server sends server-sent events with any user-controllable content.
- **Hono — Cookie Attribute Injection via unsanitized `domain` / `path` in `setCookie()`** and **missing cookie-name validation on write path.**
- **Hono — Prototype Pollution via `__proto__` in `parseBody({ dot: true })`.**
- **Hono — incorrect IP matching in `ipRestriction()` for IPv4-mapped IPv6 addresses** — IP allowlists may not behave as configured.
- **`hono/jsx` — HTML injection via unvalidated JSX tag names + CSS declaration injection via style-object values in JSX SSR** — relevant if the MCP server renders any JSX response.
- **Hono — Cache Middleware ignores `Vary`.**

These are the kind of advisories that accumulate when a TypeScript framework's pin drifts a few minor versions. A single `hono`/`@hono/node-server` bump in `mcp/` clears the class. The MCP server is honcho's external integration surface — anything an agent or another MCP client talks to — so worth prioritizing ahead of the docs-site items below.

### 2. `docs/bun.lock` — 1 critical + ~30 dependency advisories

**Tool:** Trivy
**Verdict:** **Real — vulnerable lockfile shipped in the public repo.**

The docs site (Mintlify-shaped) has its own bun lockfile, and it has drifted further than the MCP server's. Headline:

- **Critical:** `basic-ftp` — File overwrite due to path traversal.
- **High cluster:** `axios` (×15), `lodash` (×5), `picomatch` (×4), `fast-uri` (×2), `minimatch` (×3), plus `glob`, `tar-fs`, `brace-expansion`, `follow-redirects` (custom-auth-header leak across cross-domain redirect), `ajv`, `js-yaml`, `mdast-util-to-hast`, `postcss`, `yaml`, `uuid`.

The docs site doesn't process untrusted runtime input the way the MCP server does — most of these CVEs are transitive build-time dependencies. But two structural items matter even for a docs site:

1. **A shipped lockfile with known-vulnerable deps is a signal of process drift**, regardless of runtime impact. If `docs/` is being rebuilt at any cadence, the lockfile should be on the same dep-update path as the rest of the repo.
2. **`basic-ftp` showing up critical** — bun's lockfile resolves transitive deps, and `basic-ftp` is not something a docs site directly needs. Worth chasing where that came from (a dev tool? a build helper?) and pruning if it's no longer needed.

### 3. 4× workflow `${{ ... }}` shell interpolation in `fly-deploy*.yml`

**Tool:** Semgrep (`run-shell-injection`)
**Verdict:** **Real best-practice — the recurring class, now seen on every CI-heavy scan in this series.**

`.github/workflows/fly-deploy.yml` and `fly-deploy-prod.yml` interpolate `${{ ... }}` values into `run:` shell blocks at workflow-parse time. Same fix template as [gptme PR #2399](https://github.com/gptme/gptme/pull/2399) — pass through `env:` and reference `$VAR` from the shell. Four occurrences, two files, mechanical fix.

### 4. `src/db.py:72` — one `text("SQL")` site in core source

**Tool:** Semgrep (`avoid-sqlalchemy-text`)
**Verdict:** **Best-practice — same identifier-interpolation class as on three prior scans, low real risk here because the interpolation comes from config.**

Same shape as Upsonic and PraisonAI (and four sites in honcho's `scripts/configure_embeddings.py`, an operator-run script outside the request path). The `quoted_name()` / `Identifier()` defensive pattern applies — the value isn't reachable from untrusted input today, but the shape locks in the assumption.

### 5. The false positives, briefly

| Finding | Verdict |
|---|---|
| 3× `logger-credential-leak` in `src/deriver/deriver.py:271,279` + `src/utils/summarizer.py:881` | **FP** — same rule class that over-fires across the series (now five scans with zero true positives — [openllmetry](traceloop-openllmetry.html), [Upsonic](upsonic-upsonic.html), [airweave](airweave-ai-airweave.html), [HolmesGPT](holmesgpt-holmesgpt.html), honcho). A confidence downgrade is overdue. |
| 3× "secret detected" in `docs/docs.json:593`, `sdks/typescript/__tests__/errors.test.ts:307`, `tests/telemetry/test_events.py:305` | **FP** — Mintlify config + test fixtures |
| 196 SQL findings inside `migrations/**` | **Suppressed by `--ignore-file`** — Alembic migrations using `text()` for DDL with config-controlled identifiers. Same class as on Upsonic and PraisonAI; low risk in migration code |
| `examples/**` dependency advisories (Pillow, aiohttp, langchain, langgraph, etc.) | **Suppressed by `--ignore-file`** — example integration projects each ship their own lockfile; not honcho's deployed surface |

## Patterns observed

**Multi-stack monorepos accumulate drift in proportion to the number of independent lockfiles.** honcho ships three: Python `uv.lock`, TypeScript `mcp/bun.lock`, and another TypeScript `docs/bun.lock` for the docs site. The Python tree is reasonably tight; both bun lockfiles are noticeably behind. The pattern is the same as [Klavis' 50+ MCP server lockfiles](klavis-ai-klavis.html), just at smaller scale: every independently-managed dep tree without an automation backstop drifts at its own rate. honcho's case is more tractable — only two npm/bun trees to update — but the structural recommendation is identical: dependabot/renovate scoped across all three lockfile locations.

**Hono's advisory tail this year is unusually long.** Nine separate advisories against `hono` and `@hono/node-server` in a single pinned-version range is a lot. It's worth flagging because **the MCP server is honcho's external integration surface** — a stateful-memory backend that other agents and apps talk to. The `serveStatic` / encoded-slash / cookie-injection / prototype-pollution advisories are exactly the class that matters in a server context. This is one of the cleaner "upgrade a single dep, clear a real category" wins available.

**The `logger-credential-leak` rule has reached the threshold for downgrade.** Five scans in a row ([openllmetry](traceloop-openllmetry.html), [Upsonic](upsonic-upsonic.html), [airweave](airweave-ai-airweave.html), [HolmesGPT](holmesgpt-holmesgpt.html), honcho), it has fired only on false positives — and on [HolmesGPT specifically](holmesgpt-holmesgpt.html#the-other-notable-false-positive-27-logger-credential-leak-in-exemplary-oauth-code) it fired 27 times on *exemplary* OAuth-logging code. The rule's heuristic is proximity to variable names like `token` / `secret`; in any LLM-tooling or OAuth-handling codebase, those variable names are everywhere. Time to push it to `low` confidence by default and let the rare true positive earn its way back up.

## Notes on the tool

Sharpened backlog:

- **Default `low` confidence for `logger-credential-leak` is now an action item, not a backlog item** — five-for-five false positives across the series.
- **`--ignore-file` was load-bearing here for the third time.** Without `migrations/**` suppression, the report would have been dominated by the same migration `text()` cluster we've documented twice already.
- **`docs/bun.lock`'s `basic-ftp` critical** is a good test case for a future "where did this transitive dep come from?" tool feature — Trivy reports the advisory but not the dependency chain that pulled `basic-ftp` into a Mintlify-style docs site.

## Disclosure timeline

- **2026-05-25** — Scan run at commit `7470866d1284`; `migrations/**` and `examples/**` suppressed; findings curated.
- **2026-05-25** — Public courtesy issue filed on plastic-labs/honcho. All findings trace to published CVEs or best-practice patterns; no private coordination required.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/plastic-labs/honcho" \
  --reports-dir reports/plastic-labs-honcho \
  --min-severity medium \
  --ignore-file reports/plastic-labs-honcho/.aipatchlabignore
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
