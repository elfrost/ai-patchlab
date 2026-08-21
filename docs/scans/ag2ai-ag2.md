---
layout: default
title: "ag2ai/ag2: security scan"
description: "Security scan of ag2ai/ag2: 73 findings, 0 real/reachable/undefended — AG2 (formerly AutoGen), the canonical 'agents that write and run code' framework"
date: 2026-06-26
---

# ag2ai/ag2 - security scan

**Repository:** [ag2ai/ag2](https://github.com/ag2ai/ag2)
**Commit scanned:** `b6f271ed99a5ca65a586bbcde6bda6cbaafd3315`
**Scan date:** 2026-06-26
**Disclosure status:** public — post-only (no real, high-confidence item cleared the bar; no upstream issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 44 |
| Medium | 29 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 73 (0 real, reachable, undefended after curation)

AG2 (formerly AutoGen) is the open-source multi-agent framework — the canonical
"agents that write and run code" toolkit. Scanning it is interesting precisely
because the scary findings are supposed to be there: a framework whose job is to
execute LLM-generated Python, run Docker sandboxes, and `exec()` retrieved
tools will light up every code-execution rule a scanner owns. The curation
question isn't "does it run code" — it's "is anything running code it didn't
intend to," and "did the maintainers guard the one spot where an injection
actually crosses a trust boundary." On both counts AG2 comes out clean: the
deps are current (Dependabot is wired and trivy found a single devcontainer
nit), the one genuine eval-injection vector is already patched against AG2's own
advisory, and all 19 secret hits are false positives.

## Top findings

### 1. The `eval()` that matters is already patched against AG2's own advisory

- **File:** `autogen/agentchat/group/context_expression.py:228`
- **Tool:** semgrep (`eval-detected`)
- **Confidence:** high that it is **by-design and hardened**
- **Why it matters:** `ContextExpression` evaluates a boolean DSL
  (`${var_a} > 5 and ${var_b}`) by substituting context variables into a string
  and calling `eval()`. If a context value reached `eval()` unescaped, an
  attacker who controls a context variable would have arbitrary code execution.
- **Why it's not a finding:** AG2 already lived this. The code escapes string
  values (`replace("\\", "\\\\").replace("'", "\\'")`) before substitution,
  with an inline comment citing **GHSA-9fvw-gr53-m7fw** — the advisory they
  patched. The threat model is even documented: non-string `__str__` injection
  is explicitly called out as out-of-scope for the fix. This is a maintainer
  who found the eval-injection, fixed it, referenced the GHSA in the code, and
  annotated the residual. The scanner re-flags the `eval` token; it can't see
  the patch wrapped around it.

### 2. Every code-execution finding is the product, not a bug

- **Files:** `autogen/code_utils.py:448`, `autogen/coding/jupyter/docker_jupyter_server.py:118`, `autogen/beta/extensions/docker/sandbox.py:185` (docker-arbitrary-container-run); `autogen/agentchat/contrib/captainagent/tool_retriever.py:210,278` (exec-detected); `LocalCommandLineCodeExecutor` (28 sites)
- **Tool:** semgrep (`exec-detected`, `docker-arbitrary-container-run`, `dangerous-globals-use`)
- **Confidence:** high — by-design
- **Why it matters:** These are AG2's core feature surface: running
  LLM-authored code in a Docker sandbox, executing retrieved tool definitions,
  spinning up Jupyter kernels. The framework documents the sandbox/execution
  model; the `docker` executor exists specifically to contain this. There is no
  *unintended* execution path here — the `exec`/`docker-run` calls are the
  intended ones.
- **Recommendation:** None. Flagging a code-execution framework for executing
  code is a scope mismatch, not a finding.

### 3. All 19 secret hits are false positives

- **Tool:** gitleaks + semgrep (`detected-generic-secret`)
- **Confidence:** high — FP
- **Why it matters / why it doesn't:** The two that land in real code are not
  secrets: `autogen/oai/openai_utils.py:497` is an `api_key="sk-abcdef…"` inside
  a docstring `Example:` block, already annotated `# pragma: allowlist secret`;
  `autogen/beta/a2ui/transports/ag_ui.py:57` matches on the string constants
  `"a2ui-surface"` / `"a2ui_operations"`, which are a renderer wire-contract,
  not credentials. The remaining 15 are test fixtures and `website/docs/*.mdx`
  documentation examples. The maintainers have clearly already triaged these —
  the `pragma: allowlist secret` annotation is the tell.

### 4. The one genuine hardening observation: `ag2 serve` ships no auth and a `--ngrok` flag

- **File:** `cli/src/ag2_cli/commands/serve.py:49`
- **Tool:** semgrep (`wildcard-cors`)
- **Confidence:** real default, low-confidence as a vulnerability
- **Why it matters:** `ag2 serve` exposes an agent as a FastAPI REST API with
  `allow_origins=["*"]` and **no authentication** on the `POST /chat` route, and
  the command ships a built-in `--ngrok` flag that publishes the endpoint to the
  internet (the MCP variant binds `host="0.0.0.0"`). Because AG2 agents can carry
  code-execution tools, an unauthenticated, publicly-reachable `/chat` is a
  sharper exposure than a typical "serve my API" helper — anyone who finds the
  URL can drive the agent (and spend the operator's LLM budget).
- **Why it stays a note, not an issue:** The wildcard CORS carries no
  `allow_credentials=True`, so it isn't the cookie-theft variant — the real gap
  is "no auth option on an opt-in serve command," which is a property the
  operator opts into, not a vulnerability the framework forces. A focused
  hardening would be an optional `--api-key`/bearer guard and a `localhost`
  default for REST, with a loud note on `--ngrok`. Worth considering; below the
  bar for an unsolicited issue on a project this security-aware.

## Patterns observed

**A code-execution framework inverts the usual curation question.** For most
repos the job is finding the one dangerous call in a sea of safe ones. For AG2
the dangerous calls *are* the API — `exec`, `docker run`, `LocalCommandLineCodeExecutor`,
Jupyter kernels — and the job flips to "is there execution the framework didn't
mean to allow, and is the one real injection boundary guarded?" The answer is no
unintended execution and yes guarded: the `ContextExpression` eval, the single
place where attacker-influenced data meets `eval()`, is escaped and carries a
GHSA reference. That's the signature of a project that has already done its own
security review.

**The false-positive profile is textbook, and the maintainers pre-annotated
it.** 18 `insecure-websocket` hits are mostly `ws://` in blog/docs `.mdx` files;
the secret scanner fires on docstring examples and a renderer's string
constants. The `# pragma: allowlist secret` on the docstring key is the
detail that matters — it means the maintainers already ran a secret scanner,
saw the same FP, and suppressed it. Re-reporting it as "high" would be noise.

**The residual is a missing feature, not a flaw.** The honest takeaway from AG2
is the `ag2 serve` exposure story: no auth, wildcard CORS, an internet-exposure
flag, on a framework whose agents can run code. It's a real hardening
opportunity, but it's gated entirely behind operator choices (build a
code-exec agent, serve it, expose it) and the CORS is the credential-less
variant. On a sophisticated, responsive, Apache-community project that has
demonstrably patched its own eval-injection, the disciplined call is to
document it here rather than file a marginal issue — the same call the Kiln
scan reached the day before.

## Notes on the tool

- **`eval`/`exec` findings need a "guarded?" check before severity.** AG2's
  `eval` is escaped and GHSA-referenced one line up; the scanner reported it at
  full severity anyway. This is the same mitigation-awareness gap the openmed
  (`trust_remote_code` allowlist) and Kiln scans surfaced — when a dangerous
  primitive sits inside a documented guard, the effective severity should drop.
  Backlog item.
- **Code-execution frameworks need a project-class signal.** For a repo whose
  purpose is running code, `exec-detected` / `docker-arbitrary-container-run` /
  `LocalCommandLineCodeExecutor` are product surface, not findings. A
  "this project is a code executor" mode (or a per-finding "is this the
  intended executor?" check) would cut the bulk of AG2's high-severity count.
- **`# pragma: allowlist secret` should suppress the secret scanners.** Five of
  the gitleaks hits sit on lines the maintainers already annotated for
  `detect-secrets`. AG2 PatchLab should honor that pragma (and the
  `detect-secrets` baseline convention generally) so a repo's own triage carries
  over. Backlog item.
- **`.mdx` / `website/docs` should be candidate-FP like `tests/`.** 13 of the
  18 `insecure-websocket` hits and several secret hits were documentation
  examples. Docs subtrees deserve the same auto-FP flagging as test/sample dirs.

## Disclosure timeline

- 2026-06-26 — scan run
- 2026-06-26 — public post (this page); post-only, no upstream issue filed

This is a post-only write-up. Curation found no real, reachable, undefended
item that clears the quality gate: the code-execution surface is the documented
product, the one eval-injection boundary is patched against AG2's own GHSA, the
secret hits are pre-annotated false positives, and the `ag2 serve` exposure is a
hardening opportunity gated behind operator choices, below the bar for an
unsolicited issue.

## Reproduce

```bash
git clone https://github.com/ag2ai/ag2 /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/ag2ai-ag2 \
  --min-severity medium --ignore-samples
```
