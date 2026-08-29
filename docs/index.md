---
layout: default
title: AI PatchLab Scans
description: "88 curated security scans of open-source AI agents, MCP servers and LLM apps - 18 confirmed fixes, run local-first with Semgrep, Gitleaks, Trivy and pip-audit."
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

> **Want this run privately against your own codebase?** I do independent
> security review of AI agents, MCP servers, and LLM apps —
> [**work with me →**]({{ '/work-with-me' | relative_url }}). 88 scans, 18 confirmed fixes, methodology in the open.

> **OpenAI just launched [Daybreak](https://openai.com/index/daybreak-securing-the-world/) and Patch the Planet.**
> Same remediation loop, opposite trade-off: their path is a cloud frontier model;
> this one keeps your code on your disk. [Why local-first still matters →]({{ '/daybreak-and-local-first' | relative_url }})

> **New — the whole series, read end to end.**
> Measured across the first 83 scans: the four tools produced **10,635
> findings**; **56** were real.
> Here is what they reliably get wrong, the six classes of bug no rule can see,
> and why half the scans found nothing.
> [**10,635 findings, 56 that mattered →**]({{ '/what-83-scans-found' | relative_url }})

## Six scans worth reading

If you only read a handful, read these. Each one shows a different part of the
job — and the last two show it going *against* the interesting answer, which is
the part that makes the other 81 worth trusting.

**[jgravelle/jcodemunch-mcp](scans/jgravelle-jcodemunch-mcp.html)** — *a finding
concrete enough to be adopted.* A path-confinement escape, reported with a
working fix. The pull request never merged — a contributor licence agreement
expired first — so the maintainer wrote the diff themselves and said so in the
release notes. Catching the bug *by resolution* rather than by pattern exposed
that the same rule already had three separate spellings in the codebase; there
is one now, with a test that fails on a fourth.

**[EvoScientist/EvoScientist](scans/evoscientist-evoscientist.html)** — *the
finding no tool ranked.* An inverted conditional meant two webhook channels
verified their signature only when a caller-controlled flag asked them to.
Thirty-nine findings in the report; this was not one of them. A passer-by
contributor reproduced the bypass on both channels and shipped the fix with
nine regression tests.

**[54yyyu/zotero-mcp](scans/54yyyu-zotero-mcp.html)** — *curation is the
product.* Four scanner findings became six confirmed-real items, and only one
of the six came from a scanner. All six were fixed and merged about six hours
later; the next release was cut nine minutes after the issue closed.

**[whiteguo233/OpenBiliClaw](scans/whiteguo233-openbiliclaw.html)** — *when two
tools disagree, the disagreement is the finding.* Trivy read the lockfile and
reported 63 advisories; pip-audit resolved the same project's declared version
floors and reported zero. Both were right. The project ships both as real
install paths, so the containerised deployment was clean and the recommended
host install was not — from the same commit. Fixed and merged the same day, as
the single-package bump the issue asked for rather than a blanket lockfile
refresh.

**[TracecatHQ/tracecat](scans/tracecathq-tracecat.html)** — *a negative result,
published.* A security-automation platform, scanned the same way as everything
else, with every promising lead followed to a dead end. Nothing real to report,
so that is what the write-up says. A method that can only return "yes" is not a
method.

**[Mai-with-u/MaiBot](scans/mai-with-u-maibot.html)** — *the fifty-two findings
that weren't.* An automated sweep flagged 52 of 404 routes as unauthenticated,
including an entire router that visibly lacked the dependency its siblings all
carried. Reading the code dissolved it: the module imported the auth function
under an alias and called it in the handler body. Of the 404 routes, 378
enforce auth and the 9 genuinely public ones are health, version, robots,
login and static assets. Fifty-two flagged, none reported.

## How these scans work

- Each scan targets a public repository at a specific commit.
- Findings are curated: noise filtered out, top items highlighted.
- Critical issues are reported to maintainers under responsible disclosure
  before being published here in full detail.
- Where a project's security policy forbids public vulnerability reports, the
  finding is withheld from this page too — those rows read *private*.
- Posts focus on patterns and lessons — not exploit walkthroughs.

## All scans

88 scans, newest first. **Findings** is the raw count the tools produced;
**Real** is what survived curation. The gap between those two columns is the
entire job.

| Date | Repository | Findings | Real | Outcome |
|---|---|---:|---|---|
| 2026-08-29 | [ginlix-ai/LangAlpha](scans/ginlix-ai-langalpha.html) | 372 | 1 real | open |
| 2026-08-28 | [Ontos-AI/knowhere](scans/ontos-ai-knowhere.html) | 129 | 1 real — withheld | private |
| 2026-08-27 | [Zleap-AI/SAG](scans/zleap-ai-sag.html) | 60 | 1 real | open |
| 2026-08-26 | [ascending-llc/jarvis-registry](scans/ascending-llc-jarvis-registry.html) | 235 | 1 real — withheld | private |
| 2026-08-25 | [langflow-ai/openrag](scans/langflow-ai-openrag.html) | 213 | 1 real — withheld | private |
| 2026-08-20 | [whiteguo233/OpenBiliClaw](scans/whiteguo233-openbiliclaw.html) | 373 | 1 real | **fixed** |
| 2026-08-19 | [Mai-with-u/MaiBot](scans/mai-with-u-maibot.html) | 373 | 1 real — withheld | private |
| 2026-08-18 | [roflcoopter/viseron](scans/roflcoopter-viseron.html) | 399 | 1 real — withheld | private |
| 2026-08-17 | [zilliztech/memsearch](scans/zilliztech-memsearch.html) | 90 | 1 real | **fixed** |
| 2026-08-16 | [liaohch3/claude-tap](scans/liaohch3-claude-tap.html) | 104 | 1 real — withheld | private |
| 2026-08-15 | [TracecatHQ/tracecat](scans/tracecathq-tracecat.html) | 212 | 0 real | — |
| 2026-08-14 | [datalayer/jupyter-mcp-server](scans/datalayer-jupyter-mcp-server.html) | 37 | 0 real | private |
| 2026-08-13 | [lightseekorg/tokenspeed](scans/lightseekorg-tokenspeed.html) | 181 | 1 real — withheld | private |
| 2026-08-12 | [jgravelle/jcodemunch-mcp](scans/jgravelle-jcodemunch-mcp.html) | 49 | 0 real | **fixed** |
| 2026-08-11 | [semantica-agi/Semantica](scans/semantica-agi-semantica.html) | 60 | 1 real — withheld | private |
| 2026-08-10 | [datascale-ai/OpenTalking](scans/datascale-ai-opentalking.html) | 93 | 1 real | — |
| 2026-08-09 | [NeptuneHub/AudioMuse-AI](scans/neptunehub-audiomuse-ai.html) | 265 | 1 real — withheld | private |
| 2026-08-08 | [theroyallab/tabbyAPI](scans/theroyallab-tabbyapi.html) | 18 | 2 real | — |
| 2026-08-07 | [huangruiteng/loopx](scans/huangruiteng-loopx.html) | 57 | 1 real — withheld | **fixed** |
| 2026-08-06 | [nottelabs/notte](scans/nottelabs-notte.html) | 226 | 1 real — withheld | private |
| 2026-08-05 | [Vexa-ai/vexa](scans/vexa-ai-vexa.html) | 297 | 1 real — withheld | private |
| 2026-08-04 | [ArcReel/ArcReel](scans/arcreel-arcreel.html) | 82 | 1 real — withheld | private |
| 2026-08-03 | [the-momentum/open-wearables](scans/the-momentum-open-wearables.html) | 145 | 2 real | — |
| 2026-08-02 | [Observal/Observal](scans/observal-observal.html) | 1,117 | 1 real — withheld | private |
| 2026-08-01 | [repowise-dev/repowise](scans/repowise-dev-repowise.html) | 86 | 2 real — withheld | private |
| 2026-07-31 | [rocketride-org/rocketride-server](scans/rocketride-org-rocketride-server.html) | 268 | 1 real — withheld | private |
| 2026-07-30 | [pipeshub-ai/pipeshub-ai](scans/pipeshub-ai-pipeshub-ai.html) | 389 | 2 real — withheld | private |
| 2026-07-29 | [Project-N-E-K-O/N.E.K.O](scans/project-n-e-k-o-n-e-k-o.html) | 783 | 1 real | **fixed** |
| 2026-07-28 | [EvoScientist/EvoScientist](scans/evoscientist-evoscientist.html) | 39 | 1 real | **fixed** |
| 2026-07-27 | [dimensionalOS/dimos](scans/dimensionalos-dimos.html) | 280 | 0 real | — |
| 2026-07-26 | [CodeGraphContext/CodeGraphContext](scans/codegraphcontext-codegraphcontext.html) | 112 | 0 real | — |
| 2026-07-25 | [Osmantic/ODS](scans/osmantic-ods.html) | 73 | 0 real | — |
| 2026-07-24 | [gpustack/gpustack](scans/gpustack-gpustack.html) | 136 | 0 real | — |
| 2026-07-23 | [EverMind-AI/Raven](scans/evermind-ai-raven.html) | 87 | 0 real | — |
| 2026-07-22 | [mixelpixx/KiCAD-MCP-Server](scans/mixelpixx-kicad-mcp-server.html) | 29 | 0 real | — |
| 2026-07-21 | [ucbepic/docetl](scans/ucbepic-docetl.html) | 124 | 1 real | — |
| 2026-07-20 | [ModelEngine-Group/nexent](scans/modelengine-group-nexent.html) | 115 | 0 real | — |
| 2026-07-19 | [vitali87/code-graph-rag](scans/vitali87-code-graph-rag.html) | 22 | 1 real | **fixed** |
| 2026-07-18 | [algorithmicsuperintelligence/optillm](scans/algorithmicsuperintelligence-optillm.html) | 57 | 1 real | — |
| 2026-07-17 | [IBM/mcp-context-forge](scans/ibm-mcp-context-forge.html) | 946 | 0 real | — |
| 2026-07-16 | [a2aproject/a2a-python](scans/a2aproject-a2a-python.html) | 20 | 0 real | — |
| 2026-07-15 | [mnemosyne-oss/mnemosyne](scans/mnemosyne-oss-mnemosyne.html) | 195 | 0 real | — |
| 2026-07-14 | [datachain-ai/datachain](scans/datachain-ai-datachain.html) | 35 | 0 real | — |
| 2026-07-13 | [potpie-ai/potpie](scans/potpie-ai-potpie.html) | 96 | 0 real | — |
| 2026-07-10 | [sooperset/mcp-atlassian](scans/sooperset-mcp-atlassian.html) | 71 | 0 real | — |
| 2026-07-09 | [VectifyAI/OpenKB](scans/vectifyai-openkb.html) | 23 | 0 real | — |
| 2026-07-07 | [atilaahmettaner/tradingview-mcp](scans/atilaahmettaner-tradingview-mcp.html) | 28 | 0 real | — |
| 2026-07-03 | [AgentEra/Agently](scans/agentera-agently.html) | 25 | 1 real | **fixed** |
| 2026-07-02 | [UKGovernmentBEIS/inspect_ai](scans/ukgovernmentbeis-inspect-ai.html) | 161 | 0 real | — |
| 2026-07-01 | [Soju06/codex-lb](scans/soju06-codex-lb.html) | 76 | 0 real | — |
| 2026-06-30 | [openagents-org/openagents](scans/openagents-org-openagents.html) | 680 | 0 real | — |
| 2026-06-28 | [SwanHubX/SwanLab](scans/swanhubx-swanlab.html) | 32 | 0 real | — |
| 2026-06-26 | [ag2ai/ag2](scans/ag2ai-ag2.html) | 73 | 0 real | — |
| 2026-06-25 | [Kiln-AI/Kiln](scans/kiln-ai-kiln.html) | 150 | 0 real | — |
| 2026-06-24 | [maziyarpanahi/openmed](scans/maziyarpanahi-openmed.html) | 44 | 0 real | — |
| 2026-06-23 | [stickerdaniel/linkedin-mcp-server](scans/stickerdaniel-linkedin-mcp-server.html) | 6 | 0 real | — |
| 2026-06-21 | [taylorwilsdon/google_workspace_mcp](scans/taylorwilsdon-google-workspace-mcp.html) | 16 | 0 real | — |
| 2026-06-19 | [xerrors/Yuxi](scans/xerrors-yuxi.html) | 70 | see write-up | **fixed** |
| 2026-06-15 | [harbor-framework/harbor](scans/harbor-framework-harbor.html) | 570 | see write-up | — |
| 2026-06-12 | [mistralai/mistral-vibe](scans/mistralai-mistral-vibe.html) | 21 | 0 real | — |
| 2026-06-11 | [dataelement/Clawith](scans/dataelement-clawith.html) | 54 | see write-up | — |
| 2026-06-10 | [Ar9av/obsidian-wiki](scans/ar9av-obsidian-wiki.html) | — | 0 real | — |
| 2026-06-09 | [confident-ai/deepteam](scans/confident-ai-deepteam.html) | 48 | 0 real | — |
| 2026-06-08 | [54yyyu/zotero-mcp](scans/54yyyu-zotero-mcp.html) | 4 | 6 real | **fixed** |
| 2026-06-06 | [LazyAGI/LazyLLM](scans/lazyagi-lazyllm.html) | 121 | see write-up | — |
| 2026-06-04 | [agentscope-ai/ReMe](scans/agentscope-ai-reme.html) | 159 | 3 real | **fixed** |
| 2026-06-03 | [Q00/ouroboros](scans/q00-ouroboros.html) | 34 | see write-up | — |
| 2026-06-02 | [VRSEN/agency-swarm](scans/vrsen-agency-swarm.html) | 48 | see write-up | **fixed** |
| 2026-06-01 | [SuanmoSuanyangTechnology/MemoryBear](scans/suanmosuanyangtechnology-memorybear.html) | 196 | see write-up | — |
| 2026-05-29 | [homeassistant-ai/ha-mcp](scans/homeassistant-ai-ha-mcp.html) | 65 | 0 real | — |
| 2026-05-28 | [evalstate/fast-agent](scans/evalstate-fast-agent.html) | 36 | 0 real | **fixed** |
| 2026-05-27 | [aurelio-labs/semantic-router](scans/aurelio-labs-semantic-router.html) | 116 | see write-up | partial |
| 2026-05-27 | [pixeltable/pixeltable](scans/pixeltable-pixeltable.html) | 67 | see write-up | **fixed** |
| 2026-05-26 | [dstackai/dstack](scans/dstackai-dstack.html) | 163 | 3 real | — |
| 2026-05-26 | [pydantic/logfire](scans/pydantic-logfire.html) | 27 | 0 real | — |
| 2026-05-25 | [MinishLab/semble](scans/minishlab-semble.html) | 2 | 0 real | — |
| 2026-05-25 | [plastic-labs/honcho](scans/plastic-labs-honcho.html) | 315 | see write-up | — |
| 2026-05-21 | [HolmesGPT/holmesgpt](scans/holmesgpt-holmesgpt.html) | 2,143 | see write-up | — |
| 2026-05-21 | [dograh-hq/dograh](scans/dograh-hq-dograh.html) | 69 | see write-up | **fixed** |
| 2026-05-20 | [Klavis-AI/klavis](scans/klavis-ai-klavis.html) | 1,556 | see write-up | — |
| 2026-05-20 | [Giskard-AI/giskard-oss](scans/giskard-ai-giskard-oss.html) | 27 | 0 real | — |
| 2026-05-19 | [guardrails-ai/guardrails](scans/guardrails-ai-guardrails.html) | 17 | see write-up | — |
| 2026-05-19 | [airweave-ai/airweave](scans/airweave-ai-airweave.html) | 46 | see write-up | — |
| 2026-05-16 | [MervinPraison/PraisonAI](scans/mervinpraison-praisonai.html) | 489 | 5 real | **fixed** |
| 2026-05-15 | [Upsonic/Upsonic](scans/upsonic-upsonic.html) | 40 | 4 real | — |
| 2026-05-15 | [msoedov/agentic_security](scans/msoedov-agentic-security.html) | 9 | 2 real | **fixed** |
| 2026-05-14 | [traceloop/openllmetry](scans/traceloop-openllmetry.html) | 33 | 1 real | — |
| 2026-05-14 | [gptme/gptme](scans/gptme-gptme.html) | 57 | 3 real | **fixed** |

*Older entries predate the "N real" convention and are marked "see write-up".
Every scan's original summary is preserved in the
[full scan log]({{ '/scan-log' | relative_url }}).*

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
