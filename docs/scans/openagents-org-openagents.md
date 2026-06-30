---
layout: default
title: "openagents-org/openagents: security scan"
date: 2026-06-30
---

# openagents-org/openagents - security scan

**Repository:** [openagents-org/openagents](https://github.com/openagents-org/openagents)
**Commit scanned:** `bf32ccbda43b1535ef650df42ee908d8a9961d75`
**Scan date:** 2026-06-30
**Disclosure status:** public — post-only (no real, high-confidence first-party item cleared the bar; no upstream issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 8 |
| High | 251 |
| Medium | 421 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 680 — and the count is the story: it almost entirely describes the JavaScript/TypeScript frontends, not the Python agent-network core.

OpenAgents is an "AI Agent Networks" platform — a Python SDK + relay/transport
layer for connecting agents across machines into shared workspaces, plus an
Electron launcher, a web studio, and a Go web component. It's a real monorepo:
`sdk/` (Python core), `packages/agent-connector` + `packages/launcher` (Node/TS),
`workspace/frontend` + `sdk/studio` + `packages/go/web` (web frontends).

At 680 findings this looks like the heaviest scan in the series. It isn't —
it's the **harbor pattern again**: once you split first-party Python from the
bundled frontends, the scary numbers all live in `node_modules`-shaped lockfiles
and JS lint, and the Python agent core is modest and largely by-design.

## Top findings

### 1. All 8 criticals are npm frontend lockfiles

- **Files:** `sdk/studio/package-lock.json` (+ duplicate `yarn.lock`), `workspace/frontend/package-lock.json`, `packages/go/web/package-lock.json`
- **Tool:** trivy
- **Confidence:** real CVEs, frontend-scoped
- **Why it matters / why it doesn't:** The criticals are `protobufjs` (prototype-pollution → code execution), `shell-quote` (command injection), and `form-data` (unsafe random) — all classic transitive npm advisories in the web frontends. They're real, but they're frontend/build-dependency drift, not the Python relay. The Python lockfile carries **zero** trivy criticals; all 360 trivy findings are npm (`sdk/studio` alone is 154).
- **Recommendation:** Refresh the frontend lockfiles. Dependabot is already
  opening PRs on the repo, but `sdk/studio` (154 advisories) is clearly outpacing
  it — worth confirming every frontend package is in the Dependabot config.

### 2. The Python agent-network core is modest and mostly by-design

- **Files:** `sdk/src/openagents/...`
- **Tool:** semgrep
- **Confidence:** by-design / FP after review
- **Why it matters:** This is the part that actually matters for an agent
  network, and it holds up:
  - `subprocess(..., shell=True)` in `client/cli_helpers.py:1152` launches the
    **local** `npm`/`npx` studio dev server — internal path, not network input.
  - `non-literal-import` across `utils/mod_loaders.py` / `registry/loader.py` is
    the **plugin/mod loader**, importing mods by local directory name — the
    documented extension mechanism, trust-rooted in the local filesystem.
  - `eval-detected` is in `sdk/examples/agents/langchain_agent_example.py` —
    example code.
  - Four `python37-compatibility` "high" hits are pure lint on a modern-Python
    project.

### 3. The cleartext-WebSocket finding is mostly already mitigated

- **Files:** `sdk/src/openagents/sdk/transports/websocket.py:77`, `connectors/websocket_connector.py:74` (`ws://`)
- **Tool:** semgrep (`detect-insecure-websocket`)
- **Confidence:** partial hardening, not a cleartext-by-default flaw
- **Why it matters:** For a platform that connects agents *across machines*,
  unencrypted transport would be a real concern — agent traffic (and any token in
  the handshake) sniffable on the wire.
- **Why it's not a finding:** The production transport already does this right.
  `transports/http.py` sets `DEFAULT_RELAY_URL = "wss://relay.openagents.org"`
  and derives the socket scheme from the URL
  (`ws_url.replace("https://", "wss://")`), so the default relay path is TLS. The
  hardcoded `ws://` lives only in a secondary **direct-peer** transport, the kind
  used for localhost / trusted-LAN peer links. The residual hardening — let that
  direct-peer transport also negotiate `wss://` — is worth doing, but it's not
  "everything is cleartext."

### 4. Secret hits: Firebase web keys (public by design) + a test-workspace token

- **Tool:** gitleaks (17 hits)
- **Confidence:** FP / low
- **Why it matters / why it doesn't:** `workspace/frontend/lib/firebase.ts:12`
  and `packages/go/web/lib/firebase.ts:12` are **Firebase web `apiKey`s** —
  public client identifiers by design (Firebase access is gated by security
  rules and authorized domains, not key secrecy), the single most common
  gitleaks false positive. The rest are test fixtures
  (`packages/agent-connector/test/*`), SDK templates (`network.yaml`
  placeholders), and docs. The one genuine credential is a `WS_TOKEN` hardcoded
  in `.github/workflows/test-e2e.yml:10` — but it's a throwaway **e2e
  test-workspace** token (`workflow_dispatch`, self-hosted runner), not a
  production secret. Rotating it into a GH secret is tidy hygiene, not a
  disclosure.

## Patterns observed

**The monorepo ownership split decides everything here.** This is the third
scan in the series (after harbor and Kiln) where the headline count is an
artifact of bundled frontends. 680 findings: the 8 criticals are npm, ~360
trivy rows are npm across five web/Node lockfiles, and the ~300 semgrep hits are
overwhelmingly `js-*` rules in `packages/agent-connector` (43 ERRORs alone),
`packages/launcher`, and the web frontends. The first-party Python agent
network — the thing a security review of "OpenAgents" should actually care
about — contributes a couple dozen findings, and they curate to by-design
(local subprocess, local mod loading) or FP (compat lint, logger-disclosure).

**The transport story is the reachability lesson in miniature.** A flat reading
says "insecure WebSocket — agents talk in cleartext." The code says the default
relay is `wss://` and the HTTP transport upgrades `https→wss`; only a
secondary direct-peer path hardcodes `ws://`. Same rule hit, very different
conclusion once you read which transport is the default and which is the
fallback. The maintainers already reached for TLS where it counts.

**Firebase keys are not secrets.** Two of the 17 gitleaks hits are Firebase web
config, which is meant to ship in the client bundle. Treating them as leaked
credentials would be the kind of false alarm that erodes trust in a report. The
genuine items reduce to one test-workspace token, which is test-scope.

This is not strict-norm (no SECURITY.md, no commercial backing), so a real
first-party finding would have earned a focused courtesy issue. There wasn't
one: the criticals are frontend dependency drift on a repo that already runs
Dependabot, and the Python core's scariest-looking finding is already mitigated
in its default path. Post-only is the honest call.

## Notes on the tool

- **Per-component ownership split should be first-class.** AI PatchLab reported
  680 findings as one flat list; the single most useful transformation here is
  "first-party Python core vs bundled frontends (own lockfile = sub-project)."
  This is the same backlog item harbor raised — a monorepo mode that groups by
  sub-project before severity would have led with "Python core: ~4 candidates"
  instead of "8 criticals."
- **`detect-insecure-websocket` needs default-vs-fallback context.** The rule
  fired on a `ws://` in a secondary transport while the default relay is
  `wss://`. Flagging the literal without noting whether it's the default path
  overstates it — same shape as the `run-shell-injection` trigger-context gap
  from the openmed scan.
- **Firebase `apiKey` is a known-public pattern.** gitleaks' `generic-api-key`
  fires on `firebaseConfig.apiKey`; an allowlist for the Firebase web-config
  shape (apiKey + authDomain + projectId together) would kill a recurring FP.
- **`python37-compatibility` keeps surfacing as "high."** Compatibility lint on
  a modern-Python project should not be a high-severity security finding —
  noted on openmed too.

## Disclosure timeline

- 2026-06-30 — scan run
- 2026-06-30 — public post (this page); post-only, no upstream issue filed

This is a post-only write-up. After the ownership split, no real, reachable,
undefended first-party item cleared the quality gate: the criticals are
frontend npm drift (Dependabot is active), the Python core is by-design or FP,
the WebSocket finding is mitigated in its default path, and the secret hits are
public Firebase keys plus one test-scope token.

## Reproduce

```bash
git clone https://github.com/openagents-org/openagents /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/openagents-org-openagents \
  --min-severity medium --ignore-samples
```
