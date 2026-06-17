---
layout: default
title: "omnigent-ai/omnigent: security scan"
date: 2026-06-17
---

# omnigent-ai/omnigent — security scan

**Repository:** [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) — 3.2k★, Apache-2.0, "a meta-harness for all your AI agents" — a Python orchestration layer (~24 MB) that runs Claude/Codex native harnesses, brokers credentials to sandboxed sessions, exposes a server with a bundle-upload API, and ships a React web UI (`ap-web/`).
**Commit scanned:** `82d831a1b19c` (HEAD of `main` at scan time)
**Scan date:** 2026-06-17
**Disclosure status:** 🔒 **Private disclosure (maintainer email) + this methodology post.** omnigent ships a real `SECURITY.md` (strict-norm) directing reports to a private GitHub Security Advisory — but that channel currently 404s for external reporters because *Private Vulnerability Reporting* isn't enabled on the repo, so the report went privately by email to maintainers instead (with a heads-up to enable PVR). The headline finding is a **HIGH**, server-side, multi-tenant-reachable sandbox-escape / operator-credential-theft chain — so it was reported privately, and **this public post deliberately contains no weaponized reproduction** (no exploit payload, no IPC port discovery recipe, no elicitation string). It describes the *method* and the finding *classes* only.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 76 (scanner) → see curated below |
| Medium | 70 (scanner) → see curated below |
| Low | 0 |
| Info | 0 (filtered) |

**146 scanner findings → 0 scanner clusters survived adversarial verification as standalone vulnerabilities → 6 confirmed-real items surfaced by a completeness sweep, one of them HIGH.** This is the inverse-shaped scan of [harbor](harbor-framework-harbor.html): there the raw count *over*-stated risk (vendored code); here the raw clusters were all by-design or FP, and the real risk was *invisible* to the scanner because it lives in cross-process trust boundaries and absence-of-control — exactly the [zotero-mcp completeness-sweep lesson](54yyyu-zotero-mcp.html) at a higher severity. The scan was run under the project's ultracode mode: a 27-agent workflow (adversarially verify 8 scanner clusters → sweep 6 meta-harness surfaces → adversarially verify each candidate → synthesize).

## The method (because the method is the public artifact)

Eight scanner clusters went through one adversarial verifier each, tasked with *refuting* a preliminary verdict:

