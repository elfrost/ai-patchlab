---
layout: default
title: "UKGovernmentBEIS/inspect_ai: security scan"
description: "Security scan of UKGovernmentBEIS/inspect_ai: 161 findings, 0 real — 12th clean scan: the UK AI Security Institute's LLM-eval framework"
date: 2026-07-02
---

# UKGovernmentBEIS/inspect_ai - security scan

**Repository:** [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai)
**Commit scanned:** `a29a8f3e58ebb0599a6e514821fd72181a8a3594`
**Scan date:** 2026-07-02
**Disclosure status:** public — post-only (clean scan; no upstream issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 50 |
| Medium | 110 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 161 (0 real after curation)

Inspect is the LLM-evaluation framework built by the **UK AI Security
Institute** — it runs eval tasks that execute model-generated tool calls
(bash, python, editors) inside Docker/local sandboxes, records transcripts to a
log store, and ships a log viewer. That makes its most interesting surface the
sandbox boundary: an eval framework deliberately runs untrusted, model-authored
code, so the security question is whether that code stays contained.

This is the **12th clean scan**, and one of the most satisfying: the two
findings a scanner would headline — a `tarfile.extractall` sandbox-escape and
pickle deserialization — are, on inspection, defended with a CVE citation and a
trusted local cache respectively. The people whose literal job is AI safety
had already closed the interesting hole.

## Top findings

### 1. The tar-slip sandbox-escape is defended with `filter="data"` and a CVE citation

- **File:** `src/inspect_ai/util/_checkpoint/_sandbox_restic/egress.py:201`
- **Tool:** semgrep (`tarfile-extractall-traversal`)
- **Confidence:** high — by-design, correctly mitigated
- **Why it matters:** This extracts a tar built **inside the sandbox** during a
  restic checkpoint egress. Since the sandbox runs untrusted model code, a
  malicious agent could plant a tar with `../` entries or absolute paths so that
  host-side extraction writes outside the destination — a sandbox escape via
  checkpoint restore. This is exactly the finding worth chasing on an eval
  framework.
- **Why it's not a finding:** The maintainer got there first. The code carries an
  explicit comment — *"The tarball bytes originate inside the sandbox … so they
  are untrusted: a sandboxed agent can plant a malicious tar … `filter="data"`
  rejects absolute paths, `..` traversal, and outside-pointing links … (CVE-2007-4559
  class). See PEP 706"* — and calls `tar.extractall(dest_repo, filter="data")`.
  That's the correct PEP 706 mitigation, applied at the exact spot, with the CVE
  named in the source. Semgrep flags `extractall`; it can't see the `filter="data"`
  argument that neutralizes it.

### 2. Pickle is a local model-response cache, not an untrusted-load

- **File:** `src/inspect_ai/model/_cache.py:209,223,388,412`, `src/inspect_ai/_eval/task/store.py:23,43`
- **Tool:** semgrep (`avoid-pickle`)
- **Confidence:** high — by-design
- **Why it matters / why it doesn't:** `pickle.load` is dangerous when the data
  is attacker-controlled. Here it's the on-disk **model-response cache**:
  `cache_store` writes `pickle.dump((expiry, output), f)` into the user's own
  cache dir and `cache_fetch` reads it back (and even re-validates the result is
  a `ModelOutput`). The producer and consumer are the same local process; the
  trust boundary is the local filesystem. This is the same pattern `joblib` /
  `requests-cache` use — not an untrusted deserialization path.

### 3. The `eval()` "code execution" hits are the framework's own API

- **File:** `src/inspect_ai/_eval/evalset.py:378`, `src/inspect_ai/_cli/eval.py:1869`
- **Tool:** semgrep (`eval-detected`)
- **Confidence:** high — FP
- **Why it matters / why it doesn't:** `eval-detected` matches the token
  `eval(`. In a framework literally named for evaluations, `eval(tasks=…, model=…)`
  and `eval(**params)` are calls to Inspect's **public `eval()` function** (run
  an evaluation), not the Python builtin. The remaining four hits are all in
  `examples/`. No dynamic code evaluation is happening.

### 4. The one critical is a transitive `jupyter-server` CVE that isn't reached

