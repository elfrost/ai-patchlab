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
