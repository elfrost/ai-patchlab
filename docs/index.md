---
layout: default
title: AI PatchLab Scans
---

# AI PatchLab Scans

Security scans of public repositories run with
[AI PatchLab](https://github.com/elfrost/ai-patchlab), an open-source,
local-first security scanner.

Every report on this page was generated locally. No source code was sent to
any third party, no AI provider was contacted, and no paid API was called.
AI PatchLab orchestrates [Semgrep](https://semgrep.dev),
[Gitleaks](https://github.com/gitleaks/gitleaks),
[Trivy](https://trivy.dev), and
[pip-audit](https://github.com/pypa/pip-audit), then applies deterministic
remediation and confidence rules to normalize the findings.

## How these scans work

- Each scan targets a public repository at a specific commit.
- Findings are curated: noise filtered out, top items highlighted.
- Critical issues are reported to maintainers under responsible disclosure
  before being published here in full detail.
- Posts focus on patterns and lessons — not exploit walkthroughs.

## Scans

- **2026-06-17** — [omnigent-ai/omnigent](scans/omnigent-ai-omnigent.html) — 146 findings → **0 scanner clusters survived adversarial verification, but a completeness sweep surfaced a HIGH** the scanner structurally couldn't see: a `credential_proxy` `shell=True` line — correctly *by-design* from the sink — becomes a **multi-tenant sandbox-escape + operator-credential-theft chain** once you trace that an untrusted bundle upload reaches it. 🔒 Reported privately via GitHub Security Advisory (strict-norm); this is a **methodology post with no weaponized reproduction**. The lesson: reachability flips severity, not the sink — both directions
- **2026-06-15** — [harbor-framework/harbor](scans/harbor-framework-harbor.html) — 570 findings, **and the count means almost the opposite of what it looks like**: 464/570 (81%) and all 10 criticals are in 84 *vendored* benchmark adapters (`adapters/*`), not harbor's code. Harbor-core (34 findings, 0 critical) does the dangerous things right (tar `filter="data"`, Supabase publishable keys, by-design sandbox subprocess). The lesson: the first curation step on a monorepo is an **ownership split**. Filed one structural question on the sandbox-isolation threat model, not a 570-finding enumeration
- **2026-06-12** — [mistralai/mistral-vibe](scans/mistralai-mistral-vibe.html) — 21 findings, a clean coding-agent scan: the git wiring is **safe-by-construction** (GitPython argv API, no shell; `hashlib.sha1(..., usedforsecurity=False)` explicitly non-crypto). Real signal is a dependency tail with a sharp reachability split — `gitpython` imported/reachable (bump it), `pyjwt` declared-but-never-imported (version-match, not applicable)
- **2026-06-11** — [dataelement/Clawith](scans/dataelement-clawith.html) — 54 findings, **and the scan that caught a silent-failure bug in AI PatchLab's own scanner**: Semgrep crashed mid-write (Windows cp1252 vs the repo's Chinese source), left a 0-byte report, and 43 findings vanished — the first pass looked clean at 11. Fixed in PR #47 (force UTF-8 + treat empty report as scan error). Real items: a `head.ref` workflow shell-injection, a 6-CVE React Router frontend lockfile (no Dependabot), a Helm chart default password, nginx hardening
- **2026-06-10** — [Ar9av/obsidian-wiki](scans/ar9av-obsidian-wiki.html) — **0 findings literally** (sixth clean scan in the series, and the cleanest in raw count). Manual `semgrep` re-run confirmed `results: 0, errors: 0`. Architecture is "thin installer CLI + delegated Claude Code skills" — the agent intelligence lives in skill markdown the scanner doesn't read, leaving almost nothing to fire on
- **2026-06-09** — [confident-ai/deepteam](scans/confident-ai-deepteam.html) — 48 findings, **zero real in-scope runtime items**; **5th clean scan in the series**. Gitleaks hits were intentional OSS-telemetry write-only keys (PostHog `phc_…` + New Relic OTLP license); the 24-CVE trivy tail split between an out-of-scope Docusaurus `docs/yarn.lock` and a Python `poetry.lock` whose Dependabot was already on the job · post-only, no issue filed
- **2026-06-08** — [54yyyu/zotero-mcp](scans/54yyyu-zotero-mcp.html) — 4 scanner findings → **6 confirmed-real curated items, only 1 of which came from the scanner.** First scan run under the project's ultracode mode (23-agent parallel completeness sweep across MCP-specific surfaces). Headline: **medium SSRF in OA-PDF discovery** reachable via prompt injection + **medium plaintext `ZOTERO_API_KEY` stdout dump** (discipline break — same function obfuscates 25 lines earlier) + 4 hardening lows. The strongest "scanner alone undercounts MCP-specific surface" demonstration in the series. · ✅ **All six items fixed and merged ~6h later in PRs #327 + #328; v0.5.0 cut 9 min after issue close. Maintainer explicitly credited the adversarial-verification methodology.**
- **2026-06-06** — [LazyAGI/LazyLLM](scans/lazyagi-lazyllm.html) — 121 findings, **series record for the `pull_request_target` cluster** (16 sites in one workflow), Gradio ×3 + DeepSpeed RCE dep tail, classic `eval()`-based Calculator agent tool; two highest-severity items disclosed privately to a corporate maintainer address (SenseTime backing) — no public courtesy issue, post-only
- **2026-06-04** — [agentscope-ai/ReMe](scans/agentscope-ai-reme.html) — 159 findings, 3 concrete items filed (wildcard CORS + credentials on both HTTP-service entrypoints, `chromadb` CVE, Neo4j `password="neo4j"` default) · **largest SQL-identifier cluster in the series so far** (139 sites across 3 vector/file-store backends) + a new flow-DSL `exec`/`eval`-with-restricted-globals shape to watch · ✅ **All three items fixed in `reme4/` ~13h later (item-by-item response)**
- **2026-06-03** — [Q00/ouroboros](scans/q00-ouroboros.html) — 34 findings, **third "deps-are-the-thing" scan in a row** (after MemoryBear & agency-swarm) — `litellm` 7-advisory stack + `anthropic` 2-pair reported privately via the published SECURITY.md channel · ✉️ **Maintainer triaged within 48h SLA: all advisories are genuine version-matches but *none reachable* in Ouroboros's library-only usage (no LiteLLM Proxy, no anthropic memory-tool feature); coordinated refresh scheduled; post corrected for the surface conflation 2026-06-08**
- **2026-06-02** — [VRSEN/agency-swarm](scans/vrsen-agency-swarm.html) — 48 findings, **auth-tier dep concentration that fits the project's shape**: `authlib` 1 critical + 3 auth-bypass highs and `fastmcp` 1 critical SSRF + OAuth pile, on a multi-agent OAuth/MCP framework with no Dependabot · the recurring `shell=True`-in-agent-shell-tool by-design class · ✅ **Resolved 2026-06-04 in PR #659 (~15h)**
- **2026-06-01** — [SuanmoSuanyangTechnology/MemoryBear](scans/suanmosuanyangtechnology-memorybear.html) — 196 findings, **3 named critical CVEs in a stale `api/uv.lock` (pytorch RCE-class, fastmcp SSRF, nltk Zip Slip)** on a repo with no Dependabot · 37× Jinja2-for-LLM-prompts is the new rule-misfit class of the series · 📝 **Maintainer acknowledged + closed 2026-06-12 with intent to review + add Dependabot (no fix landed yet)**
- **2026-05-29** — [homeassistant-ai/ha-mcp](scans/homeassistant-ai-ha-mcp.html) — 65 findings, **zero real in-scope items**; a strict-norm repo whose maintainer published a precise threat model — every scary finding is a fixture, an intentional public demo token, a documented by-design decision, or an FP · post-only, no issue filed
- **2026-05-28** — [evalstate/fast-agent](scans/evalstate-fast-agent.html) — 36 findings, **near-clean scan where the maintainer already hand-rolled the hard mitigations** (a tar-traversal guard, a filename sanitizer before a shell call); actionable surface is two defense-in-depth hardenings + a Dependabot-lane `requests` CVE pair · ✅ **Both hardenings adopted in v0.7.13 the same day (~8h)**
- **2026-05-27** — [aurelio-labs/semantic-router](scans/aurelio-labs-semantic-router.html) — 116 findings, cleanest two-person-team scan in the series; entire actionable surface is 50 SQL-identifier sites in one Postgres-backend file + a 30-advisory dep-drift tail
- **2026-05-27** — [pixeltable/pixeltable](scans/pixeltable-pixeltable.html) — 67 findings, first scan to surface a **CVE-2007-4559-shape `tarfile.extractall` finding** on a code path that imports user-shared bundles; plus the recurring 26-site SQL-identifier class in the catalog layer · ✅ **PR #1378 (`filter='data'`) merged 2026-06-07 (~11 days, silent merge after CI review)**
- **2026-05-26** — [dstackai/dstack](scans/dstackai-dstack.html) — 163 findings, **3 real critical Go CVEs** in the runner (SSH `PublicKeyCallback` auth-bypass, Moby AuthZ bypass, go-git argument injection) + 21 workflow-injection patterns (series-high) · ❌ **Issue declined by maintainer for disclosure-format reasons; honest record kept**
- **2026-05-26** — [pydantic/logfire](scans/pydantic-logfire.html) — 27 findings, **third clean scan in the series**; every `eval`/`exec`/pickle finding is a deliberate language-feature use that an observability library structurally needs
- **2026-05-25** — [MinishLab/semble](scans/minishlab-semble.html) — 2 findings, **second clean scan in the series** (after Giskard); a small focused library with two hyper-responsive maintainers
- **2026-05-25** — [plastic-labs/honcho](scans/plastic-labs-honcho.html) — 315 findings, real cluster on the MCP server's Hono framework (~9 CVEs incl. auth bypass) + a critical `basic-ftp` in the docs-site lockfile; first scan where `logger-credential-leak` hit five-for-five FPs across the series
- **2026-05-21** — [HolmesGPT/holmesgpt](scans/holmesgpt-holmesgpt.html) — 2,143 findings, 93% are an SRE agent's deliberately-broken Kubernetes test fixtures; real signal is 17 workflow-injection patterns + a drifted `experimental/` front-end
- **2026-05-21** — [dograh-hq/dograh](scans/dograh-hq-dograh.html) — 69 findings, one dominant cluster (outdated Next.js across two front-ends, incl. middleware-bypass advisories) + a fail-open `OSS_JWT_SECRET` default · ✅ **3 of 4 PRs merged by `nuthalapativarun` (2026-05-27); issue closed**
- **2026-05-20** — [Klavis-AI/klavis](scans/klavis-ai-klavis.html) — 1,556 findings (largest scan in the series), 22 critical dependency CVEs incl. authlib auth-bypass + fastmcp SSRF; a case study in monorepo dependency drift across 50+ MCP servers
- **2026-05-20** — [Giskard-AI/giskard-oss](scans/giskard-ai-giskard-oss.html) — 27 findings, **all false positives** — first clean scan in the series; a teardown of `pull_request_target` done right vs the airweave finding
- **2026-05-19** — [guardrails-ai/guardrails](scans/guardrails-ai-guardrails.html) — 17 findings, **first dep-scan hits in the series** (7 known CVEs on a pinned `litellm` upper bound) + 2× duplicated `unverified-jwt-decode` + 4× workflow inputs interpolation
- **2026-05-19** — [airweave-ai/airweave](scans/airweave-ai-airweave.html) — 46 findings, ~4 publishable best-practice items + 1 disclosed privately via SECURITY.md email channel, ~30 false positives or intentional-by-design patterns
- **2026-05-16** — [MervinPraison/PraisonAI](scans/mervinpraison-praisonai.html) — 489 raw findings (largest scan yet), 5 real items, first validation of the `--ignore-file` workflow on a fresh target · ✅ **All five resolved in PR #1677 by their `praisonai-triage-agent` bot + human review (merged 2026-05-19)**
- **2026-05-15** — [Upsonic/Upsonic](scans/upsonic-upsonic.html) — 40 findings, 4 real items across SSL/SQL/subprocess/pickle, ~36 false positives or by-design patterns
- **2026-05-15** — [msoedov/agentic_security](scans/msoedov-agentic-security.html) — 9 findings, 2 real best-practice items + 1 disclosed privately, 6 false positives or out-of-scope
- **2026-05-14** — [traceloop/openllmetry](scans/traceloop-openllmetry.html) — 33 findings, 25 false-positive secrets in test cassettes, 1 best-practice item filed with the maintainer
- **2026-05-14** — [gptme/gptme](scans/gptme-gptme.html) — 57 findings, 3 best-practice improvements filed with the maintainer · ✅ **All three resolved in PR #2399 (merged 2026-05-15)**

---

## About AI PatchLab

AI PatchLab is a Python CLI that produces JSON and Markdown security reports
from a local repository path. It is designed for engineers and maintainers
who want a real audit without sending their codebase to a cloud service.

- Source: [github.com/elfrost/ai-patchlab](https://github.com/elfrost/ai-patchlab)
- Built on top of Semgrep, Gitleaks, Trivy, and pip-audit
- AI review is disabled by default and local-first when opted in

For setup and full documentation, see the project
[README](https://github.com/elfrost/ai-patchlab#readme).
