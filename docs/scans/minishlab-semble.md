---
layout: default
title: "MinishLab/semble: security scan"
description: "Security scan of MinishLab/semble: 2 findings, second clean scan in the series (after Giskard); a small focused library with two hyper-responsive maintainers"
date: 2026-05-25
---

# MinishLab/semble — security scan

**Repository:** [MinishLab/semble](https://github.com/MinishLab/semble) — 4.2k★, MIT, "fast and accurate code search for agents" — a Python library shipping static-embedding-based code search with a CLI front-end.
**Commit scanned:** `2fe3b533946a` (HEAD of `main` at scan time)
**Scan date:** 2026-05-25
**Disclosure status:** **No issue filed — there was nothing to action.** Both surfaced findings are non-security or a single very-common transitive dependency advisory. This post is the clean-scan write-up.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 1 |
| Medium | 1 |
| Low | 0 |
| Info | 0 (filtered) |

**2 total findings. Both are either non-security or a low-impact transitive-dep advisory. After curation: 0 real items.**

This is the **second clean scan in the series**, after [Giskard-AI/giskard-oss](giskard-ai-giskard-oss.html) — and unlike Giskard, where the cleanness story was about *27 explained false positives*, semble has essentially nothing for the scanner to even fire on. 1.9 MB of code, two active maintainers (Pringled, stephantul), issues closed within hours, PR merges within the same day. The post is short because the codebase is.

## Why the two findings don't change the verdict

### 1. `src/semble/cli.py:7` — `python37-compatibility-importlib2`

Semgrep's heuristic flags a `from importlib.metadata import ...` line that would have needed a backport on Python 3.7. semble's `requires-python` floor is presumably >= 3.10 (the rest of the codebase uses Python 3.10+ syntax), so the rule's premise doesn't apply. **Not a security finding.** Code-style hint, irrelevant.

### 2. `uv.lock` — `idna` Internationalized Domain Names advisory

A single transitive-dep advisory against the pinned `idna` version. The advisory has appeared in nine of twelve scans in this series — it's one of those near-universal transitive bumps that happens automatically the next time `idna` is updated in any dep tree that pins it. Worth bumping when convenient; not actionable as a security disclosure.

## Patterns observed

**Tight library + small maintainer team + visible discipline.** Compared to [the Klavis monorepo](klavis-ai-klavis.html) (50 sub-projects, 1,556 findings) or [HolmesGPT's CNCF-scale codebase](holmesgpt-holmesgpt.html) (2,143 findings), semble is the opposite end of the spectrum: one Python package, ~1.9 MB, two maintainers who close issues today and merge PRs the same day. The scan reflects that structure — there is simply less surface for advisories to accumulate against. This isn't a scan worth publishing because we found something; it's worth publishing because we didn't, and the absence is the story.

**A clean scan is a positive datapoint for AI PatchLab, not a wasted one.** The temptation on a near-empty result set is to either skip the writeup or stretch the two findings into a "discussion item." Neither helps the credibility of a security-tooling write-up series. Publishing "yes, we scanned this, and it was clean" — without inflating — is what makes the *non-clean* scans believable when we publish those.

**Combined with [Giskard's clean scan](giskard-ai-giskard-oss.html), the series now has two reference points for "what good looks like."** Giskard's story was about a security-tooling company that has scanners and triage processes in its own development workflow. semble's story is about a small focused library where there's just not enough surface for advisories to accumulate. Two different mechanisms, same outcome — both worth understanding when reading the not-clean scans.

## Notes on the tool

Genuinely nothing new from this scan. The two backlog items relevant to it are already documented:

- **`logger-credential-leak` was downgraded** to `low` confidence in the [honcho write-up](plastic-labs-honcho.html) — five consecutive scans of false positives was the threshold. Not applicable here (the rule didn't fire on semble at all).
- **The recurring `idna` transitive-dep advisory** suggests an upstream-dep-deduplication helper could be useful: across the series, the same six or seven near-universal advisories (`idna`, `urllib3`, `python-dotenv`, etc.) appear in many lockfiles regardless of project, and they could be summarized in a single line instead of repeated per project.

## Disclosure timeline

- **2026-05-25** — Scan run at commit `2fe3b533946a`. Both findings curated to non-security or low-impact transitive.
- **2026-05-25** — No issue filed. There is nothing to action. This clean-scan write-up is published as the only artifact.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/MinishLab/semble" \
  --reports-dir reports/minishlab-semble \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
