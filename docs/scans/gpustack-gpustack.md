---
layout: default
title: "gpustack/gpustack: security scan"
description: "Security scan of gpustack/gpustack: 136 findings, 0 real — 22nd clean scan: a GPU cluster manager for AI model serving (5.4k★, Apache-2.0"
date: 2026-07-24
---

# gpustack/gpustack — security scan

**Repository:** [gpustack/gpustack](https://github.com/gpustack/gpustack)
**Commit scanned:** `6bc353b253eb`
**Scan date:** 2026-07-24
**Disclosure status:** public (post-only — clean scan)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 74 |
| Medium | 61 |
| Low | 0 |
| Info | 0 |

**Total findings:** 136 (0 real after curation) — **22nd clean scan**

GPUStack is a **GPU cluster manager for high-performance AI model serving**
(5.4k★, Apache-2.0, 97% Python) — it registers worker nodes, proxies OpenAI-
compatible inference to vLLM/SGLang backends, exposes API-key auth, and offers
on-demand SSH-accessible GPU instances. For a serving control-plane the three
questions that decide everything are **(1) is the model-proxy an open SSRF
pivot?**, **(2) is the worker↔server tunnel authenticated?**, and **(3) is
credential / API-key handling sound?** — and GPUStack answers all three well.
The 136 findings collapse to zero real ones: a 46-strong SQL cluster that is
entirely Alembic migration DDL, a `ws://`/file-perms/secret trio that are all
rule artifacts over *correct* code, and a dependency tail that is
reachability-gated.

## Top findings (all resolved to non-issues)

### 1. The one Critical — `asyncmy` SQL-injection CVE — MySQL-backend-gated and ORM-abstracted

- **File:** `uv.lock` (`asyncmy 0.2.11`) — CVE-2025-65896
- **Tool:** trivy
- **Confidence:** high → **dropped (unreachable surface)**
- **Why it matters:** the CVE is a genuine **SQL injection via crafted dict
  keys** in the `asyncmy` MySQL driver, and `asyncmy>=0.2.10` is a *declared
  hard dependency* — so on paper a serving control-plane that stores state in a
  database looks exposed.
- **Verdict:** two independent gates close it. First, **backend selection** —
  GPUStack ships `aiosqlite` (default), `asyncpg`/`psycopg2` (Postgres) *and*
  `asyncmy`/`pymysql` (MySQL); the driver is only in the query path if an
  operator explicitly configures a `mysql://` `--database-url`. Second, and
  decisively, **the exploit primitive isn't exposed**: the crafted-dict-key
  vector requires attacker-controlled *dict keys* reaching the driver's
  `execute`, but all data access rides SQLModel / SQLAlchemy, which binds
  **values** as parameters and treats keys as internal column names. This is
  the [SCA version-match vs reachability](maziyarpanahi-openmed.html)
  distinction — a dependency-hygiene bump worth doing, not an exploitable path
  in this application.

### 2. 46 SQLAlchemy "highs" — the #1 recurring parameterized-**identifier** FP

- **File:** `gpustack/migrations/versions/*.py` (×~45) + `gpustack/utils/sql_enum.py`
- **Tool:** semgrep (`sqlalchemy-execute-raw-query`, `formatted-sql-query`)
- **Confidence:** high → **false positive**
- **Why it matters:** 32 `avoid-sqlalchemy-*` + 14 `execute-raw` + 14
  `formatted-sql` on a networked control-plane reads like an injection fire.
- **Verdict:** every one is [the identifier-interpolation
  FP](mnemosyne-oss-mnemosyne.html). ~45 of them live in **Alembic migration
  scripts** (`gpustack/migrations/versions/…`) — DDL that runs `ALTER TABLE`/
  `CREATE INDEX` against a **hardcoded, developer-authored schema** with no
  user input anywhere in the process ([codex-lb](openai-codex.html) taught this:
  auto-flag `alembic/versions/**`). The rest are `sql_enum.py`, a helper that
  f-strings **internal enum/column names** into DDL. No end user picks a table
  or column identifier; no value is interpolated. Two representative migrations
  settle all 46.

### 3. Model-proxy "tainted-url-host" — `worker_auth`-gated, host from cluster state

- **File:** `gpustack/routes/worker/proxy.py:77`
- **Tool:** semgrep (`tainted-url-host`)
- **Confidence:** high → **by-design (no SSRF)**
- **Why it matters:** `/proxy/{path:path}` forwards inference requests upstream
  by building `url = f"http://{worker_ip_getter()}:{target_service_port}/{path}"`
  — the marquee SSRF shape for a serving proxy.
- **Verdict:** the **authority is not user-controlled**. The whole route is
  `APIRouter(dependencies=[Depends(worker_auth)])`, so only an authenticated
  cluster principal reaches it. The host comes from `worker_ip_getter()` —
  server-side app state populated from the cluster's own registered-worker
  table — and the port from a routing header the gateway sets, not a free-form
  client field. The attacker-influenced `path`/query land **after** the fixed
  `host:port/`, so they can't relocate the request to a new host. This is
  intra-cluster routing to a registered worker, not an open egress
  ([credit-the-defense](ibm-mcp-context-forge.html), the guarded inverse of
  [optillm](algorithmicsuperintelligence-optillm.html)).

### 4. `security.py` "generic-api-key" — a docstring example over exemplary crypto

- **File:** `gpustack/security.py:71`
- **Tool:** gitleaks + semgrep
- **Confidence:** high → **false positive**
- **Why it matters:** a secret flagged inside the module literally named
  `security.py` demands a look.
- **Verdict:** line 71 is inside a **docstring** documenting the API-key format
  (`access_key: "3192253c"`, `secret_key: "c11c75ed6334ea9505da4ad9"`) — example
  values, not live credentials. The module itself is a model of good hygiene:
  password verification via **argon2** `PasswordHasher`, key hashing via
  **blake2b**, and generation via the **`secrets`** module. This is the
  [docstring/example-key FP](kiln-ai-kiln.html) sitting on top of code doing
  everything right.

### 5. Four "insecure-websocket" + a "world-readable" file-perms flag — rule artifacts over correct code

- **Files:** `gpustack/websocket_proxy/{main,message_client,message_server}.py`,
  `gpustack/server/server.py:600`
- **Tool:** semgrep (`detect-insecure-websocket`, `insecure-file-permissions`)
- **Confidence:** high/medium → **false positive (one operator-network note)**
- **Why it matters:** `ws://` and `os.chmod` both trip loud rules on a system
  that tunnels worker traffic and writes local sockets.
- **Verdict:** the `ws://` hits at `main.py:38/226` are a **module docstring and
  a `logger.debug` f-string** in a demo harness; `message_client.py:45` is
  `endpoint.replace('https://','wss://').replace('http://','ws://')` — it
  *preserves* the configured scheme (**upgrades to `wss://` whenever the
  operator uses https**), the opposite of forcing plaintext. The only real
  `ws://` literal is server-to-server **federation** (`message_server.py:266`),
  which runs between operator-registered peers with an authenticator injecting
  headers on every connect — a trusted-network transport note, not a client
  exposure. And the file-perms hit is [active-harm-FP territory](stickerdaniel-linkedin-mcp-server.html):
  `server.py:600` does `os.chmod(socket_dir, 0o700)` on a `mkdtemp` whose
  socket name is `secrets.token_hex(8)` — owner-only perms on a randomized path,
  which is *exactly* right. The rule's instinct would loosen it.

## Patterns observed

**A serving control-plane where the count scales with schema churn, not risk.**
GPUStack's 136 findings are dominated by two structural artifacts — 46 SQL flags
that are all migration/enum DDL, and 29 GitHub-Actions `mutable-ref` flags
(pin-your-actions-to-a-SHA hardening) — neither of which touches an
attacker-reachable surface. Strip those and the "attack surface" of a GPU
cluster manager turns out to be **narrow and well-tended**: one authenticated
model-proxy, one authenticated worker tunnel, and one API-key module built on
argon2/blake2b/`secrets`. The team's security instincts show in the details
that rules can't credit — the `0o700` randomized unix socket for the operator
gateway, the scheme-preserving websocket upgrade, the `worker_auth` dependency
stapled to the proxy router.

**The dependency tail is the honest residual, and it's reachability-gated.**
Beyond the MySQL-gated `asyncmy` Critical, trivy surfaces two `pyasn1` DoS CVEs
(transitive, only reachable when parsing attacker-supplied ASN.1) and a
build-time `setuptools` sdist-normalization issue (not a runtime path). There's
no `dependabot.yml` or `renovate.json` in the repo, but with daily merges from
multiple maintainers this is a project that clearly tracks its stack by hand —
so this stays a *note*, not a manufactured "wire up Dependabot" issue
([Kiln](kiln-ai-kiln.html) lesson: don't invent process work for a sophisticated
maintainer). Refreshing `asyncmy`, `pyasn1`, and `setuptools` is worthwhile
supply-chain hygiene; none of it is exploitable in the shipped default (SQLite)
posture.

**Every secret and every XSS flag dissolved on contact.** All 17 gitleaks hits
are non-secrets: 15 in `tests/fixtures/` model-estimate blobs and
`test_model_routes.py`, one `curl` header in an integration doc, one docstring
example. The 5 `direct-use-of-jinja2` "XSS" findings are **server-side code and
config generation** — `codegen/generate.py` (Python codegen), `cloud_providers/
user_data.py` (cloud-init), `k8s/manifest_template.py` (K8s manifests) — none of
which renders into a browser. Even the trivy "ConfigMap with secrets" flag on
the bundled Higress gateway config resolves to a single `password: ""` (empty).
The one-line takeaway: a GPU serving control-plane can carry a big raw finding
count and still be clean, because the count tracks migration history and CI
lint, not reachable risk.

## Notes on the tool

- **`alembic/versions/**` should be a first-class candidate-FP tier.** 45 of
  46 SQL "highs" were migration DDL. The [codex-lb](openai-codex.html) backlog
  item (auto-flag migration directories) would have collapsed this cluster to a
  single line before curation — this is now the *third* scan
  ([codex-lb](openai-codex.html), [mnemosyne](mnemosyne-oss-mnemosyne.html),
  gpustack) where migrations dominate the SQL count. Promote it.
- **`detect-insecure-websocket` needs to see `.replace()` chains.** Flagging
  `message_client.py:45` — a line that *upgrades* `http→ws`/`https→wss` — as
  "insecure" is a pure literal match. A scheme-**preserving** replace should
  suppress, and docstring/`logger.debug` occurrences of `ws://` should never
  score high.
- **`insecure-file-permissions` should read the octal.** `os.chmod(dir, 0o700)`
  is owner-only and correct; flagging it as "insecure" is the same active-harm
  FP class as the [linkedin-mcp `0o700`](stickerdaniel-linkedin-mcp-server.html)
  case. The rule should only fire on group/other read/write bits.
- **Dependency rows want a "backend-gated?" column.** The `asyncmy` Critical is
  real *only if MySQL is configured*; the default is SQLite. A reachability
  annotation ("requires `--database-url mysql://…`") on driver CVEs would let
  the reader weight it correctly instead of reacting to the word "Critical".

## Disclosure timeline

- 2026-07-24 — scan run (commit `6bc353b253eb`)
- 2026-07-24 — public post (this page); clean scan, no upstream issue filed

## Reproduce

```bash
git clone https://github.com/gpustack/gpustack /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/gpustack-gpustack --min-severity medium
```
