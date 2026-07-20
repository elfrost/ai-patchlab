---
layout: default
title: "vitali87/code-graph-rag: security scan"
date: 2026-07-19
---

# vitali87/code-graph-rag - security scan

**Repository:** [vitali87/code-graph-rag](https://github.com/vitali87/code-graph-rag)
**Commit scanned:** `6f3da01fb2495b5b6f1c33c2449defb43dcca6a3`
**Scan date:** 2026-07-19
**Disclosure status:** ✅ resolved — fix merged upstream ([PR #809](https://github.com/vitali87/code-graph-rag/pull/809), 2026-07-19)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 5 |
| Medium | 17 |
| Low | 0 |
| Info | 0 |

**Total findings:** 22 (1 real, reachable, exploitability-shaped after curation)

## What it is

Code-Graph-RAG is a graph-based RAG system that parses multi-language codebases
with Tree-sitter, builds a Memgraph knowledge graph, and answers natural-language
queries about code — including **editing** capabilities. It ships as an **MCP
server** (`codebase_rag/mcp/server.py`) so an agent can drive it. That MCP surface
is where the one real finding lives.

## Top findings

### 1. Reachable MCP SDK CVEs — the exposed StreamableHTTP transport binds `0.0.0.0` with no auth

- **Dependency:** `mcp==1.25.0` (`uv.lock`; `pyproject.toml` pins `mcp>=1.25.0`)
- **Tool:** trivy
- **Confidence:** high
- **CVEs:** CVE-2026-52869, CVE-2026-52870 (fixed in `mcp` 1.27.2); CVE-2026-59950 (fixed in 1.28.1)
- **Why it matters:** The project doesn't just *depend* on the MCP SDK — it exposes
  the affected transport. `codebase_rag/mcp/server.py:serve_http()` mounts
  `StreamableHTTPSessionManager.handle_request` behind a bare Starlette route with
  **no authentication middleware**, and the default bind is
  `MCP_HTTP_HOST = "0.0.0.0"`, port `8080`, path `/mcp` (`codebase_rag/config.py`).
  CVE-2026-52869 is precisely *"HTTP transports serve session requests without
  verifying the authenticated principal"* — so on the default HTTP deployment a
  network-adjacent client can reach the session manager directly. `stateless=False`
  means sessions are server-tracked, which is the exact object CVE-2026-52869 and
  the experimental-task-handler CVE-2026-52870 concern.
- **Recommendation:** Bump `mcp>=1.28.1` (`uv add 'mcp>=1.28.1'` / `uv lock
  --upgrade-package mcp`) — one constraint clears all three. Independently, treat
  `0.0.0.0` as an explicit operator choice: default the HTTP bind to `127.0.0.1`
  and document that the `/mcp` endpoint needs a reverse-proxy auth layer before it
  faces a network.

### Reachability breakdown (version-match ≠ reachable)

| CVE | Transport affected | Used here? | Verdict |
| --- | --- | --- | --- |
| CVE-2026-52869 | Streamable **HTTP** (unauth'd principal) | **Yes** — `serve_http` exposed via `cli.py`, `0.0.0.0:8080`, no auth | **Reachable** |
| CVE-2026-52870 | Experimental **task handlers** | Conditional (SDK feature) | Cleared by same bump |
| CVE-2026-59950 | **WebSocket** transport (Host/Origin) | **No** — no WS transport in the code | Version-match only |

The honest version: only one of the three is a live, reachable exposure on the
default deployment; a second is conditional; the WebSocket CVE is inert because the
server never speaks WebSocket. One dependency bump resolves all three regardless.

### The other four "highs" are false positives

- **`.github/workflows/sonarcloud.yml:43`** — flagged as a hardcoded SonarQube API
  key. It's `SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}` — a secrets *reference*, not a
  literal. FP.
- **`.github/workflows/version-bump.yml:58`** — flagged `run-shell-injection` for
  `echo "type=${{ github.event.inputs.bump_type }}"`. The input is a
  `type: choice` constrained to `patch`/`minor`/`major` — not free text — under a
  `push`/`workflow_dispatch` (privileged) trigger. Nothing attacker-controlled
  reaches the shell. FP.

## Patterns observed

The interesting move on this repo is that the RAG engine is a code-editor: it runs
model-driven Tree-sitter parsing and writes files, so the reflex is to hunt for an
`exec`/injection sink. The scanner dutifully lit up six `non-literal-import` hits in
`parser_loader.py` and the parser modules — but every one is dynamic Tree-sitter
*grammar* loading where the language name is typed `cs.SupportedLanguage` (a
constrained enum), not a path an attacker names. That's the product loading its own
grammars, not an import-injection. Same story for the two `dynamic-urllib` hits: one
fetches a **host-pinned** `https://pypi.org/pypi/{pkg}/json` summary for the
project's own dependencies (README generation — host is fixed, only the package path
segment varies), the other is a local dev-stack health probe with a timeout, already
carrying a `# noqa: S310`. Neither is SSRF.

So the real signal wasn't in the Python logic at all — it was in the **dependency +
deployment posture of the MCP transport**. The SDK is pinned to a version with three
published CVEs, *and* the project happens to expose the one transport (StreamableHTTP)
that the most serious of them targets, on `0.0.0.0` with no auth. This is the
distinction I keep coming back to across these scans: a version-match on `mcp` means
little until you check which transport the project actually stands up. Here it stands
up the vulnerable one by default — that's what promotes it from noise to a finding.

Two genuine-but-minor hardening notes round it out: `split-score.yml` pins
`actions/checkout@v4` and `vitali87/pr-split@v1.0.0` by **mutable tag** while every
other workflow in the repo SHA-pins (`actions/checkout@de0fac2…`) — worth making
consistent. Everything else — the six `evals/oracles/*.js` `path-join` hits, the
`optimize/code_to_text.sh` IFS note — is eval-harness and dev-tooling code, outside
the shipped package.

## Notes on the tool

- **SCA needs a "reachable transport?" column, not just "version-match".** All three
  `mcp` CVEs surfaced identically as HIGH. Only one is a live exposure on the default
  deployment; distinguishing them required reading `serve_http` and the default host
  binding by hand. A future enrichment could correlate a flagged transport-layer CVE
  with grep evidence that the affected transport is instantiated
  (`StreamableHTTPSessionManager` present → HTTP CVEs reachable; no WebSocket import →
  WS CVE inert). Backlog.
- **`run-shell-injection` should read the input *type*, not just `${{ inputs.* }}`.**
  A `type: choice` input constrained to a literal option set can't inject; treating it
  the same as a free-text input is a recurring workflow FP (fourth in the series).
- **`non-literal-import` over a typed/enum-constrained language name is by-design.**
  A grammar-loader keyed on an enum is not import-injection; the rule can't see the
  type constraint.

## Disclosure timeline

- 2026-07-19 — scan run
- 2026-07-19 — focused issue filed upstream ([#808](https://github.com/vitali87/code-graph-rag/issues/808)) — mcp CVE reachability + fix
- 2026-07-19 — public post (this page)
- 2026-07-19 — ✅ **resolved (~same day):** maintainer verified all three claims ("accurate on every point, including the honest triage that only CVE-2026-52869 is live here") and merged [PR #809](https://github.com/vitali87/code-graph-rag/pull/809) implementing the full suggested fix — `mcp>=1.28.1` with the lock regenerated **and** `MCP_HTTP_HOST` defaulting to `127.0.0.1` so an external bind becomes an explicit operator choice

## Reproduce

```bash
git clone https://github.com/vitali87/code-graph-rag /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/vitali87-code-graph-rag --min-severity medium
```

---

*AI PatchLab is a local-first security scanner. This report was generated locally —
no source code was sent to any third party and no AI provider was contacted. Findings
are a signal, not a verdict; the reachability and exploitability judgments above are
mine after reading the call sites.*
