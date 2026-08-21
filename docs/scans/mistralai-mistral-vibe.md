---
layout: default
title: "mistralai/mistral-vibe: security scan"
description: "Security scan of mistralai/mistral-vibe: 21 findings, a clean coding-agent scan: the git wiring is safe-by-construction (GitPython argv API, no shell"
date: 2026-06-12
---

# mistralai/mistral-vibe — security scan

**Repository:** [mistralai/mistral-vibe](https://github.com/mistralai/mistral-vibe) — 4.4k★, Apache-2.0, a minimal CLI coding agent by Mistral. Python core with a git-integration ("teleport") layer, a session/snapshot system, and a remote-workflow event translator.
**Commit scanned:** `cafb6d414747` (HEAD of `main` at scan time)
**Scan date:** 2026-06-12
**Disclosure status:** Public courtesy issue filed. Corporate-backed (Mistral) but no `SECURITY.md` or PVR is published; the curated items are routine public-CVE dependency bumps (not exploit-shaped), so a public courtesy issue — scoped tightly with reachability nuance — is the appropriate channel.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 17 |
| Medium | 4 |
| Low | 0 |
| Info | 0 (filtered) |

**21 findings. After curation: a dependency tail (gitpython, urllib3, starlette, idna — and pyjwt, which is the interesting one) plus two source findings that are both correct-by-design.** For a *coding agent* — a category whose obvious attack surface is shell/git execution and file writes — the notable result is that the git wiring is done right: GitPython's argv API (no `shell=True`, no string-built commands), and a content-hash that explicitly declares itself non-cryptographic. The real signal is a routine "bump the pinned deps + wire Dependabot" item, sharpened by a clean reachability split.

## Top findings (curated)

### 1. `gitpython==3.1.47` — three advisories, library is used (reachable)

**Tool:** pip-audit / Trivy
**Verdict:** **Real version-match on a directly-used library.**

mistral-vibe's `vibe/core/teleport/git.py` uses GitPython heavily — `Repo(...)`, `repo.git.add`, `repo.git.diff`, `repo.git.branch`, `repo.git.rev_list`, `repo.git.rev_parse`. The pinned `3.1.47` carries [CVE-2026-44243](https://github.com/advisories?query=CVE-2026-44243), [CVE-2026-44244](https://github.com/advisories?query=CVE-2026-44244), and [GHSA-mv93-w799-cj2w](https://github.com/advisories?query=GHSA-mv93-w799-cj2w) (newline injection in `config_writer()`).

Applying the [reachability discipline from the ouroboros triage](q00-ouroboros.html#patterns-observed): the **`config_writer` newline-injection (GHSA-mv93) is *not* on a reachable path** — mistral-vibe never calls `config_writer` / `set_value` / `add_section` (the only `_set_value_at_path` in the tree is a JSON-path setter in `remote_workflow_event_translator.py`, unrelated to git config). The other two CVEs sit in GitPython's broader surface that *is* exercised. So: bump `gitpython` to clear all three (low cost), but the most-severe-sounding one (config injection) isn't actually exploitable here.

### 2. `pyjwt==2.12.1` — four advisories, **declared but not imported in source (low reachability)**

**Tool:** pip-audit
**Verdict:** **Version-match, but not reachable through mistral-vibe's own code.**

`pyjwt` is pinned directly in `pyproject.toml` and carries four PYSEC advisories ([PYSEC-2026-175](https://github.com/advisories?query=PYSEC-2026-175), [-177](https://github.com/advisories?query=PYSEC-2026-177), [-178](https://github.com/advisories?query=PYSEC-2026-178), [-179](https://github.com/advisories?query=PYSEC-2026-179)). But there is **no `import jwt` anywhere in `vibe/`** — the source never constructs or verifies a JWT. In `uv.lock`, `pyjwt` appears as `{ name = "pyjwt", extra = ["crypto"] }`, i.e. it is required by a *dependency*, not by mistral-vibe's own code.

This is the same shape as the [ouroboros LiteLLM/anthropic case](q00-ouroboros.html#maintainer-response): a real version-match whose vulnerable code paths mistral-vibe doesn't exercise. The honest framing is "bump it during a dep refresh for hygiene, but it is not an applicable attack surface in this project's own usage." Worth bumping anyway since it's a one-line change, but it shouldn't be presented as an applicable vulnerability.

### 3. `urllib3==2.6.3` ×3, `starlette==1.0.0` ×3, `idna==3.13` — standard transitive web tail

**Verdict:** **Real version-matches, mixed reachability, single coordinated bump clears them.** `urllib3` (info-disclosure via cross-origin redirect, DoS) and `starlette` (security-restriction bypass; `sse-starlette` is used for the agent's streaming) are the standard 2026 web tail. `idna` `CVE-2026-45409`. A `uv lock --upgrade` clears the lot.

**No Dependabot is configured** (no `.github/dependabot.yml`), consistent with the pattern across the recent series ([MemoryBear](suanmosuanyangtechnology-memorybear.html), [agency-swarm](vrsen-agency-swarm.html), [ouroboros](q00-ouroboros.html), [Clawith](dataelement-clawith.html)). Wiring it is the durable fix.

### 4-N. Source findings — both correct-by-design

| Finding | File | Verdict |
|---|---|---|
| `insecure-hash-algorithm-sha1` | `vibe/core/session/image_snapshot.py:51` | **FP — and a model of how to do it right.** The call is `hashlib.sha1(data, usedforsecurity=False).hexdigest()` to build a content-addressed attachment filename. The developer *explicitly* passed `usedforsecurity=False` — the exact signal that tells both Python's FIPS layer and a human reader "this is a dedup hash, not a security primitive." The Semgrep rule fires on the `sha1` token regardless; the code is exemplary. |
| `non-literal-import` | `vibe/core/experiments/__init__.py:54` | **By-design** — experiment/plugin discovery via dynamic import. |

The git-execution wiring deserves an explicit callout as a *non-finding*: a coding agent is precisely the category where you expect to find `subprocess(..., shell=True)` with LLM-influenced arguments or string-concatenated git commands. mistral-vibe has neither — every git operation goes through GitPython's argv-based API (`repo.git.diff("HEAD", binary=True)`, `repo.git.rev_list("--count", ref_range)`), which handles argument boundaries safely. That's the right way to build it, and worth noting because the [recurring agent-shell-tool by-design class](vrsen-agency-swarm.html) (fast-agent, agency-swarm, ReMe, LazyLLM) is the *opposite* design choice — those ship an intentional LLM-driven shell; mistral-vibe's git layer is a constrained, safe-by-construction API surface.

## Patterns observed

**A coding agent that doesn't ship an LLM-driven shell is a different (and cleaner) shape.** Five prior agent-framework scans surfaced an intentional shell tool as a by-design finding. mistral-vibe is the first where the agent's system-interaction surface (git) is a *constrained typed API* rather than a raw shell. There's no shell-tool finding to contextualize because there's no shell tool — the git operations are a fixed vocabulary of GitPython calls. For a curated scan, "the dangerous thing you'd expect isn't here, and here's the safer construction they used instead" is as useful a data point as any finding.

**The reachability split is unusually clean on this target.** Two dependency clusters, two different reachability verdicts: `gitpython` is imported and exercised (reachable — bump it), `pyjwt` is declared but never imported in source and only pulled transitively (low reachability — bump for hygiene, not applicable as an attack surface). This is the [SCA-vs-reachability lesson](q00-ouroboros.html#patterns-observed) applying within a single scan rather than across maintainer feedback — exactly the distinction the curated report should make up front, so a reader doesn't see "4 pyjwt highs" and conclude the agent has a JWT-auth vulnerability.

**`usedforsecurity=False` is the credential-key-prefix idea applied to hashes.** Just as a `phc_…` PostHog key or a New Relic OTLP token [should downgrade a gitleaks hit](confident-ai-deepteam.html#notes-on-the-tool), an explicit `hashlib.sha1(data, usedforsecurity=False)` should downgrade (or suppress) the `insecure-hash-algorithm-sha1` Semgrep finding. The flag is an unambiguous machine-readable declaration of intent; a rule that ignores it generates exactly the kind of FP that erodes trust in the scanner. A concrete tool-side refinement: suppress the sha1/md5 hash-algorithm rules when the call site passes `usedforsecurity=False`.

## Notes on the tool

- **The 2026-06-11 UTF-8 fix held on this target**: `reports/mistralai-mistral-vibe/raw/semgrep.json` was 55,884 bytes (healthy), and per the [Clawith lesson](dataelement-clawith.html#the-scanner-bug-this-scan-caught) I verified the byte size before trusting the low semgrep count. The two semgrep findings are genuine (and both benign on inspection) — not a silent crash.
- A `usedforsecurity=False`-aware suppression for the hash-algorithm rules is the concrete scanner refinement this scan suggests, in the same family as the proposed `phc_`-prefix gitleaks downgrade and the `logger-credential-leak` downgrade already shipped.
- Reachability annotation (declared-vs-imported) would have flagged the `pyjwt` cluster automatically: a check for "is this package `import`ed anywhere in the scanned source?" cleanly separates the `gitpython` (imported) from the `pyjwt` (not imported) case.

## Disclosure timeline

- **2026-06-12** — Scan run at commit `cafb6d414747`; `semgrep.json` byte-size verified healthy (post-UTF-8-fix). Findings curated with reachability analysis: `gitpython` imported/reachable, `pyjwt` declared-but-unused, the two source findings correct-by-design.
- **2026-06-12** — Public courtesy issue [#775](https://github.com/mistralai/mistral-vibe/issues/775) filed on mistralai/mistral-vibe with the dependency refresh (gitpython + web tail), the `pyjwt` declared-but-unimported note, and a one-line Dependabot suggestion. The two source findings are noted as non-issues in this write-up.
- **2026-08-05** — Issue **closed as `not planned`, with no comment**. The substance had already landed through the project's ordinary release cadence rather than as a response to the report: `pyjwt` moved `2.12.1 → 2.13.0` by `v2.17.1` (2026-06-19, a week after filing) and `gitpython` moved `3.1.47 → 3.1.50` by `v2.19.0` (2026-07-03), then `3.1.51` and `3.1.53`. Verified against OSV at the time of closure: **`pyjwt` 2.13.0 matches zero advisories** (from nine at 2.12.1), and `gitpython` 3.1.53 clears nine of the sixteen that matched 3.1.47 — including [GHSA-mv93-w799-cj2w](https://github.com/advisories?query=GHSA-mv93-w799-cj2w), the `config_writer` newline injection this write-up singled out as the most severe-sounding one *and* correctly called unreachable here. The seven still matching 3.1.53 have no fixed version available, so "bump it" was executed as far as it can be.
  Recorded honestly: this is a **dismissal, not an acknowledgement**. No maintainer engaged with the report, and there is no evidence the bumps were caused by it. The useful read is that a routine dependency-refresh issue has little to offer a project that already refreshes dependencies on a fast release cadence — a signal about which findings are worth a maintainer's inbox, not a complaint.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/mistralai/mistral-vibe" \
  --reports-dir reports/mistralai-mistral-vibe \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
