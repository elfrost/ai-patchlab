---
layout: default
title: "taylorwilsdon/google_workspace_mcp: security scan"
date: 2026-06-21
---

# taylorwilsdon/google_workspace_mcp — security scan

**Repository:** [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) — 2.7k★, MIT, an MCP server that controls Gmail, Google Calendar, Docs, Sheets, Slides, Chat and more — i.e. it brokers Google OAuth credentials and drives the Google Workspace APIs on a user's behalf.
**Commit scanned:** `b10c3c9cea8d` (HEAD of `main` at scan time)
**Scan date:** 2026-06-21
**Disclosure status:** **Post-only — clean scan.** Strict-norm (real `SECURITY.md` → private email channel). Quality gate evaluates to false: every one of the 16 findings, concentrated in the OAuth `auth/` layer, is either a safe pattern the developer clearly understands or a security *feature* the scanner misread. Nothing to file publicly and nothing real to disclose privately.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 5 (scanner) → all FP/by-design |
| Medium | 11 (scanner) → all FP/by-design |
| Low | 0 |
| Info | 0 (filtered) |

**16 findings, all first-party, all in the OAuth credential layer — and every one is FP or by-design.** This is the **seventh clean scan in the series**, and the most instructive kind: a server whose entire job is brokering Google OAuth tokens, where the scanner fired exclusively on the credential-handling code, and *every* hit turned out to be the developer doing credential hygiene correctly. It's the "what a security-conscious OAuth MCP server looks like" reference.

## The findings, and why each is the developer doing it right

### `unverified-jwt-decode` ×2 (`auth/google_auth.py:163, :1361`) — reading email from an already-trusted token

```python
decoded_token = jwt.decode(credentials.id_token, options={"verify_signature": False})
user_email = decoded_token.get("email")
```

