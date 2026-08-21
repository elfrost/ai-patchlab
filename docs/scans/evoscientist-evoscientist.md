---
layout: default
title: "EvoScientist/EvoScientist: security scan"
description: "Security scan of EvoScientist/EvoScientist: 39 findings, 1 real — and no tool ranked it. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-07-28
---

# EvoScientist/EvoScientist — security scan

**Repository:** [EvoScientist/EvoScientist](https://github.com/EvoScientist/EvoScientist)
**Commit scanned:** `10c032450e0e`
**Scan date:** 2026-07-28
**Disclosure status:** disclosed — **resolved upstream** (PR [#401](https://github.com/EvoScientist/EvoScientist/pull/401) merged 2026-08-14)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 16 |
| Medium | 23 |
| Low | 0 |
| Info | 0 |

**Total findings:** 39 (1 real after curation — and no tool ranked it)

EvoScientist (4.4k★, Apache-2.0) is a self-evolving AI scientist: a
multi-agent research system built on
[deepagents](https://github.com/langchain-ai/deepagents) that plans experiments,
searches literature, writes and debugs code, analyses data, and drafts papers.
It is explicitly *human-on-the-loop* rather than human-in-the-loop, and it
reaches the user through ten chat channels (Feishu, WeChat/WeCom, Slack,
Discord, Telegram, DingTalk, QQ, Signal, email, iMessage).

39 findings on a 4.9 MB Python codebase is an unusually *low* count, and the
dependency picture is the cleanest this series has seen: Trivy reports **zero**
vulnerabilities on `uv.lock`, pip-audit **0 across 148 packages**, Dependabot is
wired, and the Dockerfile is multi-stage and drops to a non-root `USER evosci`.
Every one of the 39 scanner findings is a false positive. The one real finding
was found by hand, in the gap between two files.

## Top findings

### 1. Inbound chat webhooks skip signature verification on an attacker-chosen branch — *scanner-silent*

- **File:** `EvoScientist/channels/wechat/channel.py:342`, `EvoScientist/channels/feishu/channel.py:850`
- **Tool:** none — no scanner flagged this
- **Confidence:** high
- **Why it matters:** For an inbound webhook the signature check *is* the
  authentication — the port must be reachable by Tencent/Feishu for the product
  to work at all, so nothing else stands between the internet and the agent. In
  `WeChatChannel._handle_message` the check sits behind
  `if encrypt and self._crypto:`, where `encrypt` is read from the request body
  the caller sent. A POST of plaintext XML with no `<Encrypt>` element takes the
  false branch and falls straight through to `_process_message` — **even when the
  operator has correctly configured `token` and `encoding_aes_key`**. Feishu's
  `_handle_event` has the sibling shape: token verification is wrapped in
  `if self.config.verification_token:` (fail-open when unset — and the onboarding
  wizard prompts for it as *"optional"* while defaulting the subscription mode to
  `webhook`), and its AES layer is likewise gated on `"encrypt" in body`. Both
  servers bind `0.0.0.0` (`channels/mixins.py:120`, `wechat/channel.py:181`) on
  ports 9001/9000. Because `FromUserName` is then taken from the forged payload,
  the `allowed_senders` allowlist is spoofable — and it is open by default
  anyway (`AllowListMiddleware._is_sender_allowed` returns `True` on an empty
  set). The injected text drives an agent holding a shell `execute` tool whose
  approval prompt is *a reply in the same chat* (`y`/`1`/`approve`; `3`/`auto`
  approves all future actions) — a reply the same forged channel can send.
- **Recommendation:** Verify before branching, not inside the branch. Compute the
  signature over the raw request for every inbound POST and reject on mismatch;
  treat "no `Encrypt` field" and "no token configured" as failures rather than as
  skips. If backwards compatibility matters, refusing to start a webhook-mode
  channel without credentials is safer than silently accepting unsigned traffic.

Filed upstream as
[#392](https://github.com/EvoScientist/EvoScientist/issues/392). The
*approval* half of this chain — sub-agent shell execution never being gated — is
already tracked by the maintainers in
[#387](https://github.com/EvoScientist/EvoScientist/issues/387); this report is
only the ingress half.

### 2. What the 39 scanner findings actually were

- **10 SQL highs in `sessions.py`** — the [#1 parameterized-identifier
  FP](mnemosyne-oss-mnemosyne.html), and an exemplary instance. Every
  `conn.execute(query, params)` binds its data with `?`; the only interpolation
  is a module-level constant (`MAIN_THREAD_FILTER_SQL`) and
  `PRAGMA user_version = {int(version)}`, which carries the comment *"PRAGMAs
  cannot be parameter-bound; the integer is interpolated safely because we
  control the value."*
- **3 `shell=True`** — this is the agent's own `execute` tool
  (`backends.py`, `background.py`). Running code is the product
  ([ag2](ag2ai-ag2.html) class), and the third is a wizard-confirmed
  `curl`/`wget` installer.
- **4 SHA-1** — WeChat's mandated signature scheme (sorted
  `token|timestamp|nonce|encrypt`, SHA-1), implemented to spec. Flagging it would
  be an [active-harm FP](stickerdaniel-linkedin-mcp-server.html): "fix" it and
  the channel stops interoperating.
- **3 gitleaks** — a documentation example of a Discord *user ID*, and two
  fixtures inside `test_serde_default_rich_exception.py`, the project's own test
  that secrets get **redacted** from serialised exceptions. The scanner flagged
  the defense.
- **1 insecure-websocket** — `_infer_transport()` matching the literal string
  `"ws://"` to pick a transport. It parses a scheme; it doesn't open a socket.
- The remainder: 7 GitHub Actions mutable tags, 5 non-literal-import (the plugin
  and channel loader registry), 5 logger-credential-leak (a deliberately
  truncated `token[:8]…token[-4:]` debug fingerprint), 1 dynamic-urllib (a
  constant `PYPI_URL` with `timeout=3`).

## Patterns observed

The interesting thing about scanning a *self-evolving* agent is that the obvious
question turns out to be the wrong one. I expected the finding to live in the
evolution loop — an agent that writes its own skills and installs them is a
prompt-injection-to-persistence story waiting to happen. It doesn't, because
that loop is the most carefully built part of the codebase: autoskills go
through a proposal → review → approval lifecycle, skill names are validated
against a strict regex, and skill frontmatter is checked against a key
allowlist. The code interpreter is a QuickJS sandbox, not in-process Python
`exec`, and its tool allowlist explicitly *excludes* shell `execute` with the
reason written down in the module docstring: *"would bypass
`HumanInTheLoopMiddleware` approval."* That is an advertised boundary that is
actually enforced — the opposite of the [Agently](agentera-agently.html) case,
where a component named `PythonSandbox` wasn't one.

So the real finding was in the plumbing beside it, which is becoming the
pattern: [docetl](ucbepic-docetl.html) built a code-operator engine and left an
unauthenticated `/fs` router next to it; here the sandboxing, the approval
middleware, and the skill-proposal lifecycle are all thought through, and the
front door is a webhook handler that verifies signatures only if the caller
includes the field that triggers verification. Defenses fail at their seams. The
tell in both cases is the same: the correct pattern exists *in the same file* —
WeChat's `_handle_verify` (the GET handshake) checks the signature properly, and
`verify_signature` itself is a faithful implementation of the WeChat spec. The
knowledge is there; one branch just doesn't reach it.

A note on `0.0.0.0`, because this series keeps meeting it and the reading is not
constant. On [dimos](dimensionalos-dimos.html) the scattered `0.0.0.0` literals
were fine — the listeners that mattered defaulted to `127.0.0.1`, and the ones
binding wide were teleop surfaces that need LAN reach. Here the inverse holds: a
webhook receiver *must* be reachable by Tencent's servers, so "it's only exposed
if you deploy it" isn't a mitigation, it's the deployment. When a listener's
whole purpose is to accept unsolicited POSTs from the public internet, the
signature check is the entire security boundary, and a conditional around it is
a conditional around authentication.

Worth crediting separately: the honesty of the `--tunnel` flag on
`EvoSci deploy`, whose own `--help` text reads *"no auth — anyone with the URL
can drive the agent; trusted use only."* Saying that plainly is worth more than
a sandbox that overpromises.

## Notes on the tool

- **Absence-shaped findings remain invisible.** No rule fires on *"verification
  happens inside a branch the attacker selects."* Semgrep saw the SHA-1
  **inside** `verify_signature` and flagged it as weak crypto — the one place
  where the code was doing the right thing — while missing that the function
  goes uncalled on the plaintext path 200 lines away. Same lesson as the
  [zotero-mcp sweep](54yyyu-zotero-mcp.html): pair scanner output with a
  surface-specific hand sweep. Backlog: for any inbound-webhook handler, check
  that signature verification is unconditional.
- **Credit-the-defense, inverted, twice in one scan.** Gitleaks flagged the
  secret-*redaction* test; Semgrep flagged the protocol-mandated SHA-1. Both
  point at code that exists to improve security. This is a third confirmed
  instance of the mandated-interop SHA-1 class (after Chromium cookie KDF and
  RFC 6455 WebSocket) — enough to generalise the backlog rule.
- **A genuinely clean dependency graph is possible.** Trivy 0 on `uv.lock`,
  pip-audit 0/148. Worth recording as a datapoint, since this series more often
  reports lockfile drift.
- pip-audit completed normally here (148 packages, no hang), unlike the
  [dimos](dimensionalos-dimos.html) run.

## Disclosure timeline

- 2026-07-28 — scan run
- 2026-07-28 — issue [#392](https://github.com/EvoScientist/EvoScientist/issues/392) filed upstream
- 2026-07-28 — public post (this page)
- 2026-08-03 — PR [#401](https://github.com/EvoScientist/EvoScientist/pull/401) opened by a third-party
  contributor ([@NkAntony777](https://github.com/NkAntony777)), fixing the conditional-verification
  bypass on both channels and leaving the policy half explicitly to the maintainers
- 2026-08-14 — PR #401 **merged** by maintainer [@X-iZhang](https://github.com/X-iZhang); issue #392
  closed as completed (**resolved**, 17 days)

### What shipped

Both channels now verify-then-branch instead of branch-then-verify — the shape the report
asked for:

- **WeChat** `_handle_message`: the condition inverted from `if encrypt and self._crypto:` to
  `if self._crypto:` with an inner `if not encrypt: return 403`. The caller's body can no longer
  decide whether the signature is checked; when `encoding_aes_key` + `token` are configured, a
  POST with no `<Encrypt>` element is rejected before `_safe_process_message` is reached.
- **Feishu** `_handle_event`: same inversion on `encrypt_key`, plus an `isinstance(body, dict)`
  guard so a non-dict JSON body (list, string, int) is rejected rather than reaching `.get`.
- Both rejections log a warning naming the bypass, so a deployment being probed leaves a trace.
- 9 regression tests across `tests/test_feishu_channel.py` and `tests/test_wechat_channel.py`,
  including the no-regression case that plaintext mode still works when no key is configured.
  The contributor reported reproducing the bypass against `main` on both channels **before**
  writing the fix, and a full-suite run (3045 passed / 13 skipped).

**What was deliberately not fixed, and correctly so:** the policy half — whether a channel with
credentials *entirely unset* should fail closed at startup or keep accepting unsigned traffic with
a loud warning. That is a behaviour change for existing plaintext deployments, and the contributor
declined to make it unilaterally. Splitting the ask that way is what let the uncontroversial half
land; it is the same dynamic as the [semantic-router](aurelio-labs-semantic-router.html)
filing, where a separable ask let the useful half ship without the contested half blocking it —
except here the maintainer closed the issue as completed, so the residual is a decision on record
rather than an open thread.

**Third-party authorship is the notable part.** The fix was not written by me and not written by
a maintainer — a passer-by read a public issue, reproduced it, and patched it. That is the second
time in this series a filing concrete enough to be *adopted* outlived my own attention on it.

## Reproduce

```bash
git clone https://github.com/EvoScientist/EvoScientist /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/evoscientist-evoscientist --min-severity medium
```
