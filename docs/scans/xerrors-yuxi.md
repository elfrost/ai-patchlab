---
layout: default
title: "xerrors/Yuxi: security scan"
date: 2026-06-19
---

# xerrors/Yuxi — security scan

**Repository:** [xerrors/Yuxi](https://github.com/xerrors/Yuxi) — 5.6k★, MIT, a multi-tenant Agent Harness platform with knowledge-base + knowledge-graph management (Chinese-language project: "结合知识库、知识图谱管理的 多租户 Agent Harness 平台"). FastAPI backend + Vue web UI, with built-in agent skills (incl. a MySQL reporter) and a RAG/chunking pipeline.
**Commit scanned:** `3eac017d3e69` (HEAD of `main` at scan time)
**Scan date:** 2026-06-19
**Disclosure status:** ✅ **Resolved.** Public courtesy issue ([#780](https://github.com/xerrors/Yuxi/issues/780)) filed — focused on the one app-code best-practice item (wildcard CORS) + a reachable dependency refresh (the auth-path `pyjwt`, `langchain`), with explicit credit for the parts the developer built correctly. The maintainer landed both within ~2 days: a `YUXI_CORS_ORIGINS` env-allowlist (locked down by default in production) with an explicit `allow_credentials=False` downgrade when `*` is present, and a `pyjwt` bump to 2.13.0. Non-strict-norm (no SECURITY.md); the items were best-practice / public-CVE, not exploit-shaped, so a focused public issue was the right channel.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 22 |
| Medium | 48 |
| Low | 0 |
| Info | 0 (filtered) |

**70 findings, all first-party. After curation: a well-built multi-tenant harness where the developer anticipated every obvious agent/tenant-injection vector — and a reachability discipline (does tenant/agent input reach a sensitive sink?) came back *clean* on every source-code candidate.** The residual actionable surface is one genuine best-practice item (wildcard CORS + credentials on the multi-tenant server) and a dependency tail that includes a reachable-but-correctly-used `pyjwt` on the auth path. Every guard I traced held.

## Where the developer did it right (the credits, because they're the story)

This scan was picked specifically as a multi-tenant target to apply a sharp reachability discipline — *trace whether tenant/agent-controlled input reaches a sensitive sink.* Three obvious candidates, three correct defenses:

- **Agent-tool SQL is strictly allowlisted.** The built-in `mysql-reporter` skill runs `cursor.execute(f"DESCRIBE \`{table_name}\`")` — an f-string identifier interpolation, and `table_name` comes from the LLM agent. But it's gated by `MySQLSecurityChecker.validate_table_name`, which is `re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name)` — a strict allowlist that rejects backticks, semicolons, spaces, every injection metacharacter. The agent cannot inject through it. The Semgrep `formatted-sql-query` / `sqlalchemy-execute-raw-query` rules fire on the f-string (correctly, syntactically) but the code is safe — the developer anticipated exactly this and validated first.
- **JWT verification is textbook-correct.** `auth_utils.py` decodes tenant tokens with `jwt.decode(token, key, algorithms=[JWT_ALGORITHM], issuer=..., audience=..., options={"require": ["exp","sub","iss","aud"]})` — algorithm pinned (no `alg=none` / algorithm-confusion), issuer and audience verified, required claims enforced. This is how you're supposed to call PyJWT; the common multi-tenant auth-bypass shapes are all closed at the call site.
- **Markdown rendering is DOMPurify-sanitized.** The 6 `avoid-v-html` Vue findings looked like a classic agent-output-rendered-as-HTML XSS shape, but they're all safe: `MarkdownPreview.vue`'s `v-html` renders the output of `markdown_preview.js`, which imports and applies **DOMPurify** (and `escapeHtml` on frontmatter); `AgentFilePreview.vue`'s `v-html` is Shiki/hljs-highlighted code (escaped); the other 3 are in the VitePress `docs/` site (out of runtime).

When the obvious sinks are all correctly guarded, the residual findings are the best-practice edges — which is exactly the shape below.

## Top findings (curated)

### 1. `backend/server/main.py:46` — wildcard CORS with credentials on the multi-tenant server

**Tool:** Semgrep (`wildcard-cors`)
**Verdict:** **Real best-practice — the one genuine app-code item.**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

All four knobs at maximum on a **multi-tenant** API server. Browsers reject `Access-Control-Allow-Origin: *` together with credentials, so this is partially self-defeating in a browser — but on a multi-tenant platform the intent ("any origin may send credentialed requests") is exactly what cross-tenant CSRF/credential-leak protections exist to prevent, and non-browser clients don't enforce the rejection. Same unmitigated shape as [ReMe](agentscope-ai-reme.html) (vs the [agency-swarm](vrsen-agency-swarm.html) inline-downgrade pattern). Fix: read an explicit allowlist from config; when `*` is present, downgrade `allow_credentials` to `False`.

### 2. `backend/{,package/}uv.lock` — reachable dependency tail (no Dependabot)

**Tool:** Trivy / pip-audit
**Verdict:** **Real version-matches; the `pyjwt` ones are on the auth path (reachable) but the app's usage is already correct, so these are pure version bumps.**

- **`pyjwt`** — auth-bypass, SSRF, verifier-side algorithm-confusion, DoS advisories. `pyjwt` *is* imported on the tenant-auth path (`auth_utils.py`), so the advisories are reachable — **but** (per the [reachability discipline](q00-ouroboros.html#patterns-observed)) the app's own `jwt.decode` call is exemplary (pinned algorithm, verified iss/aud, required claims), so the residual risk is whatever lives in PyJWT's *internal* verification logic, not in how Yuxi calls it. Bumping the pin closes the library-internal CVEs; no code change needed.
- **`langchain`** — path-traversal / sandbox-escape advisory (×2 across both lockfiles).
- **Tail**: `aiohttp` (×5: pipelining, websocket-frame, digest-auth, parser-bypass, unread-compressed-body), `pypdf` (×3 infinite-loop / stream-length), `cryptography` (vulnerable bundled OpenSSL), `python-multipart` (quadratic querystring). A single `uv lock --upgrade` clears most; **no `.github/dependabot.yml`** is configured, so wiring it is the durable fix (same pattern as [MemoryBear](suanmosuanyangtechnology-memorybear.html) et al.).

### 3-N. By-design / FP / out-of-runtime

| Finding | Files | Verdict |
|---|---|---|
| 6× `avoid-v-html` | `MarkdownPreview.vue` (DOMPurify), `AgentFilePreview.vue` (Shiki-escaped), `docs/.vitepress/*` ×3 (out of runtime) | **FP** — see credits above |
| 4× SQL `text(f)` / formatted | `mysql-reporter/.../describe_table.py` | **Gated** — strict `validate_table_name` allowlist (see credits) |
| 5× Dockerfile root + 3 `missing-user` + apt-get | Dockerfiles | Real container-hardening best-practice (add non-root `USER`) |
| 2× gitleaks `generic-api-key` | `.env.template:7` (placeholder), `md_parser_utils.py:131` (chunking code, no secret) | **FP** |
| 2× `non-literal-import` | agent built-in registry, knowledge parser factory | **By-design** — plugin/skill discovery |

## Patterns observed

**The reachability discipline cuts toward "safe" as often as "severe" — and confirming the guards is the work.** Tracing tenant/agent input to a sink can *raise* a by-design line to a high-severity finding as readily as it clears one. Here, the discipline applied to three multi-tenant sinks (agent-SQL, tenant-JWT, agent-markdown→HTML) came back clean each time — but only *because I read the guard*, not because the scanner said so. The scanner flagged all three (f-string SQL, v-html). The verdict "safe" required reading `validate_table_name`'s regex, the `jwt.decode` options dict, and the DOMPurify import. A curated report's value is the same in both directions: a report that stopped at the rule would have been wrong here (over-stating Yuxi's SQL and v-html), just as one would under-state a case where the guard *didn't* hold.

**A multi-tenant harness whose developer pre-empted the obvious injections is a "what right looks like" reference for the agent-tool-SQL + tenant-JWT surface.** The `validate_table_name` allowlist in front of an LLM-controlled `DESCRIBE` is the cleanest agent-tool-SQL defense in the series; the `jwt.decode` call is the cleanest tenant-auth call. Where prior scans surfaced the *unguarded* version of these (the recurring `text(f)` class, the [airweave](airweave-ai-airweave.html) JWT items), Yuxi shows the guarded version of both in one codebase.

**`usedforsecurity`-style intent markers, continued: DOMPurify import is the XSS equivalent.** Just as [mistral-vibe's `hashlib.sha1(..., usedforsecurity=False)`](mistralai-mistral-vibe.html) was the machine-readable "this hash isn't security," a `DOMPurify.sanitize` in the render path is the machine-readable "this v-html is sanitized." A scanner that traced the `v-html` binding back to a DOMPurify-wrapped value could suppress the `avoid-v-html` finding — the same call-graph-aware suppression proposed for the sha1 and `phc_`-key cases.

## Notes on the tool

- **UTF-8 fix validated on a third Chinese-language repo**: `semgrep.json` came back at 153 KB (healthy, 0 scanner meta-errors) on Yuxi's Chinese source. The [2026-06-11 cp1252 crash](dataelement-clawith.html) would have silently zeroed this scan pre-fix; byte-size verified before trusting the count, per the standing lesson.
- **Ownership split ([harbor lesson](harbor-framework-harbor.html)) checked, trivial**: Yuxi is a single first-party project (no vendored sub-trees), so all 70 findings are first-party and the work went into reachability, not attribution.
- The standing scanner refinements this scan re-votes for: a **call-graph-aware v-html/innerHTML suppression when the bound value is DOMPurify-wrapped**, and the **Dependabot-presence check** to drop the dep-bump-issue suggestion (here it correctly *stays*, since no Dependabot is wired).

## Disclosure timeline

- **2026-06-19** — Scan run at commit `3eac017d3e69`; `semgrep.json` verified healthy (153 KB, Chinese source). Reachability traced on three multi-tenant sinks (agent-SQL, tenant-JWT, markdown v-html) — all three correctly guarded (allowlist regex, textbook `jwt.decode`, DOMPurify). Residual: wildcard CORS + a reachable dep tail.
- **2026-06-19** — Public courtesy issue [#780](https://github.com/xerrors/Yuxi/issues/780) filed on xerrors/Yuxi with the wildcard-CORS fix and the dependency refresh (auth-path `pyjwt` + `langchain` + tail, plus a Dependabot suggestion), explicitly crediting the guarded SQL / JWT / markdown handling.
- **2026-06-21 (~2 days later)** — ✅ Maintainer closed [#780](https://github.com/xerrors/Yuxi/issues/780) as completed (silent close). **Both primary items verified in-code on `main`:**
  - CORS (commit *"feat: add YUXI_CORS_ORIGINS environment variable for CORS configuration #780"*): `backend/server/main.py` now reads an explicit allowlist from `YUXI_CORS_ORIGINS` (and returns `[]` — fully locked down — by default in production), and `_build_cors_options` does the inline downgrade exactly as suggested: `if "*" in allow_origins: allow_credentials = False`, otherwise an explicit allowlist with scoped methods/headers. This is the [agency-swarm-pattern](vrsen-agency-swarm.html) fix plus a production-secure-by-default posture.
  - `pyjwt` bumped `2.12.1 → 2.13.0` (clears the auth-path advisories; the call site was already textbook-correct, so this closes the library-internal CVEs).
  - The Dependabot suggestion wasn't adopted — fine, it was a suggestion. The two actionable items both landed.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/xerrors/Yuxi" \
  --reports-dir reports/xerrors-yuxi \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
