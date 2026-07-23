---
layout: default
title: "EverMind-AI/Raven: security scan"
date: 2026-07-23
---

# EverMind-AI/Raven — security scan

**Repository:** [EverMind-AI/Raven](https://github.com/EverMind-AI/Raven)
**Commit scanned:** `668348301df9`
**Scan date:** 2026-07-23
**Disclosure status:** public (post-only — clean scan, strict-norm repo)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 25 |
| Medium | 62 |
| Low | 0 |
| Info | 0 |

**Total findings:** 87 (0 real after curation) — **21st clean scan**

Raven is a memory-first, self-improving **agent harness** (2.5k★, Apache-2.0,
built on EverOS with MiroThinker deep research). It is ~73% Python: a gateway
that runs agent turns, a tool layer (shell exec, web fetch, media gen, MCP
client), a plugin/provider/channel registry system, an "evolver" that mutates
and re-benchmarks harness variants, and a TUI. For an agent harness the two
questions that decide everything are **(1) can an untrusted party drive the
agent over the network?** and **(2) is the web-fetch surface an open SSRF?** —
and Raven answers both well.

## Top findings (all resolved to non-issues)

### 1. Three MCP Python SDK server-transport CVEs — not reachable (client, not server)

- **File:** `uv.lock` (mcp>=1.27.0)
- **Tool:** trivy
- **Confidence:** high → **dropped (unreachable surface)**
- **Why it matters:** trivy flags three published `mcp` CVEs — HTTP transport
  serving sessions without verifying the authenticated principal, experimental
  task handlers reachable by any client, and WebSocket transport missing
  Host/Origin validation. All three are **server-transport** vulnerabilities.
- **Verdict:** `raven/agent/tools/mcp.py` is literally headed *"MCP client:
  connects to MCP servers and wraps their tools as native Raven tools."*
  `MCPServerConfig` describes **outbound** connections (stdio / sse /
  streamableHttp) to servers Raven consumes. Raven never instantiates the
  vulnerable server transports, so this is version-match without reachable
  surface — the inverse of [code-graph-rag](vitali87-code-graph-rag.html),
  where the project *did* stand up `serve_http()` and CVE-2026-52869 was live.

### 2. Web-fetch SSRF — defended, and defended well

- **File:** `raven/security/network.py` → `raven/agent/tools/web.py:119`
- **Tool:** (scanner-silent — this is credit-the-defense)
- **Confidence:** high
- **Why it matters:** `web_fetch` is a model-callable tool that takes an
  arbitrary `url` argument. On an agent harness this is the marquee SSRF
  vector — steer the agent to read cloud metadata / internal services.
- **Verdict:** `web_fetch` calls `validate_url_target(url)` **before** the
  fetch. The guard enforces an `http`/`https` scheme allowlist, resolves the
  hostname, and blocks every private/internal CIDR — including
  `169.254.0.0/16` (**cloud metadata / link-local**), `127.0.0.0/8`, RFC 1918,
  CGNAT `100.64.0.0/10`, and the IPv6 equivalents. The DingTalk media adapter
  (`channels/adapters/dingtalk/api.py:102`) goes further still: it follows
  redirects **one hop at a time** with `follow_redirects=False` and
  re-validates every hop via `validate_resolved_url` — closing the
  redirect-to-internal / DNS-rebind gap that most SSRF guards leave open. Same
  egress class as [IBM ContextForge](ibm-mcp-context-forge.html) (defended) and
  [optillm](algorithmicsuperintelligence-optillm.html) / [a2a-python](a2aproject-a2a-python.html)
  (undefended) — Raven sits firmly on the defended side.

### 3. Gateway binds `0.0.0.0` — the default is unused; the real bind is loopback

- **File:** `raven/config/schema.py:463` (`GatewayConfig.host = "0.0.0.0"`)
- **Tool:** semgrep (`0.0.0.0` bind default)
- **Confidence:** high → **dropped (default never consumed)**
- **Why it matters:** the gateway drives agent turns that have shell-exec and
  filesystem tools; a network-exposed, unauthenticated gateway would be an
  agent-hijack surface.
- **Verdict:** `config.gateway.host` is **never read to bind a socket** — the
  only listener in `gateway_commands.py` is a `/health` endpoint pinned to
  `asyncio.start_server(_health_handler, "127.0.0.1", port)` (hardcoded
  loopback). The TUI reaches the gateway over local FIFOs (`tui_rpc/spine.py`),
  not a TCP socket. The `0.0.0.0` default is a defined-but-unused field — no
  exposure results. (A tidy-up nit: drop it or set it to `127.0.0.1` so it
  can't mislead a future reader.)

### 4. Shipped `eval()` in the evolver policy gate — false positive (param name)

- **File:** `raven/evolver/orchestrator/gates/policy.py:191`
- **Tool:** semgrep (`eval-detected`)
- **Confidence:** medium → **FP**
- **Verdict:** `eval` here is a **keyword parameter** —
  `for_round(self, ..., *, eval, ...)` — a passed-in callable that re-runs the
  parent node's benchmark harness (the docstring says so: *"Requires ``eval``
  to reproduce the parent node's harness"*). It shadows the builtin; it is not
  `eval()`. The self-improving evolver never evaluates a string.

### 5. `tarfile.extractall()` without `filter='data'` — benchmark tier, self-produced tars

- **File:** `benchmarks/proactivity_eval/runners/_common/drivers/longrun.py:596`
- **Tool:** trailofbits semgrep
- **Confidence:** high → **not shipped runtime + trusted source**
- **Verdict:** the real Zip-Slip class, but `_untar_checkpoint` expands a
  checkpoint tar that the same module **wrote itself** (`_write_checkpoint`),
  inside `benchmarks/` (an eval harness, not the shipped `raven/` runtime). No
  attacker-supplied archive reaches it. A `filter="data"` bump is still the
  right hardening (à la [inspect_ai](ukgovernmentbeis-inspect-ai.html), which
  ships it with a PEP-706 citation), but there's no live threat path.

## Patterns observed

**The reachability question cut the 25 highs to zero.** Beyond the MCP
client/server split (§1), the two `run-shell-injection` highs in
`release.yml` interpolate `${{ github.ref_name }}` into `run:` — but the
workflow triggers only on `push: tags: v*` and `workflow_dispatch`, both
**privileged** (a fork PR can't push a tag), so the tag name is maintainer-set,
not attacker-controlled — the same trigger-context lesson as
[openmed](maziyarpanahi-openmed.html) and [nexent](modelengine-group-nexent.html).
The two `python37-compatibility` highs are a compat lint, not security. The one
JS `detect-child-process` high is an `execFileNoThrow` wrapper (argv, no shell)
in the TUI.

**The medium tier is the usual scanner-noise census.** The 14 JavaScript
`path-join-resolve-traversal` hits all land in `raven/tracing/viewer/*.js` — a
**localhost tracing viewer** dev tool — plus the WhatsApp bridge. The five
`non-literal-import` hits are the plugin / provider / channel / evolver-launch
**registries** — dynamic import by design, keyed on internal registry names,
the [datachain](datachain-ai-datachain.html) mod-loader pattern. The three
`dynamic-urllib` hits are an **operator-configured** embedding endpoint
(`knn_router.py`, `embedding_endpoint` config — not an attacker URL), a
localhost tracing probe, and a benchmark. The three `sha1` hits are cache keys
and content hashes (`hashlib.sha1(f"{url}|{path}")[:16]` → a filename), not
crypto. The 18 `github-actions-mutable-action-tag` are CI supply-chain lint.
Every single medium resolves to FP, by-design, or CI hygiene.

**What the maintainers do well is the network boundary.** Raven is a
pre-alpha agent harness with shell-exec and filesystem tools — exactly the kind
of project where an SSRF hole or an unauthenticated network listener would be
catastrophic. Instead there's a **dedicated `raven/security/network.py`**
(ported from nanobot, MIT-credited) with a metadata-blocking allowlist wired
into `web_fetch`, a redirect-revalidating variant used by the DingTalk adapter,
a health endpoint pinned to loopback, and TUI↔gateway traffic kept on local
FIFOs. `web_fetch` even routes through Jina Reader (server-side fetch) *and*
validates the target first — defense in depth. For a fast-moving pre-alpha,
that's a notably deliberate posture.

**The one genuine residual is a dependency refresh**, all reachability-gated or
opt-in: `Pillow` (11 memory-safety/DoS CVEs, reachable via multimodal image
handling — the perennial treadmill, à la [SwanLab](swanhubx-swanlab.html)),
`mistune` (DoS + XSS, reached only through the **opt-in Matrix channel's**
markdown→HTML formatter, `channels/adapters/matrix/content.py` — DoS there is
self-inflicted on the agent's own output, XSS is downstream-sanitized by Matrix
clients), plus `json_repair`, `lxml_html_clean`, `protobufjs`, and `setuptools`
tails. Pin/bump hardening, not a filing — and the repo asks for private
vulnerability reporting anyway (see disclosure note).

## Notes on the tool

- **`0.0.0.0` bind default should be reachability-checked, not just pattern-matched.**
  Semgrep flagged `GatewayConfig.host = "0.0.0.0"` as an exposed-bind default,
  but the field is never consumed to bind a socket (the real listener is
  loopback-pinned). A future enrichment could downgrade a `host="0.0.0.0"`
  config default when no `bind`/`start_server`/`serve` call reads it — the same
  "defined-but-unused" shape that has now appeared enough times to be a rule.
- **`eval` / `exec` as a parameter or method name keeps producing FPs.** This
  is the third scan where `eval-detected` fired on a shadowed builtin used as an
  identifier (after [inspect_ai](ukgovernmentbeis-inspect-ai.html)'s public
  `eval()` API and datachain). Worth a heuristic: `eval`/`exec` appearing as a
  bare name in a parameter list or `def` is almost never the builtin.
- **MCP client vs server should be a first-class reachability axis.** Three
  high CVEs collapsed the moment the module docstring said "client." A
  scanner-side signal (does the repo `import`/instantiate an MCP *server*
  transport, or only a client session?) would pre-triage the entire `mcp` CVE
  family the way the SCA reachability lesson pre-triages LiteLLM-Proxy CVEs.

## Disclosure timeline

- 2026-07-23 — scan run at `668348301df9`
- 2026-07-23 — public post (this page). **Post-only:** 0 real findings, and
  Raven ships a real SECURITY.md requesting **private** vulnerability reporting
  via GitHub Security Advisories — no public issue is warranted or appropriate.

## Reproduce

```bash
git clone https://github.com/EverMind-AI/Raven /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/evermind-ai-raven --min-severity medium
```
