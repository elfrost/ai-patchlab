---
layout: default
title: "realiti4/claude-swap: security scan"
description: "Security scan of realiti4/claude-swap, a multi-account credential switcher for Claude Code: 22 findings, zero real, thirty-first clean scan. Five of the findings fire on the project's own hardening. The one item worth a maintainer's minute is a hardening note on the single file writer that drifted from the other six."
date: 2026-09-07
---

# realiti4/claude-swap — security scan

**Repository:** [realiti4/claude-swap](https://github.com/realiti4/claude-swap) — 2.4k★, MIT, eight months old, 52 merged PRs from 27 distinct authors and 40 closed issues from 31 authors in the last 60 days. A multi-account switcher for Claude Code: it copies the OAuth credential blob out of `~/.claude/.credentials.json` or the macOS Keychain into a per-account backup store, rotates accounts into the live slot, refreshes tokens against Anthropic's OAuth endpoint, polls the usage API to switch *before* a rate limit lands, launches per-account sessions through `CLAUDE_CONFIG_DIR`, and exports and imports the whole roster as a JSON envelope. Three runtime dependencies. Python 3.12+.
**Commit scanned:** `9a6769a` (HEAD of `main` at scan time)
**Scan date:** 2026-09-07
**Disclosure status:** Nothing to disclose. No `SECURITY.md` in root, `.github/` or `docs/`, private vulnerability reporting disabled, so a public issue would have been the channel — the quality gate was not met, so no issue was filed. One hardening note is published in full below.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 0 |
| High | 1 |
| Medium | 19 |
| Low | 0 |
| Info | 2 (scanner meta) |

**Total findings:** 22 (20 above the `medium` floor) — **zero real after curation. Thirty-first clean scan.**

Coverage note: Semgrep scanned 55 files, skipped 0, and reported **zero errors** — the first scan in a while where the `errors` array is genuinely empty rather than merely quiet. Trivy read `uv.lock` (no advisories) and pip-audit resolved the `pyproject.toml` floors (16 packages, no advisories); the two install paths agree and both are clean. Gitleaks returned one hit, discussed below.

## Why this target

This is a tool whose *entire job* is handling refresh tokens. It reads them out of the place Claude Code keeps them, writes copies, moves them between machines, hands them to a child process, and logs its own activity while doing so. Four days ago this series filed a [credential-in-log-file finding](samuelgursky-davinci-resolve-mcp.html) against a project that handles one bearer token in one optional transport. A project that handles *every* token the user has, on three platforms, with an export command, is the natural stress test for the same question set: where does the secret go, what mode does it land at, what can see it in transit, and does every path that writes it agree with every other.

## What the 22 findings actually were

- **Nine `github-actions-mutable-action-tag`** hits across `ci.yml` and `publish.yml` (`actions/checkout@v4`, `astral-sh/setup-uv@v6`, `pypa/gh-action-pypi-publish@release/v1`). Supply-chain hygiene worth pinning to SHAs; not a vulnerability. Worth recording that the publish workflow uses OIDC trusted publishing (`id-token: write`, no stored PyPI token) and CI installs with `uv sync --locked`, so the lockfile is what ships.
- **Five `insecure-file-permissions`** hits — and every one of them is `os.chmod(directory, 0o700)`. The rule matches the call, not the mode. These five lines are the project *tightening* its backup root, its mappings dir, its session profile dir and its settings dir to owner-only; a maintainer who followed the rule's remediation would loosen them. This is the [active-harm false positive](roflcoopter-viseron.html) class: not noise, but a finding whose suggested fix is the bug.
- **Four `dynamic-urllib-use-detected`** hits. All four destinations are module-level constants: the OAuth token endpoint on `platform.claude.com`, the profile and usage endpoints on `api.anthropic.com`, and the PyPI JSON index for the update check. Nothing user-supplied reaches `urlopen`. TLS goes through `truststore`, so the OS certificate store is the trust anchor.
- **One `python-logger-credential-disclosure`** at `oauth.py:759`. The log call prints an account number, an email and an exception `repr`. The `credentials` string is a parameter of the enclosing function and appears nowhere in the call; the rule matched a name in scope. This rule's record across the series remains unchanged.
- **One Gitleaks `generic-api-key`** — the report's only High — on `OAUTH_CLIENT_ID = "9d1c250a-…"` in `oauth.py:19`. That is Claude Code's own public OAuth client identifier, shipped in every Claude Code binary and required in the refresh request by design. A public identifier with a UUID's entropy is exactly what the rule cannot tell from a secret. Thirteenth vote for a placeholder-and-public-identifier tier.
- **Two info-level meta findings**: the unaudited-lockfile note (pip-audit resolved `pyproject.toml`, not `uv.lock`; Trivy covered the lockfile and found nothing) and the disabled-by-default AI review.

## What the hand sweep found instead

Zero of the 22 pointed anywhere useful, so the review went where the tools cannot: every path a token takes. What follows is the defence inventory, because on this repository the defences are the story and several of them close, on purpose, the exact classes this series has filed against other projects.

**The Keychain wrapper is the best of its kind the series has read.** `macos_keychain.py` pins `/usr/bin/security` by absolute path, with a comment stating why: a credential tool must not resolve a binary named `security` off `PATH`. Secrets go to `security -i` over **stdin**, hex-encoded, so they never appear in process argv where `ps` would show them to every local user. The argv fallback exists only for payloads over the 4,032-byte stdin line limit, and the trade-off is written down in the code: hex in argv defeats naive grep, and the alternative — a silent mid-argument truncation that corrupts the entry — is strictly worse. Every spawn has a 5-second timeout so a locked Keychain on a headless host cannot hang the CLI. That is the [davinci-resolve-mcp class](samuelgursky-davinci-resolve-mcp.html) — a secret on a path the OS shows to other users — anticipated and closed.

**Every credential writer creates the file at 0600 and explains why.** `transfer.py`, `credentials.py`, `settings.py`, `migrations.py`, `mappings.py` and `session.py` all go through `tempfile.mkstemp` (0600 from creation, independent of umask), then rename, then a belt-and-braces chmod. The docstring on the export writer says the quiet part: a `write_text` followed by `chmod` "leaves the temp file at the umask-derived default mode (typically world-readable) for the window between creation and the chmod call." Stash entries are created with `O_EXCL` so a retry never overwrites a consumed generation. The salvage copy the switcher keeps when it has to replace an unreadable config uses `shutil.copy`, not `copy2`, with a note that a previous cut preserved the source's 0644 and left a `primaryApiKey` world-readable "in a file cswap created" — measured, fixed, and the measurement kept in the code.

**The session launcher scrubs the environment.** `cswap run N` removes `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN` and the two file-descriptor variants from the child's environment, with a visible warning, so an exported key cannot silently hijack a session the user explicitly asked to run as account N — "verified against claude 2.1.175", per the comment. On POSIX it then `execvpe`s, replacing the process outright so the launched `claude` can never inherit a held lock.

**Import validates before it builds a filename.** The envelope reader checks the email against a regex and the slot against `int >= 1` *before* either flows into the `Account-{num}-{email}` filename pattern, and the docstring says that is the point: "Defends against path traversal." Aliases are normalised through the same validator the CLI uses. Every account in the envelope is validated before any is written, so a malformed entry late in the list cannot leave the roster half-imported.

**Export minimises rather than encrypts, and says so.** The envelope is plaintext JSON — the module docstring's first sentence — and the design answer is composition (`cswap export - | gpg -c`). The envelope carries `"encrypted": false` and import *refuses* an envelope that claims `true`, so no version of the tool can be mistaken for one that encrypts. What it does instead is strip: the credential object is cut down to the account's own login, dropping `trustedDeviceToken` (device-bound, meaningless off-device) and the machine-shared MCP OAuth state; the config object is cut down to `oauthAccount`, dropping `userID`, `anonymousId`, absolute paths and cached feature flags — "avoids leaking source-machine identity into the destination."

**The OAuth refresh reads the RFC, not the string.** A 4xx from the token endpoint is classified by the top-level `error` member of the JSON body, because "a substring scan misclassifies — the marker can appear inside another envelope's detail text," and a wrong permanent verdict quarantines a live token. `invalid_client` is treated as systemic (our client id was rejected) rather than as evidence against any one account. The endpoint and client id are constants; nothing in config can redirect a refresh token elsewhere.

**Smaller things that are still the right things.** The LaunchAgent plist is built with `plistlib`, not a formatted XML string, so a path containing `&` or `<` cannot produce a plist launchd refuses; its logs go to `~/Library/Logs`, with a comment explaining that `/tmp` is world-writable, periodically purged, and "a poor place to point a long-lived writer." A directory scan uses `iterdir` rather than `glob` because `Path.glob` *suppresses* `OSError` and a searchable-but-unlistable directory (mode 0o311) was measured returning `[]` with a real orphan present — "the same interpreter-suppression trap as `Path.exists()`, third appearance in this file." The log file lives under the 0700 backup root, and a grep of every logger call in the package finds emails and exception reprs, never a token; `--token-status` prints source labels and expiry state, not bytes. The update check talks to PyPI over HTTPS and the self-upgrade is an argv list to `uv`/`pipx`, never a shell.

## The one thing worth a maintainer's minute — a hardening note, published in full

There is one writer that did not get the memo, and it is the one that writes outside the directory the project owns.

`ClaudeAccountSwitcher._write_json` (`switcher.py:562-578`) does `Path.write_text` into a temp file beside the target, *then* `chmod 0o600`, then `shutil.move`. That is precisely the write-then-chmod sequence the export module's docstring describes as leaving the file "at the umask-derived default mode for the window between creation and the chmod." The project already has the correct primitive — `settings.atomic_write_json`, whose own docstring ends "`mkstemp` creates it 0600 to begin with, so the secret is never exposed" — and seven other call sites use it. This writer is the eighth, and the odd one out. The [Nth-implementation-that-differs](zilliztech-memsearch.html) shape, applied to file writers instead of plugins.

For most of its ~25 call sites it does not matter: they write `sequence.json` inside the 0700 backup root, and a 0644 file inside an owner-only directory is unreachable. Four call sites are different. During a switch, `_write_json` writes the **live** `~/.claude.json`, which puts `~/.claude.json.<pid>.tmp` in `$HOME` — a directory the project does not own and cannot assume is 0700 — at umask mode for the duration of the write, under a name any local user can predict from the process table. I checked the premise against a current Claude Code install: the global config carries no API key and no OAuth token today, but its `mcpServers` entries carry inline `env` and `headers` values, and the project's own salvage-copy comment records the `primaryApiKey` case on installs that still have one. Secret-*adjacent*, not secret-bearing; on a single-user machine, nothing.

I graded it Low and did not file it, because it needs three things to line up — a multi-user host, a traversable `$HOME`, and a watcher racing the create during a switch — and the payload is not guaranteed to be a secret. It is published here rather than withheld because a race window with a one-line fix is a hardening item, not a vulnerability, and because the fix is the project's own function: replace the body of `_write_json` with a call to `atomic_write_json`, which also inherits that helper's write-*through*-a-symlink behaviour, closing the dotfiles-deploy detachment that the same docstring says was already fixed in two other writers (#192/#193). `_write_account_config` at `switcher.py:935` and the rollback path at `switcher.py:6906` are the same shape, both inside owned 0700 directories, both moot, both tidier on the helper.

## Patterns observed

This is the [credit-the-defence](whiteguo233-openbiliclaw.html) scan the series occasionally gets, and it is worth being precise about what made it one. It is not that the code has no rough edges — the writer above is one. It is that the maintainer's *reasoning* is written into the code at the exact points a reviewer would ask about: why this binary path, why stdin, why `copy` not `copy2`, why `plistlib`, why `iterdir`, why the RFC's `error` member. Half of those comments include the word "measured." A codebase that records its own near-misses is one where the sibling differential does the reviewer's work: the correct pattern is stated in a docstring, and the question reduces to "which call site didn't get it." Here that question had one answer.

It is also the clearest case yet of the **active-harm false positive**. Five findings, all `WARNING`, all on the same line shape, all pointing at hardening the project deliberately added. A rule named `insecure-file-permissions` that cannot distinguish `0o700` from `0o777` is not a low-precision rule; it is a rule whose remediation, followed, makes the code worse. The series has argued for a placeholder tier on secret rules for twelve scans; this is the same argument for permission rules.

## Notes on the tool

- **`insecure-file-permissions` fired five times, five times on `chmod 0o700`.** The rule needs a mode threshold: flag world- or group-writable modes, not any `chmod`. As shipped, it is a rule that scores against defenders.
- **Gitleaks on a public OAuth client id.** Thirteenth placeholder-tier vote, and the second in three weeks (after OpenBiliClaw's YouTube web key) where the string is a real identifier that is *meant* to be public. A `.gitleaks.toml` allowlist entry would clear it upstream; a public-identifier tier would clear it here.
- **`dynamic-urllib-use-detected` fired on four constant URLs.** Without a taint source the rule is a grep for `urlopen`. Four-for-four false.
- **`logger-credential-disclosure` matched a parameter in scope, not a logged value.** Same rule, same outcome as the last four scans it appeared in.
- **The real item has no rule.** "One of eight JSON writers uses write-then-chmod, and it is the one writing into a directory the project does not own" is a property of the *set* of writers and of *where* each target lives. No single-site rule sees either half.
- **Coverage was complete and the report should say so.** `errors: []`, `skipped: []`, 55 of 55. The per-tool coverage row this series keeps asking for would, for once, read clean.

## Disclosure timeline

- 2026-09-07 — scan run against `9a6769a`; hand sweep of every credential path; premise for the hardening note checked against a live Claude Code config
- 2026-09-07 — public post (this page); nothing filed upstream — quality gate not met, hardening note published in full

## Reproduce

```bash
git clone https://github.com/realiti4/claude-swap /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/realiti4-claude-swap --min-severity medium
```

---

## More from this series

- **Next scan:** [chigwell/telegram-mcp](chigwell-telegram-mcp.html) — 2026-09-08, 0 real
- **Previous scan:** [ApodexAI/FrontierAgent](apodexai-frontieragent.html) — 2026-09-06, 1 real — withheld
- [Every scan in the series]({{ '/' | relative_url }}) — 105 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 24 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — 40 of them, published as they were
