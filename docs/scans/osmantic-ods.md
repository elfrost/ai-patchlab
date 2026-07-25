---
layout: default
title: "Osmantic/ODS: security scan"
date: 2026-07-25
---

# Osmantic/ODS — security scan

**Repository:** [Osmantic/ODS](https://github.com/Osmantic/ODS)
**Commit scanned:** `2e8446ecd9481b098c6f418a587f42d95e3c7e2d`
**Scan date:** 2026-07-25
**Disclosure status:** public — post-only (strict-norm: private-reporting SECURITY.md + `SECURITY_AUDIT.md` receipts + commercial backing)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 20 |
| Medium | 53 |
| Low | 0 |
| Info | 0 |

**Total findings:** 73 (0 real after curation)

ODS — the Osmantic Deployment System — turns a PC, Mac, or Linux box into a
private, self-hosted AI server: local model inference, a ChatGPT-style web UI,
a control dashboard, voice/agents/workflows, RAG, and image generation, wired
together over Docker (Ollama, Open WebUI, n8n, ComfyUI, and friends). That is a
wide, dangerous-looking surface — a service that manages Docker, secrets,
network exposure, OAuth credentials, and host-side installer state. For an
appliance like this the three questions are: *is the dashboard's reverse proxy
an SSRF/host-spoof pivot?*, *are the service-to-service credentials handled and
logged safely?*, and *is the SQL that fronts the token-usage store injectable?*
All three close, and they close because ODS already did the work — it ships its
own `SECURITY_AUDIT.md` with `B1`/`B2` fix markers that show up as comments in
the very files the scanner flagged.

## Top findings (all curated out)

### 1. SQL "highs" in token-spy — parameterized-identifier FP, and a textbook one

- **File:** `ods/extensions/services/token-spy/db.py:104,133,147,379,412`
- **Tool:** semgrep (`sqlalchemy-execute-raw-query` ×5 + `formatted-sql-query`)
- **Verdict:** false positive — **credit the defense**
- Every data value is a bound `?` parameter. The only f-string tokens are
  (a) column names drawn from a **hardcoded `cols` list** / an
  `ALLOWED_COLUMNS` dict, and (b) a `_RECENT_TS_BOUND` **constant** SQL fragment
  whose relative-time offset (`f"-{hours} hours"`) is itself passed as a bound
  param. The migration path (`ADD COLUMN {col}`) additionally validates each
  identifier against a `SAFE_IDENTIFIER` regex *even though the name is
  hardcoded* — with a comment saying so ("Defense in depth… protects against
  future refactoring"). This is the [#1 recurring identifier
  FP](mnemosyne-oss-mnemosyne.html), handled about as well as it can be.

### 2. `detect-insecure-websocket` ×4 — scheme-preserving, plus two non-code matches

- **File:** `hermes_bridge.py:120`, `inject-token.js:250`, `requirements.txt:5`, `SECURITY_AUDIT.md:47`
- **Tool:** semgrep (`javascript.lang.security.detect-insecure-websocket`)
- **Verdict:** false positive
- `hermes_bridge.py` builds its WS URL by **upgrading** `http→ws` / `https→wss`
  from a local base URL (and fetches a token first, appending `?token=…`) — the
  same scheme-preserving pattern credited in the [gpustack](gpustack-gpustack.html)
  scan, not a forced-plaintext downgrade. `inject-token.js` mirrors the page
  protocol (`location.protocol === "https:" ? "wss://" : "ws://"`). The other
  two "hits" are a **comment** in a `requirements.txt` and a line in the
  project's own **audit document**.

### 3. `run-shell-injection` ×5 — non-privileged / maintainer-only workflow triggers

- **File:** `.github/workflows/claude-review.yml:86,170,268`, `nightly-code-review.yml:58`, `nightly-docs-update.yml:58`
- **Tool:** semgrep (`github-actions.security.run-shell-injection`)
- **Verdict:** hardening, not exploitable
- `claude-review.yml` runs on **`pull_request`** (not `pull_request_target`) and
  the interpolated value is `github.base_ref` — the *target* branch, controlled
  by the maintainer's repo, not the attacker's `head_ref`. The nightly
  workflows are **`workflow_dispatch`** (schedule commented out) with a
  `type: number` input — maintainer-only, the
  [openmed](maziyarpanahi-openmed.html) trigger-context lesson. Env-var
  indirection is a nice defense-in-depth, but there's no fork-driven path here.

### 4. `dynamic-proxy-host` ×5 (nginx) — hardcoded internal upstream, Bearer-auth injected

- **File:** `ods/extensions/services/dashboard/nginx.conf:31,50,67,83,99`
- **Tool:** semgrep (`generic.nginx.security.dynamic-proxy-host`)
- **Verdict:** false positive — **credit the defense**
- `proxy_pass http://$dashboard_api_upstream` reads a variable — but the
  variable is a **constant** (`set $dashboard_api_upstream dashboard-api:3002;`),
  used only to force nginx to re-resolve Docker's DNS at request time (the
  comment explains: service IPs change on lifecycle recreation). No
  request-derived value (`$host`, path, header) reaches `proxy_pass`, and every
  proxied location **injects an `Authorization: Bearer` header** from a key read
  out of the environment by the entrypoint (the `B1`/`B2` fixes). Not a
  host-spoof pivot.