- **All 3 `subprocess(shell=True)` hits → by-design** in isolation (a credential-proxy resolver, the agent's Bash tool, a status-chain helper — the [recurring agent-execution-by-design class](vrsen-agency-swarm.html)).
- **19 `insecure-websocket` → FP** (loopback IPC, the [ha-mcp local-trust pattern](homeassistant-ai-ha-mcp.html)).
- **29 `gitleaks` → FP** (all under `tests/`, fixtures).
- **11 `logger-credential-disclosure` → FP** (11/11 — the parent-side proxy is inside the redaction net; the [logger-leak FP playbook](evalstate-fast-agent.html) held cleanly again).
- **3 `text(f"…")` SQL → gated** (`_FTS_TABLE` is a module constant, bound params).
- **The GH Actions line + the JS path-join → FP** (trusted value; fixed internal component).

**Zero scanner clusters survived as standalone vulnerabilities.** Then six meta-harness surfaces (credential-proxy architecture, native-app-server IPC auth, tool-execution sandbox, web-UI XSS, deserialization, secrets/logging) were swept and each candidate adversarially re-verified. That second pass is where the real findings were — and where the most important escalation happened.

## The headline: reachability flips severity, not the sink

The single most important finding began life as a **Phase-A "by-design" verdict** — a `credential_proxy` resolver that runs `subprocess.run(..., shell=True)` in the unsandboxed parent process. Under the operator-trust model (the operator configures their own credential commands in `~/.omnigent/config.yaml`), that is genuinely fine, and the first reviewer correctly called it by-design.

The Phase-C adversarial re-verification asked the question the first reviewer couldn't from the sink alone: *where else can that `command:` come from?* Tracing the ingestion path three modules deep — `POST /v1/sessions` bundle upload → `validate_agent_bundle` → spec parser → the resolver — showed the bundle validator **never strips a tenant-supplied `credential_proxy` `command:` entry**. So on a multi-tenant or managed-host deployment, an authenticated tenant's uploaded bundle can land a shell command in the operator-trusted parent that holds the LLM/git/cloud credentials. **Sandbox escape + operator-credential theft — HIGH.** Same sink, same line of code the scanner saw and (correctly) didn't flag; the severity is entirely a property of the *reachability*, which is invisible to an AST rule.

This is the [SCA-vs-reachability lesson](q00-ouroboros.html) inverted: there, reachability analysis *lowered* a version-match's applicability; here it *raised* a by-design sink to a HIGH. Reachability is the dimension, in both directions. The finding, its exact path, and the fix were reported privately via the SECURITY.md channel; the fix is an ingestion-time trust check (a tenant-supplied spec must not be able to declare a `command:`/`file:` credential source).

## The other confirmed-real items (classes, not payloads)

Reported privately alongside the HIGH (same review), described here at the class level:

- **Unauthenticated loopback IPC (Medium, local-only).** A native app-server WebSocket is an unauthenticated loopback TCP listener — any co-resident local process can connect and drive the agent. Loopback bind is not an access-control boundary (the port is locally discoverable). Fix: a shared secret on the `initialize` handshake — which restores the peer-authentication the *previous* unix-socket + `0o700` design had. Which is its own lesson:
- **A transport migration silently dropped a trust boundary (Low, defense-in-depth).** The `unix://` → `ws://` migration traded a `0o700`/UID-confined filesystem socket for an unauthenticated loopback port. The functionality moved; the access-control property didn't come with it. Migrations are where security properties quietly fall on the floor.
- **A policy hook that fails OPEN (Medium).** omnigent's *in-process* policy engine fails **closed** (deny on error) — correct. But the *native-harness* runtime hook — the actual PreToolUse gate for native sessions — returns "allow" on an HTTP error / empty body / JSON-decode failure. If the policy server drops mid-session, the primary tool-call gate silently disappears. The asymmetry between the two enforcement paths is the finding: one fails closed, its sibling fails open.
- **DOM XSS via an MCP-elicitation URL (Medium).** A `url`-mode elicitation value from a (semi-trusted) MCP server is rendered as an `<a href>` in the web UI with a path-prefix check but no scheme allowlist — a `javascript:` URL executes on click. The Electron build is mitigated by a window-open handler; the plain-browser web UI is not, and there's no CSP backstop. The exact semi-trusted-MCP-party a meta-harness is built to interoperate with is the threat actor.

## Patterns observed

**Reachability flips severity, not the sink — and it flips both ways.** The credential-proxy line is the cleanest example in the series: a single line of code, correctly judged by-design from the sink, becomes a HIGH multi-tenant escape once you trace which callers can reach it with attacker-controlled input. A curated report that stopped at the sink (as the scanner and the first reviewer did) would have shipped "by-design, no action." The adversarial second pass that asks "*who else reaches this, with what input?*" is the entire value-add over a scanner.

**Scanners see syntax; meta-harness risk lives in absence-of-control and cross-process trust boundaries.** Four of the six real items are things that *aren't there*: a missing ingestion-time strip, a missing IPC auth, a missing scheme allowlist, a missing fail-closed branch. AST rules fire on tokens that *are* present; none of these are a token. This is why an agent meta-harness — which is almost entirely about brokering trust between an operator, sandboxed sessions, native harnesses, and external MCP servers — needs a trust-boundary sweep, not just a rule scan. (Five surfaces here, modeled on the [zotero-mcp 6-surface sweep](54yyyu-zotero-mcp.html).)

**Good engineering raises the bar for the reviewer, not the floor for the bug.** omnigent's OS sandbox is default-on and fail-loud; the in-process policy engine fails closed; the egress check is provable; the credential redaction net genuinely covers the logging surface (11/11 logger-credential hits were FP). None of that is a finding — it's what made the *real* findings subtle. The bugs that survive a well-built system are the asymmetries (one path fails closed, its sibling fails open) and the ingestion gaps (the trusted config path is locked down; the upload path that reaches the same sink isn't). Well-built code doesn't mean fewer findings; it means the findings require tracing, not grepping.

**A `SECURITY.md` changes the output, not the work.** Strict-norm means the HIGH goes out as a private GitHub Security Advisory and the public artifact is *methodology* — the workflow, the finding classes, the lessons — with no weaponized reproduction. The scan work is identical; the disclosure surface is what the policy governs.

## Notes on the tool

- **The 2026-06-11 UTF-8 fix held on a third large target**: `semgrep.json` came back at 376 KB (healthy, 0 scanner meta-errors) on this 24 MB codebase. Verified before trusting the curated baseline, per the [Clawith byte-size lesson](dataelement-clawith.html).
- **The ownership-split ([harbor lesson](harbor-framework-harbor.html)) was checked and came back trivial**: omnigent is a single first-party project, no vendored sub-trees — so all 146 findings are first-party, and the curation effort went entirely into reachability rather than attribution. The two lessons compose: *first* split ownership (was there vendored code? no), *then* trace reachability (the real work here).
- This scan is the strongest case yet for an **ingestion-trust dataflow** capability — "which request handlers can reach this sink with caller-controlled input?" — which is precisely the dimension that separated the HIGH from a by-design line. That is a taint-tracking feature, beyond AST rules; until it exists, the adversarial-completeness workflow is the substitute.

## Disclosure timeline

- **2026-06-17** — Scan run at commit `82d831a1b19c`; `semgrep.json` verified healthy. 27-agent adversarial-verification + completeness-sweep workflow. 0/8 scanner clusters survived as standalone vulns; 6 confirmed-real items surfaced by the sweep, one HIGH (credential-proxy reachable via untrusted bundle upload), found by a Phase-C escalation of a Phase-A by-design verdict.
- **2026-06-17** — HIGH (+ the same-ingestion-path low, + heads-up on the three mediums) reported privately. The `SECURITY.md` GHSA channel was unavailable (Private Vulnerability Reporting not enabled on the repo → the advisory form 404s for external reporters), so the report went by private email to maintainers, with a note to enable PVR so the documented channel works. No public issue filed. This methodology post published with no weaponized reproduction; happy to hold or revise at the maintainer's request.

## Reproduce (the scan, not the exploit)

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/omnigent-ai/omnigent" \
  --reports-dir reports/omnigent-ai-omnigent \
  --min-severity medium \
  --ignore-samples
```

The scanner reproduces the 146-finding raw baseline. The six confirmed-real items came from the adversarial-verification + meta-harness-completeness-sweep workflow described above, not from the scanner CLI — and the HIGH's exploit chain is intentionally not reproduced here. External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
