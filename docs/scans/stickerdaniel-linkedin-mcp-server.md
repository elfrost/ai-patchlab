---
layout: default
title: "stickerdaniel/linkedin-mcp-server: security scan"
date: 2026-06-23
---

# stickerdaniel/linkedin-mcp-server - security scan

**Repository:** [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server)
**Commit scanned:** `9f0e3383b4f8e3ebf93f661316cdc7396611ce5c`
**Scan date:** 2026-06-23
**Disclosure status:** public — post-only (clean scan, nothing to disclose)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 1 |
| Medium | 5 |
| Low | 0 |
| Info | 0 |

**Total findings:** 6 — **0 real, exploitability-shaped items after curation.** Eighth clean scan in the series.

This is an MCP server that drives a real headless browser to scrape LinkedIn on
your behalf, which means it spends most of its code budget on the single most
sensitive thing an MCP server can touch: **a live, authenticated session
cookie** (`li_at`). It imports that cookie out of your local Chromium keychain,
decrypts it, and persists it to a profile on disk. A scanner pointed at code
like this fires almost entirely on the credential layer — and on this repo,
every hit was the developer doing it *right*. Two of the findings are
particularly instructive: they are static rules misfiring on code that is
correct **precisely because** it does the "insecure" thing.

## The two findings worth your time (both false positives — here's why that matters)

### 1. "Insecure SHA1 hash" in the cookie decryptor — `browser_import/extract.py:103`

Semgrep flags `hashes.SHA1()` as an insecure algorithm. The call site:

```python
def _derive_cbc_key(password: bytes, *, iterations: int) -> bytes:
    """PBKDF2-HMAC-SHA1(password, salt='saltysalt', iterations, dklen=16).
    macOS callers pass iterations=1003; Linux callers pass iterations=1."""
    kdf = PBKDF2HMAC(algorithm=hashes.SHA1(), length=16, salt=b"saltysalt", iterations=iterations)
    return kdf.derive(password)
```

This is not a free choice. `salt='saltysalt'`, `iterations=1003` (macOS) / `1`
(Linux), AES-128-CBC — this is **Chromium's own cookie-encryption scheme**,
hardcoded in Chromium's source. To decrypt a cookie Chrome wrote, you *must*
reproduce its KDF byte-for-byte. Swapping SHA1 for SHA256 here doesn't harden
anything; it just produces the wrong key and the decryption fails. The rule
("SHA1 is not collision-resistant, don't use it for signatures") is correct in
general and irrelevant here: PBKDF2 doesn't depend on SHA1's collision
resistance, and the algorithm is dictated by an external format, not chosen.

### 2. "Insecure file permissions `0o700`" on the cookie tempdir — `browser_import/extract.py:377`

Semgrep flags `os.chmod(temp_dir, 0o700)` and suggests `0o644` as a "good
default." Look at what the directory holds:

```python
temp_dir = Path(tempfile.mkdtemp(prefix="linkedin-cookie-import-"))
os.chmod(temp_dir, 0o700)            # flagged
db_copy = temp_dir / "Cookies"
shutil.copy2(cookies_db, db_copy)
os.chmod(db_copy, 0o600)             # the cookie DB itself: owner-only
```

It's a temp directory holding a copy of your LinkedIn cookie database. `0o700`
is owner-only — the *correct, restrictive* choice — and the DB copy inside gets
`0o600`. The rule's suggested "fix" (`0o644`) would make the secrets
**world-readable**. This is the failure mode worth internalizing: a
permissions rule with a one-size default will flag the hardened path and wave
through the lax one, because it reads the octal literal, not the intent. If you
auto-apply this class of suggestion you actively *downgrade* security.

## The rest, briefly

- **`urllib` dynamic-URL use** (`error_diagnostics.py:339`) — FP. The "dynamic"
  URL is a hardcoded GitHub issue-search endpoint with a `quote_plus`-encoded
  query string and `timeout=3`. No user-controlled scheme, no `file://` reach.
