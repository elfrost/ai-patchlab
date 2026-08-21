---
layout: default
title: "aurelio-labs/semantic-router: security scan"
description: "Security scan of aurelio-labs/semantic-router: 116 findings, cleanest two-person-team scan in the series. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-05-27
---

# aurelio-labs/semantic-router — security scan

**Repository:** [aurelio-labs/semantic-router](https://github.com/aurelio-labs/semantic-router) — 3.6k★, MIT, a semantic-routing library that uses embedding-based decisions to route LLM calls / function calls / agentic intents.
**Commit scanned:** `df9722ad75f6` (HEAD of `main` at scan time)
**Scan date:** 2026-05-27
**Disclosure status:** Public courtesy issue filed on the semantic-router repo. Scope kept tight (one issue, two concrete clusters with single-PR fixes each) per the methodology refinement after the [dstack rejection](dstackai-dstack.html#maintainer-response-and-lessons).

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 61 |
| Medium | 55 |
| Low | 0 |
| Info | 0 (filtered) |

**116 total findings. After curation: two concrete clusters worth a single coordinated cleanup each, and a short tail of false positives.**

semantic-router is the cleanest "mid-popularity, two-person maintainer team" scan in the series so far — no `eval`/`exec`/pickle/`exec.Command` in the source, no workflow shell-injections, no Dockerfile-as-root, no `tarfile.extractall` traps. The entire actionable surface lives in two distinct categories: a 50-site SQL identifier-interpolation cluster concentrated in one file, and a 30+ advisory dependency-drift tail across two `uv.lock` files.

## Top findings (curated)

### 1. 50× SQL identifier-interpolation in `semantic_router/index/postgres.py`

**Tool:** Semgrep (`sqlalchemy-execute-raw-query` ×28 + `formatted-sql-query` ×22 — same code lines, different rule families)
**Verdict:** **Same class as on six prior scans — but with the unusual property of being concentrated in a single file.**

`semantic_router/index/postgres.py` is the Postgres-backed implementation of semantic-router's vector-index interface. The whole file uses the `text(f"... {identifier} ...")` pattern for DDL and query construction with config-controlled identifiers (index name, embedding dimension, distance operator). At 50 cross-rule findings on the same call sites, this is the largest single-file cluster of this class in the series.

The defensible fix is the same SQLAlchemy `quoted_name()` / `Identifier()` pattern documented on [Upsonic](upsonic-upsonic.html), [PraisonAI](mervinpraison-praisonai.html), [airweave](airweave-ai-airweave.html), [honcho](plastic-labs-honcho.html), [dstack](dstackai-dstack.html), and [pixeltable](pixeltable-pixeltable.html). With every call site living in one file, the most pragmatic refactor is a small helper at the top of `postgres.py` (e.g. `_index_ident(self)` and `_distance_op(self)`) that other call sites use — turning 50 mechanical fixes into ~5 helper-call rewrites.

The realistic exploit window today is the same as on every prior occurrence: the identifier comes from Pydantic-validated config, so SQL injection is gated until/unless a future change lets it come from an untrusted source. The change isn't urgent; it's a class-cleanup.

### 2. ~30 dependency advisories across `uv.lock` and `.dagger/uv.lock`

**Tool:** Trivy (high/medium confidence — named advisories)
**Verdict:** **Real — concentrated in the production lockfile, single coordinated `uv lock --upgrade` pass clears most of them.**

The advisory tail by package:

| Package | Hits | Class |
|---|---:|---|
| `aiohttp` | 8 | Multiple advisories — historically aiohttp has had request-smuggling, request-parsing, and DoS classes |
| `urllib3` | 6 | Standard HTTP-client advisory pile |
| `onnx` | 3 | ML-runtime advisories |
| `Pillow` | 3 | Image-parsing CVE classes |
| `pyasn1` | 2 | ASN.1 parsing |
| `transformers` | 2 | Mostly deserialization/parsing in ML preprocessing |
| `requests`, `python-dotenv`, `idna` | 2 each | Standard transitive tail |

The `.dagger/uv.lock` is the [Dagger CI](https://dagger.io) pipeline's separate lockfile — same `idna` / `urllib3` / `requests` shape but a smaller surface (CI tooling, not the runtime). Both lockfiles benefit from a coordinated refresh; the main `uv.lock` is the priority.

For `aiohttp` specifically, the 8 advisories are dominated by a handful of CVE classes that all clear with a single bump past the current pin. Same for `urllib3` (6 advisories, single bump).

### 3-N. Out of scope / by-design

| Finding | Verdict |
|---|---|
| 2× `non-literal-import` in `semantic_router/{index/pinecone,routers/base}.py` | **By design** — plugin/index discovery |

That's it. semantic-router's scan has exactly the same shape as the cleanest scans in the series ([Giskard](giskard-ai-giskard-oss.html), [semble](minishlab-semble.html), [logfire](pydantic-logfire.html)) for everything *except* the two concrete clusters above — no `eval`/`exec`/pickle, no workflow injection, no Dockerfile findings, no agent shell-tool patterns, no secrets in source.

## Patterns observed

**A two-person maintainer team with a tight scope produces tight scans.** semantic-router is a focused library: vector-index implementations + a routing layer + integration adapters. The scan reflects that focus — the only large clusters are in two specific subsystems (the Postgres backend, and the dependency tree). There's no sprawl, no monorepo drift, no "is this code or example or fixture?" ambiguity. This is the cleanness shape we'd hope to find more often.

**The Postgres-file SQL cluster is the cleanest argument yet for a per-subsystem helper refactor over per-site fixes.** Prior occurrences ([Upsonic](upsonic-upsonic.html), [PraisonAI](mervinpraison-praisonai.html), [honcho](plastic-labs-honcho.html), [pixeltable](pixeltable-pixeltable.html)) had the f-string SQL pattern spread across multiple files, where per-site fixes made sense. Here it's 50 sites in *one file* — a `_index_ident(self)` helper at the top of `postgres.py` plus identifier-validation in the index-name setter generalizes the fix in a single PR rather than 50. Worth flagging this pragmatic shape to the maintainers explicitly.

**The dep-CVE tail is the kind of "schedule a `uv lock --upgrade` pass" item that monthly automation handles**. Dependabot or Renovate scoped over both `uv.lock` files would catch this cadence; the same recommendation we made on [Klavis](klavis-ai-klavis.html), [honcho](plastic-labs-honcho.html), and [dstack](dstackai-dstack.html) applies, just at smaller scale.

## Notes on the tool

- **The dual-rule overlap** (`sqlalchemy-execute-raw-query` ×28 + `formatted-sql-query` ×22 on the same lines) is the same Semgrep behavior noted on [PraisonAI](mervinpraison-praisonai.html) — two related rules firing on the same AST. Cross-rule dedup is still the top backlog item.
- The clean profile here (no eval/exec/pickle/workflow/Dockerfile findings outside the two clusters) makes the scan a useful "what right looks like" reference for the surrounding noise on bigger projects.

## Disclosure timeline

- **2026-05-27** — Scan run at commit `df9722ad75f6`; findings curated. No path-ignore needed (the scan's signal is concentrated cleanly).
- **2026-05-27** — Public courtesy issue filed on aurelio-labs/semantic-router with the two cluster summaries (SQL-helper refactor + `uv lock --upgrade` pass).
- **2026-08-08** — A third-party contributor ([@numair212](https://github.com/numair212)) volunteered on the issue to take the dependency half, and opened [PR #678](https://github.com/aurelio-labs/semantic-router/pull/678) the same day.
- **2026-08-10** — **PR #678 merged** — the `uv lock --upgrade` cluster is resolved. Both lockfiles refreshed (`uv.lock` and `.dagger/uv.lock`), plus four typing fixes the numpy 2.x bump surfaced, verified through the project's own Dagger lint and unit pipeline. The contributor documented in the PR which advisories they *could not* clear — several are blocked by `fastembed`'s pins — which is the right way to close a dependency-drift item: state the residual rather than claim zero.
- **2026-08-11** — **The SQL-identifier half has not landed.** [PR #674](https://github.com/aurelio-labs/semantic-router/pull/674) (`fix(postgres): centralize SQL identifier handling`, a different contributor) was closed unmerged on 2026-07-25 with no comment, and `semantic_router/index/postgres.py` still has no identifier-quoting helper. Issue #666 remains open. **Neither half was ever exploitable** — the SQL cluster is the [identifier-interpolation false positive](mnemosyne-oss-mnemosyne.html) with values bound and identifiers internal, which is exactly why it was filed as a hardening cleanup and not a vulnerability, and why it is unsurprising that it is the half nobody prioritised.
- **2026-08-11** — Recorded as a **partial resolution**. Worth noting for the series: this is the first disclosure resolved by a *third-party contributor* rather than by a maintainer or by me — the issue sat open for ten weeks, then someone unconnected picked it up because it was a public, specific, actionable description of work. A filing that is concrete enough to be adopted by a passer-by outlives my attention span for it.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/aurelio-labs/semantic-router" \
  --reports-dir reports/aurelio-labs-semantic-router \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