### 5. `logger-credential-disclosure` ×7 — the secret's *path* is logged, never its value

- **File:** `dashboard-api/security.py:20`, `token-spy/main.py:285`, `agent_monitor.py:135/159/163`, `ape/main.py:1005`, `ods-host-agent.py:3891`
- **Tool:** semgrep (`logging.logger-credential-leak`)
- **Verdict:** false positive — **credit the defense**
- The two that matter are the secure key-bootstrap fallbacks: when
  `DASHBOARD_API_KEY` / `TOKEN_SPY_API_KEY` isn't set, ODS generates one with
  `secrets.token_urlsafe(32)`, writes it with `chmod(0o600)`, and logs the
  **file path** ("wrote to %s (mode 0600)") — not the key. `agent_monitor` only
  ever uses the token to build a `Bearer` header. The rule fires on the variable
  being in scope near a log call.

## Patterns observed

**This is a security-mature project scanned, not a project being audited for the
first time.** ODS ships a real, non-default `SECURITY.md` that asks for private
vulnerability reporting, a `SECURITY_AUDIT.md` that tracks historical findings +
remediation + regression evidence, an operator-hardening guide (`ods/SECURITY.md`),
and an installer-trust doc. The fingerprints of that discipline are everywhere in
the code the scanner flagged: `B1`/`B2` fix markers in `nginx.conf`, a
defense-in-depth regex on a *hardcoded* SQL identifier, `0o600` on every
generated secret, path-only logging, and an `inject-token.js` branch literally
commented "Auto-token injection disabled to prevent gateway-token disclosure."
The scanner's 20 "highs" are the hardening itself, twice over.

**The residuals are all operator-gated and already inside the project's own
threat model.** Three worth naming, none a filing: (1) the dashboard SPA carries
four **react-router** advisories (open-redirect / XSS / constructor-injection),
but the dashboard is localhost-bound (`nginx listen 3001; server_name
localhost;`) and Bearer-gated — a frontend dependency refresh, reachability-gated
([Kiln](kiln-ai-kiln.html) lockfile-coverage shape); (2) the model-serving images
(`bark`, `llama-server`, `llama-sycl`) run as **root** — common for GPU images,
localhost-scoped, and `SECURITY.md` already flags LAN exposure as high-risk;
(3) GHA action tags use mutable refs (pin to SHA). ODS's own `SECURITY.md` states
the same posture I'd write in a hardening note — "ODS defaults to localhost-bound
services… do not expose a default install directly to the public internet without
an additional security review." When the maintainer's threat model and the
scanner's residuals agree, there's nothing to file.

**The count is a shape, not a risk signal — again.** 73 findings, 0 real, on one
of the richer surfaces in the series (Docker orchestration + secrets + a
credential-injecting reverse proxy + a token-usage SQL store). The clusters that
looked scary — five SQL highs, five "dynamic proxy hosts," seven "credential
leaks" — are the three questions above, each answered correctly in the code.

## Notes on the tool

- **`detect-insecure-websocket` fires on comments and non-code files.** Two of
  the four hits were a `# … ws:// …` comment in a `requirements.txt` and a line
  in `SECURITY_AUDIT.md`. Backlog: the JS websocket rule shouldn't match inside
  Python comment lines / `.md` prose (recurring non-code-match class, alongside
  the [ag2](ag2ai-ag2.html) `.mdx` and pragma-allowlist notes).
- **`dynamic-proxy-host` needs the `set $var … ;` constant check.** When the
  proxied variable is assigned a literal upstream earlier in the same server
  block, it isn't a dynamic host — same "constant-authority" shape as the
  [tradingview-mcp](atilaahmettaner-tradingview-mcp.html) URL note, now on nginx.
- **`logger-credential-leak` remains a five-plus-for-five FP source** whenever
  the logged interpolation is a *path* and the secret variable is merely nearby.
  Consistent with [honcho](plastic-labs-honcho.html); the rule wants dataflow
  from the secret value into the format args, not scope proximity.
- Semgrep report was healthy (359 KB, 64 results, 75 non-fatal parse errors on
  non-Python config files, 937 paths scanned) — no
  [0-byte silent-failure](dataelement-clawith.html) recurrence.

## Disclosure timeline

- 2026-07-25 — scan run; 73 findings, 0 real after curation
- 2026-07-25 — public post (this page); **post-only**, no upstream issue (strict-norm: private-reporting SECURITY.md, `SECURITY_AUDIT.md` receipts, commercial backing at osmantic.com), and the quality gate is false

## Reproduce

```bash
git clone https://github.com/Osmantic/ODS /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/osmantic-ods --min-severity medium
```
