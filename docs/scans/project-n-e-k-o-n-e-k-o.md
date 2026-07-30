---
layout: default
title: "Project-N-E-K-O/N.E.K.O: security scan"
date: 2026-07-29
---

# Project-N-E-K-O/N.E.K.O — security scan

**Repository:** [Project-N-E-K-O/N.E.K.O](https://github.com/Project-N-E-K-O/N.E.K.O)
**Commit scanned:** `35073e400bf9`
**Scan date:** 2026-07-29
**Disclosure status:** ✅ **resolved** — fixed upstream in [PR #2559](https://github.com/Project-N-E-K-O/N.E.K.O/pull/2559), merged ~14 hours after filing

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 387 |
| Medium | 394 |
| Low | 0 |
| Info | 0 |

**Total findings:** 783 (1 real after curation)

N.E.K.O. (2.3k★, Apache-2.0) is a **desktop AI companion** — the first
consumer-facing one in this series. It is a "digital life" that lives on your
machine: real-time voice and vision, a five-tier memory system, Live2D / VRM /
MMD / PNGTuber avatars, proactive chat, a plugin marketplace, Steam Workshop
character sharing, and an agent layer that drives your browser and your
computer. It ships free on Steam, runs on 14+ model providers, and is developed
in the open at a remarkable clip — **831 merged PRs from 17 distinct authors in
the last 60 days**.

That shape matters for curation. Almost every scan in this series targets a
*server*, where the first question is "what is exposed to the network?" Here the
answer is: **nothing**. Every core service — main server, memory server, agent
server, plugin host, tool server — binds `127.0.0.1`. So the question flips to
the one that actually applies to a desktop app:

> **Not "what can a remote attacker reach?" but "what can a *web page* reach on
> loopback, while the user is browsing?"**

Asked that way, one endpoint stands out. And the reason it counts as a real
finding rather than a theoretical one is that **N.E.K.O already implements the
correct defence — three times, in three sibling components — just not on the
endpoint that hands out every API key you own.**

## Top findings

### 1. The loopback config API returns every provider API key in plaintext, with no Origin/Host/CSRF check — *scanner-silent*

- **File:** `main_routers/config_router/core_config.py:33` (handler), `:76`–`:102` (the response)
- **Tool:** none — no scanner flagged this
- **Confidence:** high
- **Why it matters:** `GET /api/config/core_api` on the main server
  (`127.0.0.1:48911`, a fixed documented default) returns, unauthenticated and
  **unmasked**, `api_key` plus ~20 per-provider credentials —
  `assistApiKeyOpenai`, `assistApiKeyClaude`, `assistApiKeyGemini`,
  `assistApiKeyDeepseek`, `assistApiKeyGrok`, `assistApiKeyOpenrouter`,
  `assistApiKeyElevenlabs`, `assistApiKeyMinimax`, the Qwen/GLM/Step/Kimi/Doubao
  slots — plus `mcpToken` and the `{conversation,vision,agent,tts,…}ModelApiKey`
  custom-provider keys and their URLs. Masking logic exists in this exact file,
  but only on the **`POST`** side (`_is_masked_secret`, so a `***` placeholder is
  never written back); the `GET` returns raw values.

  The app that serves it is `app = FastAPI()`
  (`app/main_server/__init__.py:500`) with exactly two middlewares —
  a body-size limiter and a startup gate (`:609`, `:578`). There is **no CORS
  middleware, no `TrustedHostMiddleware`, no Host or Origin validation, and no
  auth dependency**; `config_router` is mounted bare
  (`app/main_server/web_app.py:467`).

  No CORS headers means a browser blocks a plain cross-origin *read* — so this
  is not one-click CSRF. It is **DNS rebinding**: an attacker page on a
  low-TTL domain re-resolves to `127.0.0.1`, at which point the request is
  *same-origin* and CORS never enters the picture. The port is a constant, the
  transport is plain HTTP, and a companion app is by design running for hours
  while the user browses. The result is silent theft of every LLM credential the
  user has configured — directly monetisable, and a category of loss the user
  will only notice on their next invoice.

- **Recommendation:** Reject requests whose `Host` header is not loopback. **The
  fix is already written in this repository** —
  `plugin/server/routes/market_bridge.py:158`
  (`_require_local_bridge_token_access`) does precisely this, and its docstring
  names the threat: *"只允许 127.0.0.1 / localhost 来源，避免被外部网页拿到 token"*
  ("only allow 127.0.0.1 / localhost origins, to stop external web pages getting
  the token"). Lifting that check to app-wide middleware on the main server
  closes the whole class in one place. Masking the `GET` response (return
  `sk-…abcd`, and let the existing `POST`-side `_is_masked_secret` logic
  round-trip it) is worthwhile defence-in-depth.

### 2. `verify_local_access` checks the peer IP — which is always `127.0.0.1`

- **File:** `main_routers/cookies_login_router.py:62`
- **Tool:** none
- **Confidence:** high
- **Why it matters:** The credential router (`/api/auth/*` — saved
  Bilibili / Douyin / Weibo / Reddit / Twitter / Kuaishou login cookies) carries
  a router-wide `Depends(verify_local_access)`. But the check is
  `request.client.host not in ["127.0.0.1", "::1", "localhost"]` — and on a
  socket **bound to `127.0.0.1`, every request that arrives already has a
  loopback peer address**, including one a browser was tricked into sending. The
  guard is honestly labelled "Defense in depth", so this is not a
  misunderstanding of the boundary so much as the same missing Host check as #1.
- **Recommendation:** Same middleware. The peer-IP check only ever mattered for a
  non-loopback bind.

### 3. The monitor server binds `0.0.0.0` with an unauthenticated write path

- **File:** `app/monitor.py:513` (bind), `:328` (`/sync/{lanlan_name}`), `:171` (`/api/config/preferences`)
- **Tool:** none
- **Confidence:** medium
- **Why it matters:** This one is deliberate — the comment says the monitor is
  "a read-only status receiver designed to be reachable by external clients", and
  it is the surface that lets a phone or a second screen show subtitles. But it
  is not read-only: the `/sync/{lanlan_name}` websocket `accept()`s any
  connection with no token and forwards whatever JSON it receives to
  `broadcast_message()` and into the subtitle state, so **anyone on the same
  LAN** — café, dorm, conference wifi — can put words in the companion's mouth on
  the user's screen. `GET /api/config/preferences` on the same port serves the
  user's learned preference list, and `page_config` the character name. For a
  companion app the privacy surface *is* the product.
- **Recommendation:** Keep the bind if the multi-device use case needs it, but
  require the existing `AUTOSTART_CSRF_TOKEN`-style shared secret on `/sync`, and
  gate the two config reads.

### 4. Telemetry and survey upload over cleartext HTTP with a shipped HMAC key

- **File:** `utils/token_tracker/reporting.py:39`,`:45`; `utils/survey_client.py:43`,`:51`
- **Tool:** gitleaks (2 of 109 hits — the only two that were not FPs)
- **Confidence:** high
- **Why it matters:** `_TELEMETRY_SERVER_URL = "http://118.31.122.91:8099"` and
  `_SURVEY_SERVER_URL = "http://118.31.122.91:8100"` — **plain HTTP to a fixed
  IP**, carrying an anonymous device ID, hardware profile, locale, timezone, app
  version, usage counters and a `settings_state` snapshot. Any network observer
  reads and can rewrite it. Both files also hardcode the HMAC signing key, each
  marked *"★ 发版前修改"* ("change before release") — and the app has shipped. To
  be fair to the design: a signing key inside an open-source client can never be
  secret, the server treats it as a spam gate rather than authentication
  (`local_server/*/security.py` adds a timestamp replay window, per-device rate
  limiting and an env override), so the key's exposure is bounded. The cleartext
  transport is the part worth fixing. Reporting is also **opt-out**
  (`NEKO_DO_NOT_TRACK`), not opt-in.
- **Recommendation:** HTTPS. Rotate the two defaults out of the client and take
  them from the environment as the servers already allow.

## Patterns observed

**The best-built parts are exactly the parts I expected to break.** I came to
this repo with a list: a plugin marketplace, Steam Workshop UGC, five avatar-format
importers, drag-and-drop file ingestion, an agent that runs code. That is a lot
of untrusted content arriving from strangers. Every one of those paths is
defended, and several are defended better than in projects with a security team.
There is **no `extractall` anywhere in the codebase** — all five archive
importers walk `infolist()` member by member and check
`target.resolve().is_relative_to(root.resolve())` before writing
(`mmd_router.py:257`, `characters_router/cards.py:736`, `jukebox_router.py:109`,
`memory/external_markdown_import.py:75`). The markdown importer goes further and
runs imported text through an `_INJECTION_PATTERNS` table — *prompt-injection*
filtering on third-party content, which almost nobody ships. The plugin market
bridge pairs remote origins through a one-time code, writes its token file
`0o600`, and validates the `Host` header. The autostart routes require a CSRF
token compared with `secrets.compare_digest` against an Origin allowlist. There
is even a `sk-CANARY-APIKEY-9182` planted in a memory-export smoke test to prove
keys *don't* leak into exports.

Which is what makes the real finding worth filing. This is not a project that
doesn't understand the threat — it is a project that **solved this exact threat
three times and left the highest-value endpoint outside the fix.** The gap is
architectural, not conceptual: each guard was written as a local decorator on the
component that needed it, so a route added elsewhere silently inherits nothing.
One piece of app-wide middleware turns three good local answers into one global
one. That is a much better bug to report than "you forgot about security," and a
much easier one to fix.

**783 findings, 1 real — and the ratio is a property of the surface, not the
risk.** This is now a well-established pattern in the series
([IBM ContextForge](ibm-mcp-context-forge.html) hit 946/0): finding count scales
with how much *stuff* a project does. N.E.K.O has 2,515 Python files, a React
frontend, GitHub Actions, four lockfiles and a bundled plugin ecosystem, so it
trips every rule in the book. The clusters:

- **109 gitleaks "generic-api-key" — 107 false.** Eighty of them are in
  `static/tutorial/icebreaker`, and they are **i18n message keys**
  (`avatar_floating_day7_wrap`) whose length and underscore density read as
  entropy. The rest are test fixtures (`sk-test-1234567890`, `AIza-test-key-12345`).
  Only the two telemetry secrets above are real, and they are by-design shared.
- **67 SQL "highs"** (`sqlalchemy-execute-raw-query` ×42, `avoid-sqlalchemy-text`
  ×15, `formatted-sql-query` ×10) — the
  [#1 recurring identifier FP](mnemosyne-oss-mnemosyne.html), and among the
  cleanest instances yet. Every data value is `?`-bound; the only interpolation is
  a `where`-clause *skeleton* chosen by a branch and constant column/join
  fragments. `survey_server/storage.py:190` even clamps `limit` on **both** ends
  with a comment explaining that SQLite reads `LIMIT -1` as unlimited — a bound
  most projects only clamp above.
- **29 `sha1`** — all content fingerprints and cache keys (memory dedup, persona
  cluster hashes, OCR frame identity). Non-cryptographic use; no interop mandate
  this time, unlike the [WeChat](evoscientist-evoscientist.html) and
  [Chromium-cookie](stickerdaniel-linkedin-mcp-server.html) cases.
- **7 `avoid-pickle`** — `plugin/core/zmq_transport.py` pickling over a ZMQ
  channel bound to `tcp://127.0.0.1:*` between the plugin host and its own child
  processes. Installed plugins already run arbitrary Python, so the codec crosses
  no trust boundary — though an ephemeral loopback TCP port is a weaker container
  than a unix socket would be.
- **91 `insecure-websocket`, 89 GHA mutable action tags, 21 `non-literal-import`**
  (the plugin loader registry), **19 `logger-credential-leak`**, 5 `run-shell-injection`
  (all in release/build workflows) — the standard tail.
- **The `insecure-file-permissions` hit on `utils/cookies_login.py:142` is
  `os.chmod(CONFIG_DIR, 0o700)`** — the
  [active-harm FP](stickerdaniel-linkedin-mcp-server.html) again. Semgrep flags
  the line that *protects* the cookie store, and following the suggestion would
  widen it.

**The `exec` is honest, so it isn't a finding.** `brain/computer_use.py:1191`
runs model-generated `pyautogui` code with full builtins and `os` in scope, and
`brain/cua/agents/worker.py:205` `eval`s a generated plan. On any other project
that is the headline. Here the product's front page says it *operates your
browser and your computer*, and — critically — **nothing in the codebase claims
the executor is sandboxed**. That is the [AG2](ag2ai-ag2.html) case: an honest
"no boundary" is product surface, not a vulnerability. It is the precise inverse
of [Agently](agentera-agently.html), where a component *named* `PythonSandbox`
promised a boundary it could not enforce. An advertised-but-unenforced boundary
is worse than a documented absence of one, and N.E.K.O documents the absence.

**Both "criticals" are unreachable.** CVE-2026-27962 in `authlib==1.6.8` appears
twice (once per lockfile) and is the only Critical in the report. `authlib` has
**zero import sites** in 2,515 Python files; it arrives transitively through
`browser-use`, which uses it for cloud-sync OAuth — a path N.E.K.O never touches,
since it drives a local browser. [Version-match, not
reachable](maziyarpanahi-openmed.html). Worth bumping because it is free, not
because it is live. The genuine dependency work is elsewhere and is ordinary
refresh: Pillow (a long DoS/heap tail, and genuinely reachable via avatar and
screen-capture image handling), pypdf, Tornado, `python-multipart`, plus a
17-high `frontend/plugin-manager/package-lock.json`.

## Notes on the tool

- **The finding that mattered was absence-shaped again.** No rule fires on "a
  loopback HTTP server with no `Host`/`Origin` validation serves secrets." Every
  ingredient was visible — a bare `FastAPI()`, a route returning `apiKey` fields,
  no `TrustedHostMiddleware` — but they live in three files and the vulnerability
  is the *gap* between them. Candidate check: flag a FastAPI/Flask app that (a)
  binds loopback, (b) registers no CORS/TrustedHost middleware, and (c) has a
  handler whose response dict contains key-shaped field names.
- **Grade the guard, don't just find it.** `verify_local_access` would satisfy
  any "is this route access-controlled?" heuristic — it is a router-wide
  `Depends`. It is also a no-op. A rule that knows `request.client.host` is
  tautological on a loopback bind would have caught #2, and would have caught the
  [codex-lb](soju06-codex-lb.html) spoofable-XFF case too. Same family: *the
  check runs, the check means nothing.*
- **Reward intra-repo consistency.** The strongest signal here was differential:
  one component validates `Host`, its siblings don't. A cross-file pass that
  finds a security predicate applied in one place and absent at comparable sinks
  would have ranked this first. This is the third scan where "the project already
  wrote the fix elsewhere" was the sharpest framing.
- **Honour i18n key files.** 80 of 109 gitleaks hits were message-catalog
  identifiers in `static/tutorial/`. Alongside the `.secrets.baseline`
  ([IBM](ibm-mcp-context-forge.html)) and `# pragma: allowlist secret`
  ([AG2](ag2ai-ag2.html)) votes, the entropy rule needs a structural
  suppression tier.
- **Tooling:** `GIT_LFS_SKIP_SMUDGE=1` was again required (385 MB of assets).
  Semgrep produced a healthy 1.8 MB report — the
  [0-byte check](dataelement-clawith.html) is now routine. pip-audit returned
  empty on a 51 KB `requirements.txt` without hanging this time; Trivy carried
  the dependency picture across all four lockfiles.

## Disclosure timeline

- 2026-07-29 — scan run
- 2026-07-29 — issue [#2558](https://github.com/Project-N-E-K-O/N.E.K.O/issues/2558) filed upstream
- 2026-07-29 — public post (this page)
- 2026-07-30 — **resolved.** [PR #2559](https://github.com/Project-N-E-K-O/N.E.K.O/pull/2559)
  merged (+2043 / −101 across 22 files), closing #2558 roughly **14 hours** after
  it was filed.

## Resolution

The maintainer ([@MingTianSang](https://github.com/MingTianSang)) fixed both
halves and took the structural option on each.

**The masking gap.** All 32 sensitive fields returned by
`GET /api/config/core_api` are now replaced with a fixed sentinel rather than
plaintext. The interesting part is what that forced: because the front end can no
longer read the real key, the PR also had to make the *write* path
sentinel-aware — a masked value posted back must mean "keep what's stored", an
explicit empty must mean "clear it", and a provider switch must not cross-wire
one provider's key into another. The connectivity-test button now detects a
masked key and asks for re-entry instead of shipping the sentinel to a provider
as if it were a credential. That is the whole reason a redaction change touched
244 lines of `core_config.py` and 175 of `api_key_settings.js`: masking a
read-back field is only safe once round-tripping is safe.

**The missing boundary.** Rather than bolting a `Host` check onto the one leaking
route, the PR adds `utils/host_origin_guard.py` (360 new lines) and registers it
as middleware on **all four** servers — `main_server/__init__.py`,
`memory_server/runtime.py`, `agent_server/api_shared.py`, and
`plugin/server/http_app.py` — with WebSocket `Origin` rejection alongside the
`Host` allowlist. Untrusted `Host` now returns `400`. Custom domains and mDNS
names are opted in through `NEKO_TRUSTED_HOSTS` / `NEKO_TRUSTED_ORIGINS`
(documented in `docs/config/environment-vars.md`), and `docker/entrypoint.sh`
auto-allows the existing `SSL_DOMAIN` so reverse-proxy deployments don't break.
Loopback and bare IPs are unaffected.

This is the outcome the [intra-repo differential](#notes-on-the-tool) framing was
arguing for. The report's recommendation was not "add a check here" —
it was "you already wrote this guard three times in this repo, promote it to
app-wide middleware." That is precisely what shipped, and it now also covers the
WebSocket `Origin` surface, which the report had only raised as a secondary item.

Three new test files came with it — `tests/unit/test_host_origin_guard.py` (311
lines), `tests/unit/test_core_config_secret_redaction.py` (513 lines), and
`tests/frontend/api_key_secret_masking.test.cjs` (286 lines) — and the PR
reports a **main-branch control run**: on `main`, the config endpoint still
returned plaintext, a forged `Host` still returned `200`, and a hostile
WebSocket `Origin` still connected. An independent confirmation that the issue
reproduced as described, which is a more useful artifact than any severity label.

## Reproduce

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/Project-N-E-K-O/N.E.K.O /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/project-n-e-k-o-n-e-k-o --min-severity medium
```
