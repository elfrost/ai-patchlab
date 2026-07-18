---
layout: default
title: "algorithmicsuperintelligence/optillm: security scan"
date: 2026-07-18
---

# algorithmicsuperintelligence/optillm - security scan

**Repository:** [algorithmicsuperintelligence/optillm](https://github.com/algorithmicsuperintelligence/optillm)
**Commit scanned:** `eaf171aa6da5682ba1014ef342556f40247f5b35`
**Scan date:** 2026-07-18
**Disclosure status:** disclosed (one focused issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 1 |
| Medium | 56 |
| Low | 0 |
| Info | 0 |

**Total findings:** 57 (1 real residual after curation)

OptiLLM is an OpenAI-API-compatible **optimizing inference proxy** (4.2k★): you
point your client at it, it applies a reasoning technique (MoA, MCTS, best-of-n,
a Z3 solver, code execution, URL reading, web search, deep research…) and
forwards to the real model behind a configured `base_url`. So the interesting
surface is the *proxy*: how it authenticates callers, what it forwards, and what
its approaches reach out to. Most of it is done carefully. One egress path isn't
guarded, and that's the finding.

## The one that matters: `readurls` fetches attacker-named URLs with no SSRF guard

- **File:** `optillm/plugins/readurls_plugin.py:47` (`fetch_webpage_content`)
- **Tool:** none — semgrep-blind (SSRF via `requests.get` on a regex-extracted URL)
- **Confidence:** high (client-reachable when the proxy is exposed)
- **Why it matters:** The `readurls` approach extracts every `https?://…` URL from
  the prompt with a bare regex (`readurls_plugin.py:12`) and calls
  `requests.get(url, headers=headers, timeout=10, verify=verify)` on each — with
  **no host resolution, no private-IP block, no loopback/link-local block, no
  metadata-endpoint block**. A caller selects the approach by request field
  (`optillm_approach`) or model slug (`readurls-<model>`), so on any hosted /
  multi-client deployment (`--host 0.0.0.0`) a prompt containing
  `http://169.254.169.254/latest/meta-data/iam/security-credentials/…` or
  `http://127.0.0.1:<internal-port>/…` makes the proxy fetch it and return the
  body in the completion. Classic server-side request forgery on a URL-fetcher.
- **Recommendation:** Before fetching, resolve the host and refuse RFC 1918,
  loopback, and link-local (`169.254.0.0/16`, incl. the cloud metadata IP) unless
  an operator explicitly opts in — the same secure-by-default shape
  [IBM/mcp-context-forge](ibm-mcp-context-forge.html) ships in its
  `SecurityValidator._validate_ssrf`. A ~20-line guard on `fetch_webpage_content`
  closes it without changing the happy path.

This is the same class as [a2a-python](a2aproject-a2a-python.html)'s
push-notification webhook (undefended, deployer-hardening note) and
[IBM/mcp-context-forge](ibm-mcp-context-forge.html)'s gateway egress (thoroughly
defended). OptiLLM sits at the a2a end: the guard is simply absent, and here the
URL is *fully attacker-chosen* (it comes from the prompt), not a registered
webhook — which is why it's worth a filing rather than a footnote.

## What the maintainer already does well

Before the residual, the defenses — because they're the reason the other 56
findings collapse:

- **Auth is timing-safe and opt-in the right way.** `check_api_key`
  (`server.py:690`) gates every request when `OPTILLM_API_KEY` is set and compares
  with `secrets.compare_digest` (`server.py:701`) — no string `==`, no timing
  oracle.
- **Localhost by default.** The server binds `127.0.0.1` unless you pass
  `--host 0.0.0.0`, and the code says so in a comment (`server.py:193`): *"Default
  to localhost for security."* External exposure is a deliberate operator choice,
  which is exactly what scopes the SSRF above.
- **No wildcard CORS.** There's no `flask_cors` / `CORS(app)` anywhere — the proxy
  doesn't hand its origin to the browser.
- **`base_url` is operator-set, not client-controlled** (`server.py:768`), so the
  *forwarding* path can't be redirected by a caller — the SSRF is confined to the
  opt-in `readurls` approach, not the core proxy.

## What looks scary but isn't

- **`exec` in the Z3 solver** (`z3_solver.py:138`) and the **`executecode`
  plugin** (Jupyter `ExecutePreprocessor`, `executecode_plugin.py:45`) both run
  model- (and, for `executecode`, request-) supplied Python **on the host with no
  sandbox**. On a code-executor product this is the *feature*, not the bug: these
  are advertised approaches whose literal job is to run code
  (`"The code will be automatically executed when submitted."`), opt-in per
  request, in the same spirit as [ag2](ag2ai-ag2.html). The honest framing is a
  **deployment caveat** — don't expose a proxy with `executecode`/`z3` enabled to
  untrusted callers — not a code fix. (Contrast [Agently](agentera-agently.html),
  where the problem was a component that *advertised* a sandbox it didn't enforce;
  OptiLLM advertises no sandbox, so there's no broken promise.)
- **`non-literal-import`** (`plugins/proxy/approach_handler.py:83`) — FP. The
  `import_module(module_path)` argument comes from a **hardcoded internal dict**
  of approach modules (`mcts`, `bon`, `moa`, …), never from user input.
- **Workflow `run-shell-injection`** (`publish-docker-manifest.yml:68`) — the lone
  "high". `github.event.workflow_run.head_branch` is interpolated into a `run:`
  block, but the trigger chain is `release: created` → `workflow_run`, so
  `head_branch` traces back to a **maintainer-created release tag**, not a fork.
  Not outsider-exploitable; still worth the standard hardening (assign to an `env:`
  var, reference `"$VERSION"`).
- **51× `github-actions-mutable-action-tag`** — the bulk of the count. Actions
  pinned to `@v3`/`@v4` instead of a commit SHA: real supply-chain hardening, but
  best-practice, not a vulnerability — and low-value advice for a maintainer who
  already runs their own `security-scan.yml`.
- **2× `automatic-memory-pinning`** — a Trail of Bits *torch performance* rule in a
  training script, not security.

## Secondary note (defense-in-depth, not filed)

`server.py:713` logs the caller's bearer token at DEBUG
(`logger.debug(f"Intercepted Bearer Token: {bearer_token}")`). Since OptiLLM
supports "bring-your-own-key" pass-through (a client key starting with `sk-`
becomes the upstream key, `server.py:797`), that log line can write a **real
provider API key** to disk when debug logging is on. Redact to a prefix
(`sk-…{last4}`) or drop the value. Debug-gated, so a hardening nit rather than a
filing.

## Patterns observed

This is the **credit-the-defense** scan again, and the third proxy/gateway in a
row ([codex-lb](soju06-codex-lb.html), [IBM/mcp-context-forge](ibm-mcp-context-forge.html),
now OptiLLM) where the finding count is dominated by CI lint and the real question
is one the scanner can't ask: *for every place the service reaches out, is the
egress bounded?* OptiLLM bounds the two that a scanner would worry about — the
core forward (operator-set `base_url`) and auth (timing-safe, localhost default) —
but the **plugin egress** surface is where it drifts. Of the URL-touching
approaches (`readurls`, `web_search`, `deep_research`, `mcp`), `readurls` is the
one that fetches a **fully caller-chosen URL** with no allow/deny on the
destination host. That's the whole delta between "well-built proxy" and "filed
issue."

The other pattern worth naming: on a **code-executor** framework the severity
histogram lies twice. It over-counts (51 action-pin lints, 2 torch-perf hits) and
it *mis-frames* — the two `exec`/`ExecutePreprocessor` sites read as critical RCE
but are the advertised product, while the genuinely interesting item (`readurls`
SSRF) carries **no scanner flag at all**. The curation move that pays off is the
one from the [ag2](ag2ai-ag2.html) / [Agently](agentera-agently.html) lineage:
separate "runs code by design" from "reaches the network by accident," and check
whether each advertised boundary is honest. OptiLLM's code-exec is honest; its
URL-fetch quietly reaches further than "fetch a webpage" implies.

## Notes on the tool

- **SSRF on a prompt-derived URL is still invisible to the pipeline.** `readurls`
  is the fourth undefended-or-defended egress path the series has had to trace by
  hand ([a2a-python](a2aproject-a2a-python.html), [IBM](ibm-mcp-context-forge.html),
  [tradingview-mcp](atilaahmettaner-tradingview-mcp.html), now OptiLLM). Backlog
  item stands: a taint-lite check for `requests.get`/`httpx.get` whose URL
  argument is not a module constant, emitting a *candidate*-SSRF that the reviewer
  confirms by checking for a private-IP guard.
- **The action-pin cluster (51) is the recurring CI-lint over-count** — same shape
  as inspect_ai (62) and datachain (26). It's real best-practice but rarely the
  story; it should be foldable to a single grouped "pin N actions to SHA" line so
  it stops dominating the severity histogram.
- **`--min-severity medium` still surfaced the workflow lint as a `high`** while
  the one real item was scanner-silent — another data point that severity rank
  and *interest* rank are different axes on these targets.

## Disclosure timeline

- 2026-07-18 - scan run (commit `eaf171aa`)
- 2026-07-18 - focused issue filed upstream ([#323](https://github.com/algorithmicsuperintelligence/optillm/issues/323), readurls SSRF)
- 2026-07-18 - public post (this page)

## Reproduce

```bash
git clone https://github.com/algorithmicsuperintelligence/optillm /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/algorithmicsuperintelligence-optillm --min-severity medium
```
