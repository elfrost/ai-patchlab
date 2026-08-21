---
layout: default
title: "potpie-ai/potpie: security scan"
description: "Security scan of potpie-ai/potpie: 96 findings, 0 real — 15th clean scan: a code-context-graph SDLC platform (FastAPI + a subprocess sandbox + repo"
date: 2026-07-13
---

# potpie-ai/potpie - security scan

**Repository:** [potpie-ai/potpie](https://github.com/potpie-ai/potpie)
**Commit scanned:** `5631cd0b885d0dd3511bf860b458e588027ee8e8`
**Scan date:** 2026-07-13
**Disclosure status:** public — post-only (strict-norm: commercial backing; nothing cleared the quality gate)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 28 |
| Medium | 68 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 96 (0 real after curation)

potpie turns a codebase and its SDLC into a context graph for AI agents — a
FastAPI platform that ingests repositories, runs a code-execution sandbox, and
serves an API, with a hosted product at potpie.ai. That's a wide surface
(CORS/auth, a subprocess sandbox, repo ingestion), so this scan is a
completeness sweep of the dangerous bits. It comes back clean: the two things a
scanner *did* flag — subprocess execution and CORS — are both handled correctly,
and the 96-finding count is dominated by a `legacy/` tree and workflow lint.

## Top findings

### 1. The `subprocess-injection` hits are the sandbox executor, and it quotes safely

- **File:** `potpie/sandbox/.../local/subprocess_runtime.py:97`, `.../docker/runtime.py:173`
- **Tool:** semgrep (`subprocess-injection`)
- **Confidence:** high — by-design, injection-safe
- **Why it matters:** potpie ships a sandbox that runs commands for agents — a
  local subprocess runtime and a Docker runtime. `subprocess.run` on a dynamic
  command is exactly what an injection rule flags, and on a code-runner it's the
  first thing to check.
- **Why it's not a finding:** The command builder is safe by construction.
  `_command()` returns `list(request.cmd)` — an **argv list, no shell** — by
  default; only when `request.shell` is explicitly set does it build a string,
  and then it **`shlex.quote`s every part** (`" ".join(shlex.quote(p) for p in request.cmd)`).
  There's no `shell=True` anywhere in the repo. So the "injectable" command is
  either an argv vector (not shell-parsed) or individually shell-escaped, and a
  Docker-isolated runtime is available alongside the local one. This is the AG2
  pattern — running code is the product — done with correct quoting.

### 2. CORS is secure-by-default in a dedicated hardening module

- **File:** `potpie/context-engine/adapters/inbound/http/_hardening.py`
- **Tool:** manual completeness sweep
- **Confidence:** high — by-design, correct
- **Why it matters:** A repo-ingesting API with wildcard CORS + credentials is
  the recurring dangerous shape (ReMe, Yuxi). potpie has a `_hardening.py`, so
  the question is whether it's real hardening.
- **Why it's not a finding:** It's the correct pattern. Origins come from
  `CONTEXT_ENGINE_CORS_ORIGINS` (env), **defaulting to empty**; and the
  middleware is `allow_credentials=bool(origins)` with
  `allow_methods/headers=["*"] if origins else []`. So the default is
  *no cross-origin access at all*, credentials are enabled only when an operator
  sets an explicit allowlist, and there is never wildcard-origins-with-credentials.
  The same module adds security headers (`X-Content-Type-Options: nosniff`, …),
  a max-body-size cap, and rate-limiting on `/webhooks` and `/api/v1/context`.
  This is the Yuxi env-allowlist fix, shipped by default.

### 3. The count is a `legacy/` tree, workflow tags, and lint

- **Tool:** semgrep + gitleaks + trivy
- **Confidence:** high — FP / out-of-scope
- **Why it matters / why it doesn't:** 7 of the highs are in `legacy/` (an old
  alembic migration + six deployment Dockerfiles) — not the current
  `potpie/` product. 20 more are `github-actions-mutable-action-tag`
  (SHA-pinning hardening). The rest are `dynamic-urllib` on operator-directed
  repo/URL ingestion, `python-logger-credential-disclosure` (debug context, not
  raw secrets), and `uv-missing-dependency-cooldown`. All 3 gitleaks hits are a
  `.env.template` and two test fixtures; trivy found **zero** dependency
  vulnerabilities (its 13 hits are Dockerfile misconfigurations in `legacy/`).

## Patterns observed

**The rich surface was the point, and it held.** A repo-ingesting agent platform
with a subprocess sandbox and a public API is exactly where you'd expect a real
finding — an unquoted command, a wildcard-CORS-with-credentials, an SSRF on
clone. The completeness sweep walked each one and each was already handled:
argv/`shlex.quote` on the executor, an env-allowlist with credential-gating on
CORS, operator-directed (not attacker-directed) ingestion. The tell is a file
literally named `_hardening.py` that does what it says.

**Separating `legacy/` first collapses the count.** This is the monorepo
ownership-split move again: 7 of 28 highs and all 13 trivy misconfigs live in a
`legacy/` tree that isn't the shipped product. Auto-flagging a `legacy/`
directory as candidate-FP (like `tests/`) would have moved the report's center
of gravity to the ~handful of current-code findings, which then curate to
by-design.

**Strict-norm, and clean anyway.** potpie has a commercial hosted tier
(potpie.ai), so grouped issues are off the table by policy — but there was
nothing to file: the deps are clean, the code-execution and CORS surfaces are
correctly built, and the residue is lint. Post-only, crediting the hardening.

## Notes on the tool

- **`subprocess-injection` should check the command constructor.** Both hits ran
  through a builder that returns argv or `shlex.quote`s each part — the rule
  fired on the `subprocess.run(cmd)` call without seeing the quoting one function
  up. A check for "is `cmd` a list, or shell-escaped?" would suppress these, the
  same shape as the parameterized-SQL false positives.
- **`legacy/` deserves candidate-FP flagging.** A top-level `legacy/`
  (or `deprecated/`, `old/`) tree is out-of-scope for the shipped product the
  same way `tests/` is; flagging it would have removed 7 highs + 13 trivy
  misconfigs from the headline.
- **`github-actions-mutable-action-tag` (20) again dominates** a scan's
  high/medium count. A single repo-level "actions SHA-pinned?" line would
  compress this recurring hardening class — noted on mcp-atlassian too.

## Disclosure timeline

- 2026-07-13 — scan run
- 2026-07-13 — public post (this page); post-only, no upstream issue filed

This is a post-only clean-scan write-up. The sandbox executor is argv/`shlex.quote`-safe
with a Docker-isolated option, CORS is env-allowlisted and credential-gated by
default in a dedicated hardening module, dependencies are clean, and the finding
count is a `legacy/` tree plus workflow lint. Nothing cleared the quality gate.

## Reproduce

```bash
git clone https://github.com/potpie-ai/potpie /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/potpie-ai-potpie \
  --min-severity medium --ignore-samples
```
