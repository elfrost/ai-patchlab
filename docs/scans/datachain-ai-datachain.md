---
layout: default
title: "datachain-ai/datachain: security scan"
description: "Security scan of datachain-ai/datachain: 35 findings, 0 real — 16th clean scan: a Python 'context layer' for unstructured data (DVC/Iterative team"
date: 2026-07-14
---

# datachain-ai/datachain - security scan

**Repository:** [datachain-ai/datachain](https://github.com/datachain-ai/datachain)
**Commit scanned:** `431252d7261429dd535203794cc8612acfd74af3`
**Scan date:** 2026-07-14
**Disclosure status:** public — post-only (strict-norm: commercial "Studio" tier; nothing cleared the quality gate)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 3 |
| Medium | 32 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 35 (0 real after curation)

DataChain (from the DVC / Iterative team) is a Python "context layer" for
unstructured data — typed, versioned datasets over S3/GCS/Azure, with UDFs
applied at scale and a hosted "Studio" tier. For a library that caches datasets
and ships user functions to distributed workers, the security question is
**deserialization**: does anything `pickle.load` data an attacker could shape?
The completeness sweep says no. This is the **16th clean scan**; the finding
count is workflow lint.

## Top findings

### 1. The deserialization surface is serialize-own-code, not load-untrusted-data

- **Tool:** manual completeness sweep (semgrep did not flag pickle here)
- **Confidence:** high — not reachable
- **Why it matters:** DataChain uses `pickle` (16 sites) and `cloudpickle` (10)
  — exactly the shape that turns "cached dataset" or "distributed UDF" into
  RCE if a `load` ever touches attacker-controlled bytes.
- **Why it's not a finding:** There is **no `pickle.load` / `pickle.loads` /
  `cloudpickle.loads` in the source** (outside tests). The serialization is
  `dumps` — the engine pickling the **user's own UDF** to hand to its own
  workers for distributed execution. The producer and consumer are the same
  pipeline running the same person's code; nothing deserializes a dataset or a
  third party's payload. The scary primitive is present, but only on the
  write side.

### 2. The one `exec` is schema-inference codegen over your own data

- **File:** `src/datachain/lib/meta_formats.py:161`
- **Tool:** semgrep (`exec-detected`)
- **Confidence:** documented feature; a trust-boundary note, not a vuln
- **Why it matters:** `exec(model_code, gl)` runs a Pydantic model that
  `gen_datamodel_code(file, …)` generated from a data file's schema — DataChain's
  "infer a DataModel from a sample" feature (built on datamodel-code-generator).
  Executing generated code is worth understanding.
- **Why it stays a note:** The input is a data file in *your own* pipeline, and
  the codegen path is a vetted library, not string-concatenated Python. The
  residual trust assumption — "schema inference `exec`s generated code, so run it
  on data samples you trust" — is worth a docstring, but it isn't an
  attacker-reachable path in the local pipeline model, and there's no evidence a
  crafted schema yields injectable code through the generator. Static
  `spec=`-provided schemas skip the `exec` entirely.

### 3. The count is workflow tags, a backend loader, and examples

- **Tool:** semgrep + gitleaks
- **Confidence:** high — FP / hardening
- **Why it matters / why it doesn't:** 26 of the 35 findings are
  `github-actions-mutable-action-tag` (SHA-pinning hardening). Three
  `non-literal-import`s are `catalog/loader.py` selecting the configured
  warehouse/DB backend by name — the standard plugin-loader pattern. The rest
  are `examples/` (a torch `pin_memory` hint), a docs SRI warning, and a
  `dependabot-missing-cooldown` nit. Dependencies are clean (trivy found no
  CVEs; Dependabot is wired). The two gitleaks hits are a `docs/studio/webhooks.md`
  example and `tests/func/fake-service-account-credentials.json` — a fixture
  whose filename says "fake."

## Patterns observed

**"Present" is not "reachable" for `pickle`.** A grep for pickle on a
data-caching, distributed-execution library lights up 26 sites, and the instinct
is "deserialization RCE." But the direction matters: every one is a `dumps` on
the write side, serializing the user's own UDF for the user's own workers. The
completeness-sweep move — search specifically for `.load`/`.loads` on an
attacker-reachable source — turned the scariest-looking surface into a
non-finding in one query. Same discipline as the OpenKB "CLI has no server" and
inspect_ai "pickle is a local cache" reads.

**The residual is a documentation trust-boundary, not a bug.** The `exec` in
schema inference is the only thing on this codebase that runs generated code,
and it's a documented convenience (infer a model from a sample) over data the
pipeline author chose. Noting the assumption ("infer from trusted samples") is
useful; filing it as a vulnerability would be crying wolf, especially since a
static `spec` avoids it and the codegen goes through a real library.

**Strict-norm and clean.** DataChain has a commercial Studio tier, so this is
post-only by policy anyway — but there was nothing to file: no untrusted
deserialization, clean deps, and a finding list that's workflow hardening and a
by-design backend loader.

## Notes on the tool

- **`pickle` findings need a load-vs-dump direction.** The scanner's
  `avoid-pickle` class (and a plain grep) can't distinguish "serialize my own
  object" from "deserialize someone else's bytes," yet only the second is an RCE.
  A rule that flags `pickle.load`/`loads` (and `cloudpickle.loads`) on an
  externally-sourced buffer — and stays quiet on `dumps` — would target the
  actual risk. Highest-value backlog item from this scan.
- **`exec-detected` should surface the code's provenance.** Here the exec'd
  string came from a codegen library over a data-file schema. "Is the exec'd
  string a literal, a generated artifact, or attacker-influenced input?" is the
  distinction that decides severity — the same trust-source gap noted on the
  Agently `PythonSandbox` finding, inverted (there it was reachable, here it
  isn't).
- **`github-actions-mutable-action-tag` (26) dominates a third scan running.**
  mcp-atlassian (18), potpie (20), now datachain (26). A repo-level
  "actions SHA-pinned?" rollup is overdue.

## Disclosure timeline

- 2026-07-14 — scan run
- 2026-07-14 — public post (this page); post-only, no upstream issue filed

This is a post-only clean-scan write-up. The `pickle`/`cloudpickle` surface is
serialize-own-UDF (no untrusted `load`), the one `exec` is documented
schema-inference codegen over the pipeline author's own data, dependencies are
clean, and the finding count is workflow lint and a by-design backend loader.
Nothing cleared the quality gate.

## Reproduce

```bash
git clone https://github.com/datachain-ai/datachain /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/datachain-ai-datachain \
  --min-severity medium --ignore-samples
```
