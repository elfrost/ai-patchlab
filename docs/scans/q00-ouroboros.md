---
layout: default
title: "Q00/ouroboros: security scan"
date: 2026-06-03
---

# Q00/ouroboros — security scan

**Repository:** [Q00/ouroboros](https://github.com/Q00/ouroboros) — 4.4k★, MIT, an "Agent OS" framework (*"Stop prompting. Start specifying."*) that wires LLM agents around a specification-first orchestration model and integrates LiteLLM, Claude SDK, and an MCP layer.
**Commit scanned:** `136e9afb4d33` (HEAD of `main` at scan time)
**Scan date:** 2026-06-03
**Disclosure status:** **Post-only on the repo + private email via the published `SECURITY.md` channel.** Ouroboros ships a real `SECURITY.md` with explicit "do not open a public GitHub issue for security vulnerabilities" language and a private contact address. The LiteLLM/Claude-SDK advisory cluster was reported via that channel; this write-up covers the broader curated scan.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 17 |
| Medium | 15 |
| Low | 0 |
| Info | 0 (filtered) |

**34 total findings. After curation: the actionable surface is a single coordinated dependency refresh — `litellm` is pinned past **seven** published advisories (two critical: auth bypass + SQL data access, five high: RCE, bytecode rewriting, MCP-stdio command execution, pass-the-hash) and `claude-sdk-python` past two file-permission / TOCTOU advisories. Source code is otherwise structurally clean; gitleaks fired only on test fixtures, and the few semgrep code hits are URL-builder patterns or by-design plugin discovery.**

This is the third "deps-are-the-thing" scan in a row ([MemoryBear](suanmosuanyangtechnology-memorybear.html) → [agency-swarm](vrsen-agency-swarm.html) → ouroboros), and the second one where the dependency tail is meaningfully **shaped** by the project's purpose: an Agent OS that ships LiteLLM + Claude SDK accumulates exactly the LiteLLM + Claude SDK advisory pile.

## Top findings (curated)

### 1. `uv.lock` — `litellm` carries a seven-advisory stack including two criticals

**Tool:** Trivy
**Verdict:** **Real. Reported via the maintainer's published `SECURITY.md` private channel.**

This is the same pattern shape as the [guardrails](guardrails-ai-guardrails.html) scan in May (which carried seven `litellm` advisories on a pinned upper bound) — except more severe here because two of the seven are critical, and the high tier is RCE / unsandboxed-prompt / command-execution class:

| CVE | Class | Severity |
|---|---|---|
| [CVE-2026-35030](https://github.com/advisories?query=CVE-2026-35030) | **Authentication bypass and privilege escalation** | **Critical** |
| [CVE-2026-42208](https://github.com/advisories?query=CVE-2026-42208) | **Unauthorized data access and modification via SQL** | **Critical** |
| [CVE-2026-35029](https://github.com/advisories?query=CVE-2026-35029) | Remote code execution and privilege escalation | High |
| [CVE-2026-40217](https://github.com/advisories?query=CVE-2026-40217) | Arbitrary code execution via bytecode rewriting | High |
| [CVE-2026-42203](https://github.com/advisories?query=CVE-2026-42203) | Arbitrary code execution via unsandboxed prompt path | High |
| [CVE-2026-42271](https://github.com/advisories?query=CVE-2026-42271) | Authenticated command execution via MCP stdio test endpoint | High |
| GHSA-69X8-HRGQ-FJJ8 | Password hash exposure / pass-the-hash | High |

Per the project's own severity classification, two of these (auth bypass + RCE) sit squarely in the "Critical" tier the `SECURITY.md` defines (*"Remote code execution, credential exposure, or complete bypass of security controls"*). Filed via the private channel rather than as a public issue, per the policy.

### 2. `uv.lock` — Claude SDK for Python: 2 mediums

| CVE | Class |
|---|---|
| [CVE-2026-34450](https://github.com/advisories?query=CVE-2026-34450) | Insecure default file permissions in local-filesystem memory tool |
| [CVE-2026-34452](https://github.com/advisories?query=CVE-2026-34452) | Memory tool path-validation race condition |

For a project whose value-add is "AI Memory" + agent orchestration around the Claude SDK, these directly affect the surface. Bundled into the private report.

### 3. Standard dep tail (mediums + a few highs worth a glance)

- `aiohttp` ×4 (DoS via header/multipart classes, info-disclosure via static resource, Host-header bypass — `CVE-2026-22815`, `CVE-2026-34515`, `CVE-2026-34516`, `CVE-2026-34525`)
- `urllib3` ×2 highs (`CVE-2026-44431` info-disclosure cross-origin redirect, `CVE-2026-44432` DoS)
- `python-multipart` 1 high (`CVE-2026-42561`) + 1 medium (`CVE-2026-40347`)
- `cryptography` `CVE-2026-39892`, `requests` `CVE-2026-25645`, IDNA `CVE-2026-45409`

A single `uv lock --upgrade` pass clears most. Dependabot is not configured on the repo (no `.github/dependabot.yml`, no Dependabot PRs in the history) — same drift-by-no-bot pattern as MemoryBear and agency-swarm earlier this week.

### 4. `.github/workflows/release.yml:46` — `${{ … }}`-into-`run:` shell-injection

**Tool:** Semgrep (`run-shell-injection`)
**Verdict:** Real best-practice — the recurring workflow class. Standard `env:`-indirection fix.

### 5-N. By-design / FP

| Finding | Files | Verdict |
|---|---|---|
| 3× `gitleaks` `generic-api-key` | `tests/unit/{mcp/resources/test_handlers.py:443, observability/test_logging.py:592, orchestrator/test_mcp_config.py:191}` | **FP** — all test fixtures |
| 5× `python37-compatibility-importlib2` | Various | **Noise** — Semgrep compatibility rule, not security |
| 3× `dynamic-urllib-use-detected` | `scripts/version-check.py:74`, `src/ouroboros/copilot/model_discovery.py:160`, `tools/sync_github_project.py:97` | URL-builder patterns; typically the safe case |
| 2× `non-literal-import` | `src/ouroboros/auto/__init__.py:95`, `src/ouroboros/core/__init__.py:70` | **By-design** — plugin / feature discovery |

## Patterns observed

**Three "deps-are-the-thing" scans in a row.** [MemoryBear](suanmosuanyangtechnology-memorybear.html) (2026-06-01), [agency-swarm](vrsen-agency-swarm.html) (2026-06-02), and ouroboros (today) all share the same shape: source-code surface is largely clean, the actionable signal lives entirely in a stale `uv.lock`, and none of the three had Dependabot configured. With three back-to-back data points, the cross-scan lesson is now decisive: **shipping a `.github/dependabot.yml` template in any AI-stack Python starter would remove the largest single category of curated finding from the next year of scans.**

**LiteLLM is the new "guardrails-pattern" recurring item.** Back in [guardrails-ai/guardrails](guardrails-ai-guardrails.html) (2026-05-19) we surfaced seven litellm advisories on a pinned upper bound. Ouroboros's litellm pin is even older — same seven plus two criticals. Whenever a Python AI project imports `litellm`, the version is almost always stale relative to the current advisory stack, because litellm's velocity is high and its advisory density is also high. Worth scanning specifically for this: `litellm` is the highest "stale-pin → real-CVE" yield in the series so far.

**Strict-norm + a real published threat model continues to be the easiest case to curate respectfully.** Ouroboros's `SECURITY.md` is precise (severity definitions, 48h ack SLA, 7-day assessment, 30-day fix target, private email channel, explicit "do not open public issue"). That removes the ambiguity that the [dstack rejection](dstackai-dstack.html#maintainer-response-and-lessons) revealed: when the policy is published, the curated workflow follows it without guessing.

## Notes on the tool

- The `--ignore-samples` default (shipped 2026-05-28) again surfaces only test-fixture gitleaks hits and nothing else; the post-only path's signal-to-noise is materially better than it was a week ago.
- This is the **fourth** scan to reuse the cross-scan link to a prior post for a *recurring CVE class* (litellm pile here echoing guardrails; fastmcp/SSRF echoing Klavis on previous scans). The "this is the Nth scan with this class" framing is now load-bearing for the series narrative — worth a future tool-side feature that flags recurring-class CVE matches against prior reports.

## Disclosure timeline

- **2026-06-03** — Scan run at commit `136e9afb4d33`; findings curated against the maintainer's published `SECURITY.md`.
- **2026-06-03** — LiteLLM 7-advisory cluster (incl. 2 criticals) and Claude-SDK 2-advisory pair reported privately to the address listed in `SECURITY.md` (per the policy's explicit "do not open a public GitHub issue" requirement).
- **2026-06-03** — This public retrospective published, citing the CVE IDs (which are themselves public NVD advisories) without exploit detail.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/Q00/ouroboros" \
  --reports-dir reports/q00-ouroboros \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