- **File:** `uv.lock` (`jupyter-server` — stored-XSS → RCE)
- **Tool:** trivy
- **Confidence:** high — version-match, not reachable
- **Why it matters / why it doesn't:** The CVE requires running the **Jupyter
  Server web application**. Inspect imports `jupyter` in a handful of places
  (kernel/notebook tooling), but `jupyter_server` has **zero** direct imports —
  it's a transitive dependency, and Inspect never stands up the Jupyter web app
  whose XSS surface the CVE describes.

### 5. The 50→bulk is workflow tag-pinning and by-design sandbox Dockerfiles

- **Tool:** semgrep
- **Confidence:** hardening / by-design
- **Why it matters:** 62 of the findings are `github-actions-mutable-action-tag`
  — using `@v4`-style mutable tags instead of pinned commit SHAs. Reasonable
  supply-chain hardening, not a vulnerability. The `run-shell-injection` hits are
  in release/CI workflows (`docker.yml`, `npm-publish.yml`, `test.yml`), and the
  two `missing-user` (root) findings are **example sandbox Dockerfiles** — where
  root-inside-the-container is the point, because the container *is* the isolation
  boundary.

## Patterns observed

**An eval framework's threat model is the sandbox, and this one holds.** The
whole reason Inspect exists is to run model-authored code — bash tools, python
tools, editors — so "arbitrary code execution" inside the sandbox is the
feature, not the bug (the same inversion the AG2 scan showed). The security
question narrows to the boundary: does anything let that code reach the host?
The one place it could — extracting a sandbox-built tar on the host during
checkpoint egress — is defended with `filter="data"` and a CVE-2007-4559 comment.
That's the single most important control on the codebase, and it's correct.

**The scariest-looking findings were the most thoroughly handled.** This keeps
recurring (openmed's `trust_remote_code` allowlist, codex-lb's trusted-proxy
CIDRs) and Inspect is a clean example: `tarfile.extractall` and `pickle.load`
are exactly the rules a reviewer's eye jumps to, and both were already reasoned
through — one with an inline CVE reference, the other by keeping the data on the
local side of the trust boundary. A scanner reports the dangerous *primitive*;
it can't report the *argument* or the *data source* that makes it safe.

**Provenance shows.** Inspect is maintained by an AI security institute, and the
security posture is what you'd hope for from that: the sandbox-escape vector is
documented and mitigated, the log-store SQL is parameterized (the `IN`-clause
builds `?` placeholders and binds the values; only internal table-name constants
are interpolated), Dependabot is wired, and there are no secrets (gitleaks
clean). The 161 count is real scanner output, but after curation it's tag-pinning
hardening and a transitive CVE.

## Notes on the tool

- **`tarfile-extractall-traversal` should check for `filter=`.** Since Python
  3.12 / PEP 706, `extractall(..., filter="data")` is *the* mitigation. A rule
  that flags `extractall` without checking whether a `filter=` argument is
  present will false-positive on correctly-hardened code — as it did here, on a
  line that even cites the CVE. High-value backlog item; pairs with the
  mitigation-awareness gap seen on openmed and codex-lb.
- **`eval-detected` needs to resolve the callee.** `eval(` as a token match is
  a poor signal in any project that defines its own `eval` function; here it hit
  the framework's public API five times. Checking that the name resolves to the
  builtin (not a local/imported symbol) would remove the class.
- **Local-cache pickle is a different tier than untrusted-load pickle.** The
  `avoid-pickle` hits were all a same-process disk cache. Distinguishing
  "pickle of data this process just produced" from "pickle.load of externally
  supplied bytes" (by data-flow or even by directory heuristic) would right-size
  these.
- **`missing-user` on example sandbox Dockerfiles is by-design.** For a sandbox
  image, root-inside-the-container is intentional; the `examples/**` +
  sandbox-Dockerfile combination should be candidate-FP.

## Disclosure timeline

- 2026-07-02 — scan run
- 2026-07-02 — public post (this page); post-only, no upstream issue filed

This is a post-only clean-scan write-up. The sandbox-escape vector is mitigated
with `filter="data"` and a CVE citation, the pickle is a trusted local cache,
the `eval()` hits are the framework's own API, the log-store SQL is
parameterized, and the lone critical is a transitive, unreached `jupyter-server`
CVE. Nothing cleared the quality gate.

## Reproduce

```bash
git clone https://github.com/UKGovernmentBEIS/inspect_ai /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/ukgovernmentbeis-inspect-ai \
  --min-severity medium --ignore-samples
```
