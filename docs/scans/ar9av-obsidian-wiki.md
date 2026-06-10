---
layout: default
title: "Ar9av/obsidian-wiki: security scan"
date: 2026-06-10
---

# Ar9av/obsidian-wiki — security scan

**Repository:** [Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki) — 1.8k★, MIT, a framework for AI agents to build and maintain a digital brain through Obsidian vaults. The runtime is a thin pip-installable CLI; the agent logic lives entirely inside bundled Claude Code skills (`wiki-update`, `wiki-query`) that the CLI installs into the target agent's skills directory.
**Commit scanned:** `de3a090b8f4b` (HEAD of `main` at scan time)
**Scan date:** 2026-06-10
**Disclosure status:** **Post-only — no issue filed. Clean-scan write-up.** The scanner returned zero findings at any severity level. A manual `semgrep --config=auto` re-run on `obsidian_wiki/` confirmed: `results: 0, errors: 0`. Gitleaks, Trivy, and pip-audit also returned empty result sets on a successful run.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| Info | 0 |

**0 total findings — literally zero, across all four scanners.** This is the **sixth clean scan in the series** and the cleanest one in raw count terms (Giskard had 27 all-FP, semble had 2 by-design, logfire had 27 deliberate language-feature uses, ha-mcp had 65 zero-in-scope, deepteam yesterday had 48 zero-in-scope; obsidian-wiki returned a strict zero before curation).

## Why the count is genuinely zero

The structural reason matters more than the count, because "zero findings" can also mean "scanner crashed silently." Both are checked here:

- The raw scanner outputs were each inspected. `gitleaks.json` = `[]` (3 bytes, valid empty array). `pip-audit.json` = empty dependencies object (35 bytes, no requirements file present). `trivy.json` = 2060 bytes of valid Trivy `ReportID` / `SchemaVersion` / `Results` metadata with empty vulnerability sets. `semgrep.json` was 0 bytes, which on its own is ambiguous — but a manual `semgrep --config=auto --severity=WARNING --severity=ERROR --json` re-run against `obsidian_wiki/` returned `results: 0, errors: 0`, confirming a clean run rather than a silent crash.
- The runtime *is* small enough that zero is plausible. The `obsidian_wiki/` package contains three files: `cli.py` (~457 lines), `__init__.py` (14 lines), `__main__.py` (6 lines) — about 480 lines of Python total. The rest of the repo's ~2845 Python LOC is the bundled-skill payload under `.skills/skill-creator/scripts/` (Anthropic's [skill-creator](https://github.com/anthropics/skills) skill, vendored and unmodified for the skill-evaluation harness), which is by-design out of the runtime threat model — those scripts run only when an operator chooses to evaluate or improve a skill.

The runtime CLI does file copies, symlinks bundled skill directories into agent skills folders, and writes a `~/.obsidian-wiki/config` file. There are no network calls, no subprocess executions, no deserialization of untrusted inputs, no SQL, no shell-true patterns. The architecture is intentionally "thin runtime + delegated skills" — the agent intelligence lives in the markdown + tool-spec of the skills, not in the Python.

## Top findings (curated)

None.

## Patterns observed

**The "thin runtime + delegated skills" architecture naturally produces zero-finding scans.** This is the first scan in the series of an agent-framework project where the agent logic is *not* implemented in the project's own Python code. obsidian-wiki ships two skills (`wiki-update`, `wiki-query`) that contain the agent-side intelligence as markdown SKILL.md files plus a small set of agent-callable scripts; the project's Python runtime is purely a deployment layer for those skills. This is the inverse of the architectural shape that produced the [LazyLLM 16-site `pull_request_target` cluster](lazyagi-lazyllm.html) or the [ReMe 139-site SQL identifier cluster](agentscope-ai-reme.html) — those projects own the entire agent stack in Python, which is also where the surface concentrated. obsidian-wiki's choice to delegate everything past `cli.py` to skill markdown leaves the scanner with almost nothing to fire on.

**Six clean scans now, and the shapes are diversifying.** [Giskard](giskard-ai-giskard-oss.html) was meticulous `pull_request_target` hygiene. [semble](minishlab-semble.html) was a one-purpose library with two responsive maintainers. [logfire](pydantic-logfire.html) was an observability stack whose `eval`/`exec`/`pickle` were all deliberate. [ha-mcp](homeassistant-ai-ha-mcp.html) was a precise published threat model. [deepteam](confident-ai-deepteam.html) was a strict docs/runtime split plus intentional public OSS telemetry. obsidian-wiki is the sixth shape: a thin installer whose substance lives in skill markdown that the scanner doesn't read. None of the six share the same reason for being clean.

**The "is the empty file an empty result or a silent crash?" question is now a documented step.** semgrep.json at 0 bytes is technically ambiguous — empty stdout could mean "zero matches output as nothing" or "scanner errored before writing any output." Re-running semgrep manually on the same target (`semgrep --config=auto --severity=WARNING --severity=ERROR --json obsidian_wiki/`) and confirming the same outcome is the right disambiguation step. Worth shipping as a scanner-side feature: when the orchestrator sees `semgrep.json` with byte-size `< 10`, it should emit an `info`-level finding suggesting the manual re-run rather than silently treating the output as "no matches."

## Notes on the tool

- This scan's complete file size on disk for the raw outputs (semgrep + gitleaks + trivy + pip-audit) is **under 3 KB combined** — the smallest scanner footprint in the series. A useful baseline for "what does a scan look like when there's nothing to find."
- The bundled `.skills/skill-creator/` directory contains evaluation-harness scripts (`generate_review.py`, `aggregate_benchmark.py`, etc.). These are runtime-out-of-scope for the obsidian-wiki CLI but would be the right thing to scan separately if a user were considering running the skill-evaluation harness on their own machine.
- The cross-scan rule on the `docs/yarn.lock` out-of-scope handling (proposed in the [deepteam scan notes](confident-ai-deepteam.html#notes-on-the-tool)) doesn't apply here — obsidian-wiki has no documentation site lockfile. A different category of clean.

## Disclosure timeline

- **2026-06-10** — Scan run at commit `de3a090b8f4b`; raw outputs inspected, manual `semgrep` re-run confirmed `results: 0, errors: 0`. No findings to triage; no courtesy issue filed.
- **2026-06-10** — Post-only published. Sixth clean scan in the series.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/Ar9av/obsidian-wiki" \
  --reports-dir reports/ar9av-obsidian-wiki \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
