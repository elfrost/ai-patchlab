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

- **2026-06-06** — [LazyAGI/LazyLLM](scans/lazyagi-lazyllm.html) — 121 findings, **series record for the `pull_request_target` cluster** (16 sites in one workflow), Gradio ×3 + DeepSpeed RCE dep tail, classic `eval()`-based Calculator agent tool; two highest-severity items disclosed privately to a corporate maintainer address (SenseTime backing) — no public courtesy issue, post-only
- **2026-06-04** — [agentscope-ai/ReMe](scans/agentscope-ai-reme.html) — 159 findings, 3 concrete items filed (wildcard CORS + credentials on both HTTP-service entrypoints, `chromadb` CVE, Neo4j `password="neo4j"` default) · **largest SQL-identifier cluster in the series so far** (139 sites across 3 vector/file-store backends) + a new flow-DSL `exec`/`eval`-with-restricted-globals shape to watch · ✅ **All three items fixed in `reme4/` ~13h later (item-by-item response)**
- **2026-06-03** — [Q00/ouroboros](scans/q00-ouroboros.html) — 34 findings, **third "deps-are-the-thing" scan in a row** (after MemoryBear & agency-swarm) — `litellm` carries a 7-advisory stack incl. 2 criticals (auth bypass + SQL data access) reported privately via the published SECURITY.md channel; the cross-scan litellm-pin-stale pattern is now decisive
- **2026-06-02** — [VRSEN/agency-swarm](scans/vrsen-agency-swarm.html) — 48 findings, **auth-tier dep concentration that fits the project's shape**: `authlib` 1 critical + 3 auth-bypass highs and `fastmcp` 1 critical SSRF + OAuth pile, on a multi-agent OAuth/MCP framework with no Dependabot · the recurring `shell=True`-in-agent-shell-tool by-design class · ✅ **Resolved 2026-06-04 in PR #659 (~15h)**
- **2026-06-01** — [SuanmoSuanyangTechnology/MemoryBear](scans/suanmosuanyangtechnology-memorybear.html) — 196 findings, **3 named critical CVEs in a stale `api/uv.lock` (pytorch RCE-class, fastmcp SSRF, nltk Zip Slip)** on a repo with no Dependabot · 37× Jinja2-for-LLM-prompts is the new rule-misfit class of the series
- **2026-05-29** — [homeassistant-ai/ha-mcp](scans/homeassistant-ai-ha-mcp.html) — 65 findings, **zero real in-scope items**; a strict-norm repo whose maintainer published a precise threat model — every scary finding is a fixture, an intentional public demo token, a documented by-design decision, or an FP · post-only, no issue filed
- **2026-05-28** — [evalstate/fast-agent](scans/evalstate-fast-agent.html) — 36 findings, **near-clean scan where the maintainer already hand-rolled the hard mitigations** (a tar-traversal guard, a filename sanitizer before a shell call); actionable surface is two defense-in-depth hardenings + a Dependabot-lane `requests` CVE pair · ✅ **Both hardenings adopted in v0.7.13 the same day (~8h)**
- **2026-05-27** — [aurelio-labs/semantic-router](scans/aurelio-labs-semantic-router.html) — 116 findings, cleanest two-person-team scan in the series; entire actionable surface is 50 SQL-identifier sites in one Postgres-backend file + a 30-advisory dep-drift tail
- **2026-05-27** — [pixeltable/pixeltable](scans/pixeltable-pixeltable.html) — 67 findings, first scan to surface a **CVE-2007-4559-shape `tarfile.extractall` finding** on a code path that imports user-shared bundles; plus the recurring 26-site SQL-identifier class in the catalog layer
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