- **`logger-credential-leak`** (`error_handler.py:80`, confidence already
  downgraded to low) — FP. The line logs a `CredentialsNotFoundError` — whose
  message is *"credentials not found"* — not a credential value. The rule fired
  on the word "Credentials." (Five-for-five FP rate on this rule across the
  series now.)
- **Two transitive dependency CVEs** — `starlette` CVE-2026-54283 (urlencoded
  form-limit bypass DoS) and `pydantic-settings` GHSA-4xgf (symlink-follow out
  of `secrets_dir`). Both are real advisories and both are **version-match
  without reachability here**: `starlette` is pulled in only via FastMCP's
  *optional* `streamable-http` transport (default is stdio, and even in HTTP
  mode MCP speaks JSON-RPC, not `request.form()` urlencoded — the actual CVE
  sink); `pydantic-settings` is transitive and the vulnerable
  `NestedSecretsSettingsSource` is never imported (config is plain dataclasses,
  0 references in the tree). A `uv lock` refresh clears both for free — good
  hygiene, not an exploitable condition.

## Patterns observed

The thing this repo gets right is **the layout of the credential blast radius**.
The cookie DB is copied into a `0o700` tempdir, the copy is `0o600`, the live DB
is never opened in place, the temp dir is torn down in a `finally`, and the
config carries an explicit, well-reasoned gate: auto-import-from-browser is
disabled on any non-loopback HTTP bind, with a comment explaining that a
network-exposed server must never read the host keychain. The HTTP transport
validator warns, in plain language, that the MCP endpoint has **no
authentication** if you bind it to `0.0.0.0`. These are the decisions you hope
to find and usually have to go looking for; here they're already made and
documented inline.

That makes this the clean inverse of the failure mode this series usually
chases. A credential-handling MCP server is exactly where you expect to find a
plaintext key dumped to stdout (zotero-mcp) or a cookie written world-readable.
Instead, the scanner's four code-level hits are all *the hardening itself* being
mistaken for the vulnerability. The reusable lesson is about the tool, not the
target: **a static rule keyed on an octal literal or an algorithm name cannot
see intent.** SHA1-inside-PBKDF2-for-interop and `0o700`-on-a-secrets-tempdir
are correct *because* of the thing the rule objects to. Triage that auto-applies
this class of suggestion doesn't just add noise — it can talk a careful
developer into loosening permissions on their own secrets.

## Notes on the tool

- **Semgrep's `insecure-hash-algorithm-sha1` rule has no PBKDF2 exception.**
  SHA1 inside a `PBKDF2HMAC(...)` construction is not a signature/collision use
  and is frequently mandated by an external format (Chromium cookies here).
  Backlog item: suppress or downgrade this rule when the `hashes.SHA1()` is an
  argument to a KDF constructor.
- **`insecure-file-permissions` suggests `0o644` unconditionally**, including
  for directories and for paths that demonstrably hold secrets. Suggesting a
  *more permissive* mode as the "fix" for an already-restrictive `0o700` is an
  active-harm false positive. Backlog item: never recommend widening
  permissions; only flag modes laxer than the current one.
- The **version-match-vs-reachability** split (a recurring theme since the
  Ouroboros and mistral-vibe scans) held again: both dep CVEs are genuine
  version matches that are not reachable in this project's usage. The report
  surfaces severity from the advisory but not an "is this import path even
  present?" column — still the most valuable missing dimension in the SCA
  output.

## Disclosure timeline

- 2026-06-23 — scan run, full curation
- 2026-06-23 — public post (this page). No issue or PR filed: nothing rose to a
  real, exploitability-shaped finding, and a "two unreachable transitive CVEs +
  consider Dependabot" issue would be exactly the low-signal noise this project
  declines to file. Post-only is the honest outcome.

## Reproduce

```bash
git clone https://github.com/stickerdaniel/linkedin-mcp-server /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/stickerdaniel-linkedin-mcp-server --min-severity medium
```