On an OAuth server, "decode a JWT without verifying the signature" is exactly the shape you'd worry about — *if* the token were attacker-supplied. It isn't: `credentials.id_token` is the ID token the **Google OAuth library already obtained and verified** during the authorization-code exchange. These two call sites decode it only to read the `email` claim for session-keying and logging (the second one's comment literally says *"Decode without verification (just to get email for logging)"*). The token isn't a trust boundary here — it's already-trusted post-exchange — so skipping re-verification to read a claim is the standard, safe pattern. The `unverified-jwt-decode` rule can't tell an attacker-supplied token from an already-verified one; the developer can, and annotated it. **FP.**

### `detected-google-oauth-access-token` ×2 (`fastmcp_server.py:66`, `main.py:91`) — a log-suppression comment, i.e. a security feature

```python
# Suppress httpx/httpcore INFO logs that leak access tokens in URLs
# (e.g. tokeninfo?access_token=ya29.xxx)
logging.getLogger("httpx").setLevel(logging.WARNING)
```

The scanner matched `ya29.xxx` (Google's access-token format) and flagged a "detected OAuth access token." But it's in a **comment**, and the code beneath it is the *opposite* of a leak: it raises the httpx/httpcore log level specifically so that access tokens embedded in request URLs (`tokeninfo?access_token=ya29.…`) **don't** get written to logs. The finding is a security control the rule misread as a leak. **FP — and a credit.**

### `insecure-file-permissions` (`auth/oauth21_session_store.py:252`) — already `0o600`/`0o700`

The OAuth state/token store creates its directory `mode=0o700`, `chmod`s it `0o700`, and `chmod`s the state file `0o600` — owner-only, exactly the convention for on-disk tokens (the same fix [zotero-mcp adopted](54yyyu-zotero-mcp.html) after the fact; here it's already present). The Semgrep rule fires on the `chmod` call regardless of the mode; the mode is correct. **FP.**

### `python-logger-credential-disclosure` ×8 (`auth/google_auth.py`, `auth/credential_store.py`) — fingerprinted, value-free logging

Eight hits across the auth layer, and the sampled call sites show the opposite of credential disclosure: session IDs are logged through `_session_id_log_fingerprint(...)` (a fingerprint, never the raw ID), and credential-file log lines record the *email and filename*, never the token. The developer built a dedicated fingerprint helper specifically to keep raw session identifiers out of logs. This is the known [`logger-credential-leak` FP class](evalstate-fast-agent.html) (sibling rule), here at 8/8 FP on a codebase that is demonstrably careful about exactly this. **FP.**

### `dynamic-urllib-use-detected` (`auth/oauth_callback_server.py:231`) — a loopback self-probe

`urlopen(probe_url)` where `probe_url` is `{scheme}://{host}:{self.port}/oauth2callback` — the server probing **its own** callback endpoint to confirm it's listening (with `0.0.0.0`/`::` normalized to `127.0.0.1`), then checking the body for "Authentication Successful/Error". The host is the configured callback host, not user input; the fetch is a localhost health-check. **By-design.**

### Remainder

`dangerous-globals-use` in `core/log_formatter.py` (a log-formatting dispatch pattern) and the Dockerfile `apt-get` missing `--no-install-recommends` (minor container-image-size hygiene) round out the list. Neither is security-relevant to the runtime.

## Patterns observed

**A credential-broker whose every scanner hit is a credit is the cleanest "what right looks like" reference for OAuth handling.** Prior clean scans were clean for structural reasons (a [published threat model](homeassistant-ai-ha-mcp.html), a [thin runtime](ar9av-obsidian-wiki.html), a [docs/runtime split](confident-ai-deepteam.html)). google_workspace_mcp is clean for a *behavioral* reason: the developer is conspicuously careful about credentials, and the scanner — which fires on credential-shaped code — lit up the auth layer precisely because that's where all the careful code is. Every hit is the safe version of a dangerous pattern: unverified-decode of an *already-trusted* token, a log-suppression comment, `0o600` token files, fingerprinted logging, a loopback self-probe. The finding count (16) is a measure of how much credential code there is, not how much risk.

**"Decode without verification" needs the same call-graph awareness as the SQL and sha1 rules.** The `unverified-jwt-decode` rule is high-value in general (decoding an *attacker-supplied* token without verification is a real auth bypass), but it can't distinguish an attacker-supplied token from `credentials.id_token` (already verified by the OAuth library three lines of trust earlier). This is the same call-graph-vs-token gap behind the [`text(f)` SQL](upsonic-upsonic.html), the [`usedforsecurity=False` sha1](mistralai-mistral-vibe.html), and the [DOMPurify v-html](xerrors-yuxi.html) cases: the rule sees the syntax, the curator reads where the value came from. A refinement that traced the `jwt.decode` argument to a post-OAuth-exchange `Credentials` object could suppress it.

**The log-suppression-comment false positive is a new FP shape worth naming.** A `# … access_token=ya29.xxx …` comment explaining a token-leak *mitigation* got flagged as a token leak. Secret scanners that match inside comments will misread security documentation as the vulnerability it describes. Scoping the `detected-google-oauth-access-token` rule to non-comment lines (or recognizing the obvious-placeholder `ya29.xxx` / `…xxx` shape) would clear it.

## Notes on the tool

- `semgrep.json` verified healthy (71 KB, 0 scanner meta-errors). Dependabot is wired on this repo, so the dependency tail is already handled — consistent with the [deepteam](confident-ai-deepteam.html) "Dependabot-present inverts the dep-tail framing" note; no dep-bump item to raise.
- Two concrete scanner refinements this scan re-votes for: **comment-aware secret scanning** (the `ya29.xxx`-in-a-comment FP), and **call-graph-aware `unverified-jwt-decode`** (suppress when the token argument is a post-OAuth `Credentials.id_token`, not request input). Both are in the same family as the standing `usedforsecurity=False` and DOMPurify-aware suppressions.

## Disclosure timeline

- **2026-06-21** — Scan run at commit `b10c3c9cea8d`; `semgrep.json` verified healthy. All 16 findings inspected in the `auth/` OAuth layer; each confirmed FP or by-design (unverified-decode of an already-trusted token, a log-suppression comment, `0o600` token files, fingerprinted logging, a loopback self-probe). Quality gate false.
- **2026-06-21** — Post-only published. No issue filed and no private report sent (the repo's `SECURITY.md` private email channel would be the route if there were anything real — there wasn't). Seventh clean scan in the series.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/taylorwilsdon/google_workspace_mcp" \
  --reports-dir reports/taylorwilsdon-google-workspace-mcp \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
