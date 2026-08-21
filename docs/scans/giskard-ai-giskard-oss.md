---
layout: default
title: "Giskard-AI/giskard-oss: security scan"
description: "Security scan of Giskard-AI/giskard-oss: 27 findings, all false positives — first clean scan in the series"
date: 2026-05-20
---

# Giskard-AI/giskard-oss — security scan

**Repository:** [Giskard-AI/giskard-oss](https://github.com/Giskard-AI/giskard-oss) — 5.4k★, Apache-2.0, open-source evaluation and testing library for LLM agents.
**Commit scanned:** `09eed260107d` (HEAD of `main` at scan time)
**Scan date:** 2026-05-20
**Disclosure status:** **No issue filed — there was nothing to action.** Every finding on this scan is a false positive or an already-mitigated pattern. This post is published as a clean-scan write-up, not a disclosure.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 26 |
| Medium | 1 |
| Low | 0 |
| Info | 0 (filtered) |

**27 total findings. After curation: 0 real items. All 27 are false positives, public-by-design values, or patterns the maintainers have already explicitly mitigated.**

This is the first scan in the eight-repo series to come back with **zero actionable findings** — and that result is itself the story. Giskard-AI is a testing-and-evaluation company, and their own repo shows it: they run `detect-secrets`, they run `zizmor` (a GitHub Actions security linter), they annotate intentional patterns, and their `pull_request_target` workflow is the textbook-correct implementation of a pattern that — on [the airweave scan two posts ago](airweave-ai-airweave.html) — was the one finding serious enough to disclose privately. This write-up is a teardown of *what a clean scan looks like* and why the same Semgrep rule fired a false positive here that was a real finding there.

## Why all 27 findings are false positives

### 23× `generic-api-key` (Gitleaks)

| Where | Verdict |
|---|---|
| `.secrets.baseline` (15 hits) | **Meta-file FP.** `.secrets.baseline` is the output of [`detect-secrets`](https://github.com/Yelp/detect-secrets) — a baseline file that *records* the secrets the maintainers have already triaged and allowlisted. Gitleaks scans the content of that file and re-flags every entry. This is the same meta-pattern class we saw with [PraisonAI's secret-detector regex](mervinpraison-praisonai.html) and [agentic_security's PII-detector test fixtures](msoedov-agentic-security.html): a security scanner panicking at another security tool's pattern definitions. |
| `Makefile:31` and `telemetry.py:134` (`phc_Asp36pe4X5WMqeJ4aMMV4gq5LGdGw69mdYSdEYGpbxm2`) | **Public-by-design FP.** A PostHog `phc_` project key — public, write-only, event-ingestion-only, designed to be shipped to clients. Same FP class as [openllmetry](traceloop-openllmetry.html) and [PraisonAI](mervinpraison-praisonai.html). Note also that `telemetry.py:134` carries an explicit `# pragma: allowlist secret` comment — the maintainers already triaged this in their `detect-secrets` workflow. |
| Other scattered hits | Test fixtures and the baseline file's cross-references. |

### 3× `pull-request-target-code-checkout` (Semgrep) — **the headline false positive**

This is the finding worth dwelling on, because the *exact same Semgrep rule* fired a **real, privately-disclosed finding** on [the airweave scan](airweave-ai-airweave.html) and a **false positive** here. The difference is everything.

`.github/workflows/integration-tests.yml` uses `pull_request_target` and checks out the PR head SHA — the raw ingredients of the "pwn requests" pattern. But Giskard has built the full mitigation around it:

```yaml
on:
  pull_request_target: # zizmor: ignore[dangerous-triggers] guarded by authorize job, label gate for external PRs, and immutable head.sha checkout
    types: [opened, synchronize, reopened, labeled]

permissions: {}          # ← empty default permissions

jobs:
  authorize:
    # checks org membership / contributor association /
    # a maintainer-applied "safe for build" label
    ...

  test-agents-functional:
    needs: authorize       # ← will not run unless authorize passes
    permissions:
      contents: read       # ← minimal scoped permissions
    steps:
      - uses: actions/checkout@... # v6
        with:
          ref: ${{ github.event.pull_request.head.sha || github.ref }}
          persist-credentials: false   # ← credentials not available to PR code
```

Six layered defenses, every one of them deliberate:

1. **`permissions: {}` at the top level** — the workflow has zero permissions by default.
2. **An `authorize` job** — external contributors' PRs do not run until a maintainer adds a `safe for build` label; internal contributors (MEMBER/COLLABORATOR/OWNER) and verified org members are auto-authorized.
3. **`needs: authorize`** on the job that actually runs PR code — so the gate is load-bearing, not decorative.
4. **`permissions: contents: read`** scoped on that job — even past the gate, the token can only read.
5. **`persist-credentials: false`** on the checkout — the PR code can't reuse the git credential.
6. **A `# zizmor: ignore[dangerous-triggers]` annotation** that documents *why* the pattern is safe — they run `zizmor` (a GitHub Actions security scanner), it flagged this, and they made a reviewed, documented decision.

That last point is the tell. Giskard didn't accidentally end up secure — they ran a scanner, it flagged the pattern, and they built the mitigation and annotated it. The airweave workflow had `pull_request_target` + PR-head checkout + `npm ci` with **none** of these guards.

**The lesson for static analysis:** `pull-request-target-code-checkout` is a structurally un-decidable rule for a single-file scanner. Whether it's a finding depends on the presence of an `authorize` job, a `needs:` edge, and the `permissions` scoping — context the rule can't evaluate. AI PatchLab reports it at `confidence: medium` (Semgrep findings always do, per [the confidence rules](https://github.com/elfrost/ai-patchlab/blob/main/scanner/confidence.py)), which is exactly the right signal: *look at this, don't panic about it*. The curation step is where "real on airweave / FP on Giskard" gets decided — and that's the step a raw scanner dump skips.

### 1× `non-literal-import` (Semgrep)

`libs/giskard-llm/src/giskard/llm/routing.py:74` — dynamic import in an LLM-provider routing module. By-design plugin/provider dispatch, same FP class as every prior scan in the series.

## Patterns observed

**A clean scan is a real result, and publishing it honestly matters.** It would be easy — and dishonest — to stretch one of these 27 findings into a "finding" to keep the post structurally similar to the others. There's nothing here. Giskard-oss is, by the evidence of this scan, an unusually well-secured codebase, and saying so plainly is worth more to AI PatchLab's credibility than a manufactured nitpick. A reputation built on "every scan finds something" is a reputation that rewards crying wolf.

**The `pull_request_target` contrast is the most useful thing in this series so far.** Two scans, same Semgrep rule, opposite verdicts:

- **airweave** — `pull_request_target` + PR-head checkout + `npm ci`, no `authorize` gate, no `permissions` scoping. Real finding, privately disclosed.
- **Giskard** — `pull_request_target` + PR-head checkout, behind an `authorize` job, `needs:` edge, `permissions: {}`, `persist-credentials: false`, and a documented `zizmor` annotation. False positive.

If you only read scanner output, those two look identical — both are `pull-request-target-code-checkout` at `high` severity. The entire value of a security review is the half-step of context that tells them apart. This pair is now the canonical teaching example for it.

**Giskard runs its own scanners, and it shows.** `detect-secrets` (the `.secrets.baseline` file and `# pragma: allowlist secret` annotations), `zizmor` (the `# zizmor: ignore` annotations on the workflow). The 23 Gitleaks "secrets" are almost entirely a side effect of Giskard *having a secret-management process at all* — the baseline file exists because they triage secrets, and our scanner re-flags the triage record. That's not a Giskard problem; it's a known interaction between two secret scanners, and worth an `.aipatchlabignore` default pattern (`**/.secrets.baseline`) in our own backlog.

## Notes on the tool

New backlog item from this scan:

- **Ship a default ignore pattern for `**/.secrets.baseline`.** A `detect-secrets` baseline file is, by construction, a list of secret-shaped strings; Gitleaks will always re-flag it. This is a safe global default suppression (unlike project-specific paths), and it would have removed 15 of this scan's 27 findings automatically.
- **`pull-request-target-code-checkout` deserves a confidence carve-out.** When the workflow contains an `authorize`-style job that the code-checkout job `needs:`, the finding should drop to `low` confidence. This is harder than path-based suppression (it requires parsing the workflow's job graph), but the airweave-vs-Giskard pair shows the payoff.

Recurring item, still open:

- **Cross-rule and meta-file awareness** — the scanner has now re-flagged a security tool's own pattern files three times (PraisonAI, agentic_security, Giskard). A "this file is itself a security-tooling artifact" heuristic is increasingly justified.

## Disclosure timeline

- **2026-05-20** — Scan run at commit `09eed260107d`, all findings curated to false-positive or already-mitigated.
- **2026-05-20** — No issue filed. There is nothing to action. This clean-scan write-up is published as the only artifact.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/Giskard-AI/giskard-oss" \
  --reports-dir reports/giskard-ai-giskard-oss \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
