---
layout: default
title: "Q00/ouroboros: security scan"
date: 2026-06-03
---

# Q00/ouroboros — security scan

**Repository:** [Q00/ouroboros](https://github.com/Q00/ouroboros) — 4.4k★, MIT, an "Agent OS" framework (*"Stop prompting. Start specifying."*) that wires LLM agents around a specification-first orchestration model and integrates LiteLLM, Claude SDK, and an MCP layer.
**Commit scanned:** `136e9afb4d33` (HEAD of `main` at scan time)
**Scan date:** 2026-06-03
**Disclosure status:** **Post-only on the repo + private email via the published `SECURITY.md` channel — and the maintainer triaged within their 48h SLA with a detailed reachability analysis and specific factual corrections, applied to this post on 2026-06-08.** Ouroboros ships a real `SECURITY.md` with explicit "do not open a public GitHub issue for security vulnerabilities" language and a private contact address. The LiteLLM/Claude-SDK advisory cluster was reported via that channel; the maintainer confirmed all nine advisories are *genuine version matches* but **not reachable in Ouroboros's actual library-only usage** (Ouroboros runs no LiteLLM Proxy and does not use the Anthropic SDK's local-filesystem memory tool). The tail-dep findings stand and are scheduled for a single coordinated refresh; corrections are folded into the body below. See [Maintainer response](#maintainer-response) for the full quoted record.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 17 |
| Medium | 15 |
| Low | 0 |
| Info | 0 (filtered) |

**34 total findings. After curation: the actionable surface is a single coordinated dependency refresh. The raw `litellm` 7-advisory cluster (2 critical, 5 high) and `anthropic` 2-advisory pair were initially flagged as critical/high because the *upstream* CVSS scores are accurate — but Ouroboros's library-only usage of both packages means *none of those nine items are reachable in this project's actual code paths* (the maintainer confirmed this by exhaustive source sweep — every LiteLLM advisory lives in the unused LiteLLM Proxy Server surface, and the anthropic memory-tool advisories live in the unused `BetaLocalFilesystemMemoryTool`). The genuinely-actionable items reduce to the tail (`cryptography 46.0.5 → 46.0.7` carrying the 9.8 buffer-overflow CVE is the only one *on Ouroboros's runtime path*, plus `aiohttp` / `urllib3` / `python-multipart` / `requests` server-side/transitive bumps) plus one `${{ }}`-in-`run:` shell-injection in `release.yml`. Source code is otherwise structurally clean. Severity counts above are raw scanner output; **the applicability-mapped picture is "informational / dependency-hygiene," not critical** — corrected per the [maintainer response](#maintainer-response).**

This is the third "deps-are-the-thing" scan in a row ([MemoryBear](suanmosuanyangtechnology-memorybear.html) → [agency-swarm](vrsen-agency-swarm.html) → ouroboros), and the second one where the dependency tail is meaningfully **shaped** by the project's purpose: an Agent OS that ships LiteLLM + Claude SDK accumulates exactly the LiteLLM + Claude SDK advisory pile.

## Top findings (curated)

### 1. `uv.lock` — `litellm` carries a seven-advisory stack — but **none reachable in this project**

**Tool:** Trivy
**Verdict:** **Real version-matches, not applicable to Ouroboros. Reported via the maintainer's `SECURITY.md` private channel; reachability triage came back negative on every item.**

This started as the same pattern shape as the [guardrails](guardrails-ai-guardrails.html) scan in May (seven `litellm` advisories on a pinned upper bound). The maintainer triage clarified an important structural point: **every one of these advisories lives in the LiteLLM Proxy Server surface — and Ouroboros uses LiteLLM only as an in-process SDK client** (`litellm.acompletion()`, `litellm.token_counter()`, `litellm.ModelResponse`, exception classes). No proxy process, no DB, no auth/key layer, no admin endpoints. Per the maintainer's source sweep, none of these code paths are imported, instantiated, or network-exposed.

| CVE | Upstream class | Affected surface | Reachable in Ouroboros? |
|---|---|---|---|
| [CVE-2026-35030](https://github.com/advisories?query=CVE-2026-35030) | Authentication bypass and privilege escalation | LiteLLM **Proxy** JWT/OIDC userinfo cache (off by default) | **No** — no proxy run |
| [CVE-2026-42208](https://github.com/advisories?query=CVE-2026-42208) | Unauthorized data access and modification via SQL | LiteLLM **Proxy** API-key DB query (pre-auth SQLi) | **No** — no proxy, no DB |
| [CVE-2026-35029](https://github.com/advisories?query=CVE-2026-35029) | Remote code execution and privilege escalation | LiteLLM **Proxy** `/config/update` | **No** |
| [CVE-2026-40217](https://github.com/advisories?query=CVE-2026-40217) | Arbitrary code execution via bytecode rewriting | LiteLLM **Proxy** `/guardrails/test_custom_code` | **No** |
| [CVE-2026-42203](https://github.com/advisories?query=CVE-2026-42203) | Arbitrary code execution via unsandboxed prompt path | LiteLLM **Proxy** `/prompts/test` | **No** |
| [CVE-2026-42271](https://github.com/advisories?query=CVE-2026-42271) | Authenticated command execution via the LiteLLM **Proxy** MCP-Gateway preview endpoints (`/mcp-rest/test/*`) | LiteLLM **Proxy** (the MCP-Gateway preview — unrelated to Ouroboros's own MCP layer; same acronym, no shared code) | **No** |
| GHSA-69X8-HRGQ-FJJ8 | Password hash exposure / pass-the-hash | LiteLLM **Proxy** user-management endpoints | **No** |

**Earlier framing correction:** this section originally treated the SCA flags as criticals for Ouroboros and described CVE-2026-42271 as "particularly relevant given Ouroboros's MCP layer." Both framings overstate the exposure — the advisory affects LiteLLM Proxy's `/mcp-rest/test/*` MCP-Gateway endpoints, which are a different component from Ouroboros's own MCP server (they only share the acronym). Corrected per maintainer triage; the lesson on the methodology side is in [Patterns observed](#patterns-observed).

### 2. `uv.lock` — `anthropic` SDK: 2 mediums — **not applicable to Ouroboros**

**Package correction:** these advisories affect the `anthropic` PyPI package — not `claude-agent-sdk`, which is a separate dependency. The earlier "Claude SDK for Python" framing conflated them; the affected artifact is `anthropic`.

| CVE | Upstream class | Affected feature | Reachable in Ouroboros? |
|---|---|---|---|
| [CVE-2026-34450](https://github.com/advisories?query=CVE-2026-34450) | Insecure default file permissions | `anthropic` SDK's `BetaLocalFilesystemMemoryTool` | **No** — Ouroboros uses `AsyncAnthropic` as an API client only, and additionally requires a local attacker with write access to the memory directory |
| [CVE-2026-34452](https://github.com/advisories?query=CVE-2026-34452) | Path-validation race condition | `anthropic` SDK's `BetaLocalFilesystemMemoryTool` | **No** — same reason |

**Earlier framing correction:** this section originally said "for a project whose value-add is AI memory + agent orchestration around the Claude SDK, these directly affect the surface." That's wrong on two counts and worth being explicit about. (1) **Ouroboros's memory feature is its own subsystem — it is not the `anthropic` SDK's `BetaLocalFilesystemMemoryTool`.** The two share the word "memory" but no code. (2) The advisories require a *local* attacker with write access to the memory directory, which makes the realistic threat low even for users of the actual `BetaLocalFilesystemMemoryTool` feature. Corrected per maintainer triage.

### 3. Standard dep tail — the **actually-actionable** part of the curated scan

This is the section that survived the reachability triage as genuinely worth a refresh. The runtime-on-path standout is `cryptography`:

- **`cryptography` `CVE-2026-39892` (9.8 buffer overflow via non-contiguous buffers) — on Ouroboros's runtime path.** `cryptography 46.0.5` → `46.0.7` is the one item the maintainer triage prioritized; the others are server-side parsing / low-level-API / non-default-utility paths, several transitive.
- `aiohttp` ×4 (DoS via header/multipart, info-disclosure via static resource, Host-header bypass — `CVE-2026-22815`, `CVE-2026-34515`, `CVE-2026-34516`, `CVE-2026-34525`) — server-side parsing surface.
- `urllib3` ×2 — `CVE-2026-44431` info-disclosure cross-origin redirect, `CVE-2026-44432` excessive HTTP response handling. **NVD rates both Medium** (an earlier framing here said High; corrected).
- `python-multipart` `CVE-2026-42561` + `CVE-2026-40347` — multipart parsing.
- `requests` `CVE-2026-25645`, IDNA `CVE-2026-45409`.

Per the maintainer response: a single coordinated refresh is planned (`litellm` to a verified-clean `>=1.83.7`, `anthropic` `>=0.87.0`, `cryptography` `>=46.0.7`, `aiohttp` `>=3.13.4`, `urllib3` `>=2.7.0`, `python-multipart` `>=0.0.27`, `requests` `>=2.33.0`), plus the `release.yml` `${{ github.ref_name }}` `env:`-indirection hardening, plus an evaluation of adding `dependabot.yml`. Notably, this will *not* be a blanket `uv lock --upgrade` — the maintainer pinned deliberately to verified-clean versions specifically because of LiteLLM's March 2026 PyPI supply-chain incident (the malicious `1.82.7`/`1.82.8` uploads). The on-offer PR was declined for that reason, which is a reasonable supply-chain-hygiene posture.

Dependabot is not configured on the repo (no `.github/dependabot.yml`, no Dependabot PRs in the history); the maintainer's response indicates they'll evaluate adding it. Same drift-by-no-bot pattern as [MemoryBear](suanmosuanyangtechnology-memorybear.html) and [agency-swarm](vrsen-agency-swarm.html) earlier this week.

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

**Applicability/reachability is the curation dimension this scan was missing — and the maintainer triage revealed it.** This is the most important lesson of the engagement. SCA tools (and our curated reports) flag *version matches*: package X is pinned at a version within an advisory's affected range. That signal is real and worth surfacing — but it conflates "the version is vulnerable" with "this project is exposed to that vulnerability." Ouroboros pins a vulnerable `litellm` and a vulnerable `anthropic`, but uses neither package's vulnerable code paths: LiteLLM as an in-process SDK client (not the Proxy), `anthropic` as an API client (not the local-filesystem memory tool). All nine advisories are *real*. None are *reachable*. The maintainer's exhaustive source sweep is the right primary-source-of-truth, and the methodology lesson here is that the curated post should distinguish version-match from reachability up front — when the project ships only a subset of a package's surface, a "Critical 2 / High 17" summary header reads as the reachable picture even when most of the count is upstream-proxy code Ouroboros doesn't run. Future scans need an applicability column (or at least a footnote when the surface is library-only).

**Three "deps-are-the-thing" scans in a row.** [MemoryBear](suanmosuanyangtechnology-memorybear.html) (2026-06-01), [agency-swarm](vrsen-agency-swarm.html) (2026-06-02), and ouroboros (today) all share the same shape: source-code surface is largely clean, the actionable signal lives in a stale `uv.lock`, and none of the three had Dependabot configured. With three back-to-back data points, the cross-scan lesson is decisive: **shipping a `.github/dependabot.yml` template in any AI-stack Python starter would remove the largest single category of curated finding from the next year of scans.** That said, the ouroboros engagement adds a refinement: a maintainer with strong supply-chain hygiene may prefer deliberate pinning to verified-clean versions over a blanket bot bump, especially in the wake of an upstream supply-chain incident (LiteLLM's malicious-PyPI-upload episode in March 2026). "Wire Dependabot" should be the default; "wire Dependabot configured to require manual review for high-velocity packages with a recent supply-chain incident" is the better default.

**LiteLLM is the new "guardrails-pattern" recurring SCA item — *for projects that run the Proxy*.** Back in [guardrails-ai/guardrails](guardrails-ai-guardrails.html) (2026-05-19) we surfaced seven litellm advisories. The same seven re-surfaced here (plus two criticals added since), and on multiple of the post-2026-06-01 scans. The pattern needs the applicability qualifier: every one of LiteLLM's recent CVEs lives in the Proxy Server surface, so the scoring depends entirely on whether the project runs the Proxy or only uses the SDK. Future LiteLLM mentions in our posts will name the surface (Proxy vs SDK) explicitly. The right tool-side feature is a per-CVE "affects surface X" tag derived from the advisory body, surfaced in the curated output.

**Strict-norm + a real published threat model continues to be the easiest case to curate respectfully.** Ouroboros's `SECURITY.md` is precise (severity definitions, 48h ack SLA, 7-day assessment, 30-day fix target, private email channel, explicit "do not open public issue"). That removes the ambiguity that the [dstack rejection](dstackai-dstack.html#maintainer-response-and-lessons) revealed: when the policy is published, the curated workflow follows it without guessing.

## Notes on the tool

- The `--ignore-samples` default (shipped 2026-05-28) again surfaces only test-fixture gitleaks hits and nothing else; the post-only path's signal-to-noise is materially better than it was a week ago.
- This is the **fourth** scan to reuse the cross-scan link to a prior post for a *recurring CVE class* (litellm pile here echoing guardrails; fastmcp/SSRF echoing Klavis on previous scans). The "this is the Nth scan with this class" framing is now load-bearing for the series narrative — worth a future tool-side feature that flags recurring-class CVE matches against prior reports.

## Disclosure timeline

- **2026-06-03** — Scan run at commit `136e9afb4d33`; findings curated against the maintainer's published `SECURITY.md`.
- **2026-06-03** — This public retrospective published, citing the CVE IDs (which are themselves public NVD advisories) without exploit detail.
- **2026-06-04** — `litellm` 7-advisory cluster and `anthropic` 2-advisory pair reported privately to the address listed in `SECURITY.md` (per the policy's explicit "do not open a public GitHub issue" requirement).
- **2026-06-07** — ✉️ Maintainer acknowledgement well within the 48h `SECURITY.md` SLA. Detailed item-by-item reachability triage: all nine advisories confirmed as *genuine version-matches*, but **none reachable in Ouroboros's library-only usage** (LiteLLM used as an in-process SDK client, not the Proxy; `anthropic` used as an API client, not the local-filesystem memory tool). Tail items confirmed valid; coordinated refresh scheduled with deliberate version pinning. Offered PR declined per the maintainer's supply-chain-hygiene posture (see [Maintainer response](#maintainer-response)).
- **2026-06-08** — Post corrected per the maintainer triage: applicability columns added to the two main tables, the "Claude SDK for Python" framing replaced with the correct `anthropic` package name, the "Ouroboros memory feature = `BetaLocalFilesystemMemoryTool`" conflation removed, the "LiteLLM MCP-stdio" framing rewritten to clarify it's LiteLLM Proxy's `/mcp-rest/test/*` (unrelated to Ouroboros's own MCP layer), and urllib3 severity corrected to Medium per NVD.

## Maintainer response

The maintainer's response is the cleanest item-by-item reachability triage we've received on a private disclosure in the series and is reproduced here as part of the honest record. Load-bearing passages, lightly truncated:

> Up front, to be fair: all nine advisories are genuine, and our pinned versions do fall within their affected ranges — a version-match SCA flag is entirely legitimate. Our triage conclusion, however, is that none of the nine are reachable in Ouroboros's actual usage, for a structural reason.

> **LiteLLM (7 advisories) — not applicable.** Ouroboros imports litellm purely as an in-process SDK client. The complete surface we touch is `litellm.acompletion()`, `litellm.token_counter()`, `litellm.ModelResponse`, and a handful of exception classes. We do not run the LiteLLM Proxy Server — no proxy process, no database, no auth/key layer, no admin/management HTTP endpoints anywhere in the repository (verified by an exhaustive source sweep). All seven advisories live exclusively in proxy-server surfaces […]. None of these code paths are imported, instantiated, or network-exposed when LiteLLM is used as a library.

> **Anthropic SDK (2 advisories) — not applicable.** […] Ouroboros does not use the SDK's filesystem memory-tool feature — our anthropic usage is a direct `AsyncAnthropic` API client — and both issues additionally require a local attacker with write access to the memory directory.

> A note on this one, since the public page states these "directly affect the surface" for a project whose value-add is "AI Memory": Ouroboros's memory feature is its own subsystem; it is not the Anthropic SDK's `BetaLocalFilesystemMemoryTool`. The two are unrelated, so that applicability claim doesn't hold here — we'd ask for a small correction […].

> **Tail dependencies — valid version-matches; we'll refresh them.** Your tail findings are accurate […]. Practical applicability is low (most are server-side parsing, low-level-API, or non-default-utility paths, and several are transitive), but we'll fold them into a single dependency refresh regardless. We're prioritizing cryptography → 46.0.7 (CVE-2026-39892, the 9.8 buffer-overflow) since cryptography is actually on our runtime path. One small data point: NVD rates the two urllib3 items (CVE-2026-44431/44432) as Medium, not High.

> **Two factual corrections, in the spirit of accuracy:** The "MCP stdio test endpoint" item (CVE-2026-42271) is LiteLLM Proxy's MCP Gateway preview endpoints (`/mcp-rest/test/*`) — unrelated to Ouroboros's own MCP server. They share the acronym but no code […]. The two "Claude SDK for Python" items affect the `anthropic` PyPI package, not `claude-agent-sdk`, which is a separate dependency and not the vulnerable artifact.

> **On severity.** Our SECURITY.md ladder scopes severity to impact on the ouroboros-ai package. Mapped to Ouroboros's actual exposure, the reported cluster is informational / dependency-hygiene rather than Critical/High — the upstream CVSS numbers are accurate, but they describe a deployment surface (the proxy, the memory tool) Ouroboros doesn't present.

> **What we'll do (hygiene, on our own schedule):** a single coordinated refresh — litellm to a verified-clean >=1.83.7, anthropic >=0.87.0, cryptography >=46.0.7, aiohttp >=3.13.4, urllib3 >=2.7.0, python-multipart >=0.0.27, requests >=2.33.0 — plus the release.yml `${{ github.ref_name }}` env:-indirection hardening, and we'll evaluate adding dependabot.yml.

> **On the offered PR:** thank you, but we'll apply the bumps ourselves. LiteLLM's own March 2026 PyPI supply-chain incident (the malicious 1.82.7/1.82.8 uploads) is exactly why we pin deliberately to verified-clean versions rather than via a blanket `uv lock --upgrade`, so we'd like to keep that change in-house.

The full response is on file privately; the passages quoted above are the load-bearing ones for the corrections applied to this post.

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
