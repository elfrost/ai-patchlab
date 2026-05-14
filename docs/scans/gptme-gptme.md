---
layout: default
title: "gptme/gptme: security scan"
date: 2026-05-14
---

# gptme/gptme — security scan

**Repository:** [gptme/gptme](https://github.com/gptme/gptme) — 4.3k★, a terminal-based AI agent that writes code and runs commands locally.
**Commit scanned:** approx `0bf47a6` (HEAD of `master` at scan time)
**Scan date:** 2026-05-14
**Disclosure status:** Best-practice items filed as a public courtesy issue on the gptme repo. No findings required private coordination.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 29 |
| Medium | 28 |
| Low | 0 |
| Info | 0 (filtered) |

**57 total findings. After curation: 0 critical confirmed, ~3 best-practice improvements worth flagging, ~50 false positives or by-design patterns.**

The headline: **gptme is well-defended**, and the one systemic pattern worth addressing is in CI/CD configuration, not application code.

## Top findings (curated)

### 1. GitHub Actions — 8× shell-injection patterns via `${{ inputs.* }}` interpolation

**Files:** `.github/workflows/{build,optimize-prompts,release,tauri}.yml`
**Severity:** high (per Semgrep)
**Verdict:** Real best-practice issue, narrow realistic exploit window.

`${{ inputs.* }}` values are inserted into `run:` shell scripts at workflow-parse time, before any shell quoting can protect them. Exploitation would require a dispatcher with write access intentionally passing a malicious input — narrow but not zero. The standard fix is to pass the value through `env:` and reference it as `$ENV_VAR` from the shell. GitHub Actions documents this in their [security hardening guide](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-an-intermediate-environment-variable).

### 2. `optimize-prompts.yml:149` — github-script JS injection

**Severity:** high
**Verdict:** Real, same class as #1.

`${{ inputs.model }}` is interpolated directly into a JavaScript template literal inside an `actions/github-script` step. The fix is the same: pass via `env:` and read `process.env.MODEL` inside the script.

### 3. `gptme/prompts/context_cmd.py:55` — `subprocess.run(cmd, shell=True)`

**Severity:** high
**Verdict:** By design. User-controlled command is the feature.

The function `get_project_context_cmd_output(cmd, workspace)` takes a project-context command the user explicitly configures, then runs it in their workspace. `shell=True` is correct here — the trust model is "the user is the only attacker, and they are also the victim." Suggested improvement: a one-line code comment so contributors don't accidentally start passing untrusted strings into this function later.

### 4. `swe_bench_extra_data.py:271-282` — `pd.read_pickle` on a local cache

**Severity:** high
**Verdict:** Low impact. Internal eval infrastructure.

The pickle file (`top_50_cache.pkl`) is written and read by the same script in the same directory. Not exposed to any network input. Idiomatic Parquet or Feather would be a cleaner choice but the realistic attack surface is essentially zero.

### 5. `tests/test_onboard.py:46` — `"sk-test1234567890abcdef"`

**Severity:** high (gitleaks)
**Verdict:** False positive. Obvious test placeholder.

Gitleaks' `generic-api-key` rule matches the `sk-` prefix; the actual value is a transparent placeholder used to assert API-key detection logic. In a real audit this should be excluded via a `.gitleaksignore` rule scoped to test fixtures.

## Patterns observed

**The single real systemic signal: CI/CD inputs.** Of 57 findings, the meaningful security pattern is one class: 9 GitHub Actions workflows interpolating user-controllable inputs into shell or JS contexts without using the `env:` indirection. That's a CI/CD-configuration concern, not application code. It's also one of the most common patterns I expect to see in mid-size Python projects with growing release automation — most teams discover this only after the first time someone abuses it.

**The application code is defensive.** The findings inside the actual gptme runtime are limited to one intentional `shell=True` (the user's own context command) and a handful of `non-literal-import` calls in plugin/discovery paths where dynamic imports are the design. There's no SQL-injection-shaped pattern, no eval/exec on LLM output, no unsafe deserialization of user data, no hardcoded credentials in the runtime.

**The eval framework is where pickle lives.** Both pickle findings are inside `gptme/eval/swe_extra/` — the SWE-bench evaluation tooling, which is internal-only and cache-only. Worth keeping isolated, but not a runtime risk.

**The false positives illustrate why the second-pass matters.** Semgrep's `non-literal-import` fired 12 times on perfectly normal plugin discovery code. The `insecure-websocket` rule fired 10 times — all in test files (`useVoiceSession.test.tsx`). The `missing-integrity` rule fired 7 times on CDN-loaded scripts in static HTML. Every one of those would have been false-positive in any sane review.

**What AI PatchLab's confidence rules got right:** every Semgrep finding came out at `confidence: medium`, not `high`. That's deliberate — rule-based static analysis carries an unavoidable FP rate, and the confidence value signals "this is worth looking at, not panicking about." The only `confidence: high` findings in the whole scan were the gitleaks `generic-api-key` matches, and even those turned out to be FPs (test placeholders) — exactly the case where named-rule scanners should still be reviewed against context.

## Notes on the tool

Things AI PatchLab handled awkwardly or missed during this scan, each of which now lives in the project backlog:

- **No deduplication across files.** 8 separate `run-shell-injection` findings for the same rule pattern would read much better collapsed into one "8 occurrences across `.github/workflows/`" entry.
- **No persistent "verified FP" annotation.** Re-scanning gptme tomorrow would surface the same 50 FPs again with no way to mark them as already-reviewed.
- **The `Repository:` header in `security_report.md` still shows the temp clone path** even though finding-level `file` fields are rebased correctly. (Already in the backlog.)
- **No SARIF export** for users who want to feed findings into GitHub code-scanning or other tooling.

## Disclosure timeline

- **2026-05-14** — Scan run, top findings curated.
- **2026-05-14** — Public courtesy issue filed on [gptme/gptme](https://github.com/gptme/gptme/issues) with the three best-practice items (CI/CD `env:` fix + `shell=True` comment). This post and that issue are public from day 1; no critical finding required private coordination.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/gptme/gptme" \
  --reports-dir reports/gptme-gptme \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
