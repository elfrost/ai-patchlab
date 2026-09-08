---
layout: default
title: "chigwell/telegram-mcp: security scan"
date: 2026-09-08
---

# chigwell/telegram-mcp — security scan

**Repository:** [chigwell/telegram-mcp](https://github.com/chigwell/telegram-mcp)
**Commit scanned:** `02f93bf`
**Scan date:** 2026-09-08
**Disclosure status:** public — clean scan, nothing filed

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 18 |
| Medium | 17 |
| Low | 0 |
| Info | 2 |

**Total findings:** 38 (0 real after curation)

## Top findings

There are none. This is the thirty-second scan in the series to come back clean,
and the shape of the noise is the interesting part. One `Critical` and fifteen
of the eighteen `High` findings are Trivy reading a single dependency file that
no way of installing this project ever touches. The rest are the usual
placeholder secrets, mutable GitHub Actions tags, and two rules objecting to
code that is doing the right thing.

## The project

An MCP server that hands a Claude, Cursor, or Codex agent the keys to a Telegram
account: 80-plus tools spanning messages, chats, groups, admin operations,
contacts, media, and voice transcription, over [Telethon](https://docs.telethon.dev/).
It is a real one — 1.6k stars, Apache-2.0, 37 merged pull requests from 26
distinct authors in the last sixty days, and a codebase that has clearly been
through security review already. The defensive detail is not incidental; it is
everywhere, which is why the clean result is worth reading rather than the raw
count.

## The one finding worth stating: a lockfile that isn't an install path

Trivy produced twenty of the thirty-eight findings — the lone `Critical` and
fifteen `High` — and every single one is an advisory against `poetry.lock`:
`h11 0.14.0`, `mcp 1.6.0`, `starlette 0.46.2`, `rsa 4.2`, `pyasn1`, and so on.
Read on its own, that is an alarming report, and it includes a genuinely
scary-sounding line: *"DNS Rebinding Protection Disabled by Default in Model
Context Protocol."* For an unauthenticated MCP server that speaks HTTP, that is
exactly the advisory you would not want to be real.

It is not real here, for a reason a scanner cannot see: **`poetry.lock` is not
an install path for this project.** The evidence is unanimous.

- The `pyproject.toml` has **no `[tool.poetry]` section** — it is a setuptools
  project. `poetry install` would not build it from this file, and the lockfile
  does not correspond to it.
- The README's quick start is `uv sync`, which resolves `uv.lock` — and `uv.lock`
  pins **`mcp 1.29.0`, `starlette 1.6.0`, `h11 0.16.0`, `rsa 4.9.1`**. Every one
  of Trivy's twenty advisories is already fixed there.
- The Dockerfile installs with `pip install -r requirements.txt`, and
  `requirements.txt` carries open floors (`mcp[cli]>=1.8.0,<2`, no pin on
  `starlette`/`h11`/`rsa`), so a build resolves the current, patched releases.
  The Poetry lines in the Dockerfile are **commented out** (lines 16-19).

So the stale lockfile is a fourth manifest that sits in the tree, is generated
by nothing, and is read by no installer — except Trivy, which has no notion of
"is this file an install path" and dutifully reports its contents as if someone
ran it. The correct verdict on all twenty is *not reachable via any documented
install path*, and the correct action is hygiene: **delete `poetry.lock`** so it
stops misleading both scanners and any contributor who assumes a committed
lockfile means something.

The MCP DNS-rebinding advisory deserves the extra sentence, because it is the
one a reader would most want checked rather than asserted. The version this
project actually ships — `mcp 1.29.0` — has the protection **on** by default. I
ran it: `FastMCP(...).settings.transport_security` comes back with
`enable_dns_rebinding_protection=True` and `allowed_hosts` pinned to
`127.0.0.1:*`, `localhost:*`, `[::1]:*`, and that object is passed into the
streamable-HTTP session manager. A browser page trying to rebind a domain to the
loopback port sends `Host: attacker.example` and is rejected before any tool
runs. The project also wires `MCP_ALLOWED_HOSTS`/`MCP_ALLOWED_ORIGINS` into that
same setting for the reverse-proxy case, and its `docker-compose.yml` binds
`127.0.0.1:8765` only, with a comment that says the endpoint is unauthenticated
and must stay on localhost. The advisory is fixed in the shipped SDK and the
deployment does not contradict it. It reads as `Critical`-adjacent and is inert.

## Patterns observed

**This is a defended codebase, and the defenses are the kind a scanner cannot
credit.** The file-path tools (`send_file`, `download_media`, `upload_file`, …)
are **deny-all by default**: they take their allowed roots from the MCP client's
Roots list, and if the client advertises an empty list, or `list_roots` fails in
a way the code cannot safely recover, the tools are disabled rather than falling
back to something permissive. Server-side CLI roots are honoured only behind an
explicit `TELEGRAM_ALLOW_SERVER_ROOTS_FALLBACK` opt-in. Every path is
`resolve()`d and checked against the roots — parent directory included — and an
extension allowlist is applied on top. A download stages into a private temp
directory, enforces a byte cap mid-transfer, and re-validates the resolved final
path before `os.replace`. This is the confinement discipline this series usually
finds *missing*; here it is the default and the escape hatch is the thing you
have to turn on.

**Prompt injection is treated as the primary threat, which is correct for a tool
that feeds Telegram content to an LLM.** Every tool result that carries
user-controlled text runs through `sanitize.py`, which strips control and
zero-width characters, collapses runaway newlines, and — the part that matters —
leans on a structural JSON boundary so a chat message cannot be confused with a
field name or a tool instruction. The module's docstring reasons about the
threat model rather than reaching for a keyword denylist, and explicitly rejects
keyword detection as too brittle. The incoming-event-feed documentation carries
the same warning: feed lines contain untrusted `name` fields.

**The credential handling anticipates the exact class this series has filed
elsewhere.** The Telegram session string is the crown jewel, and it is never
logged: the file logger is `ERROR`-level and writes API errors, not secrets;
the session-pool lock derives a filename from a truncated one-way hash of the
session rather than writing the session anywhere; the contact-alias and
transcript stores are created `0700`/`0600` because they hold personal-chat
text. There is even a PyPI-collision guard (`install_guard.py`) that refuses to
run if the installed distribution metadata points at the unrelated `telegram-mcp`
package that currently squats the name — a supply-chain footgun the README also
warns about in prose.

## What the other eighteen findings were

- **Four Gitleaks "generic-api-key" (High).** All placeholders: `.env.example:3`
  is `TELEGRAM_API_HASH=0123…`, `README.md:450` is a proxy-secret example
  `ee0123…`, and two are fixtures in `tests/test_runtime.py`. The
  placeholder-tier false positive, now logged more times than any other secrets
  result in the series.
- **Ten Semgrep `github-actions-mutable-action-tag` (Medium).** Actions pinned to
  a moving tag rather than a commit SHA across three workflows. Real hardening,
  the recurring largest cluster, not a vulnerability.
- **One Semgrep `insecure-hash-algorithm-sha1` (Medium).** `runtime.py:421`
  hashes the session string to *name a lock file* — content addressing, not
  authentication. SHA-256 would change nothing.
- **One Semgrep `insecure-file-permissions` (Medium).** `transcription.py:135` is
  `os.chmod(dir, 0o700)` — the project *tightening* a directory that holds
  plaintext chat transcripts. The remediation the rule implies would loosen it.
  The [active-harm false-positive class](realiti4-claude-swap.html), one scan
  after five of the same on claude-swap.
- **Five more Trivy advisories at Medium** — same orphaned `poetry.lock`.
- **Two info/meta**: the dependency-scan coverage note (below) and AI review
  disabled by default.

## Notes on the tool

- **The dependency layer needs a notion of "is this file an install path."**
  This scan is the sharpest case yet in the series. On
  [OpenBiliClaw](whiteguo233-openbiliclaw.html) two dependency tools disagreed and
  *both were right* because the project shipped both a lockfile and open floors as
  real install paths, so the fix was to report them as separate rows. Here the
  inverse: a fourth manifest that **no** install path uses drives the entire
  `Critical`+`High` tier, and the merged verdict is wrong for **every** actual
  user of the project. A scanner that read `uv.lock` (the README's path) would
  have reported zero. The value-add a bare Trivy run cannot provide is the one
  sentence "which of these committed manifests does an install actually resolve"
  — and the answer retired twenty findings, including one that reads as Critical.
- **The one true coverage note fired correctly.** `dependency-scan` flagged that
  `requirements.txt` was not covered by pip-audit's resolution — the honest
  "which manifest did the tool open" signal the series now treats as a Gate-0
  question. It did not hide anything here, because the manifests that matter
  (`uv.lock`, the open floors) are clean, but it is the right thing to surface.
- **`insecure-file-permissions` and `insecure-hash-algorithm-sha1` both fired on
  correct code, again.** A `0o700` chmod and a non-security SHA-1 filename hash
  are two rules whose false-positive rate in this series is now effectively total
  on repositories that handle their own secrets carefully — the better a project's
  hygiene, the more these two rules misfire, because tightening permissions and
  content-addressing with a fast hash are exactly what careful code does.

## Disclosure timeline

- 2026-09-08 — scan run at `02f93bf`; every finding curated to false-positive,
  by-design, or hardening
- 2026-09-08 — the MCP DNS-rebinding advisory checked by executing the shipped
  SDK version; protection confirmed on by default
- 2026-09-08 — public post (this page). Nothing filed: no real finding, so the
  quality gate is false and the clean-scan write-up stands alone

## Reproduce

```bash
git clone https://github.com/chigwell/telegram-mcp /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/chigwell-telegram-mcp --min-severity medium
```
