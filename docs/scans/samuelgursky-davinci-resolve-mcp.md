---
layout: default
title: "samuelgursky/davinci-resolve-mcp: security scan"
date: 2026-09-03
---

# samuelgursky/davinci-resolve-mcp - security scan

**Repository:** [samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp)
**Commit scanned:** `619d473`
**Scan date:** 2026-09-03
**Disclosure status:** ✅ **resolved** — reported privately by email; fixed by the maintainer in
[v2.212.1](https://github.com/samuelgursky/davinci-resolve-mcp/releases/tag/v2.212.1) with a
published advisory
([GHSA-8f4v-j8rq-hj47](https://github.com/samuelgursky/davinci-resolve-mcp/security/advisories/GHSA-8f4v-j8rq-hj47),
Low, patched `2.212.1`) and a regression test, **twelve minutes after the report was read**. The
maintainer has cleared the mechanism for publication; the finding below is now in full.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 51 |
| Medium | 44 |
| Low | 0 |
| Info | 2 |

**Total findings:** 97 (1 of interest after curation)

## Top findings

### 1. The networked transport's bearer token was written in cleartext to `logs/server.log` — fixed in v2.212.1

- **Tool:** semgrep — raised at medium, promoted by curation
- **Confidence:** high — mechanism executed against the real module
- **Class:** CWE-532, insertion of sensitive information into a log file
- **Status:** reported privately 2026-09-03, delivered 2026-09-08, fixed the same hour

`src/utils/mcp_transport.py:127` logged the generated bearer token verbatim when the opt-in
networked transport (`--transport sse` or `--transport streamable-http`) was started without
`$DAVINCI_MCP_TOKEN` pinned:

```python
if generated:
    logger.info("Generated bearer token (set $DAVINCI_MCP_TOKEN to pin it): %s", token)
```

That logger has no handler of its own, so the record propagates to the root logger — which
`src/server.py:167-171` had already configured at import time with a
`logging.FileHandler(<project_dir>/logs/server.log)`. `run_networked` is called from that same
module, so the token that is the transport's only access control was appended to a log file.

**Why it mattered even as a local-only exposure: the same secret already had a carefully
protected copy, and the log copy was worse on both axes.** `write_transport_state` stores the
token through `src/utils/private_state.py`, which opens with an explicit `0o600`, re-chmods on
POSIX, runs `icacls /inheritance:r` on Windows, and lives under a `0700` per-user directory
whose docstring says *"never in a shared tempdir"*. `logging.FileHandler` does none of that —
default mode, `0644` under the usual umask, world-readable. And the durability was inverted:
`run_networked`'s `finally:` clears the protected copy at shutdown, while the log line is
appended forever. Every token any networked session ever generated accumulated in
`server.log` and outlived the process.

**The sibling differential was the whole argument.** The control panel's token, in the same
`server.py`, is handled against exactly this threat — *"Passed via the environment (never argv,
which `ps` would show to every local user)"* and *"The token travels in the URL fragment —
browsers never send fragments, so it stays out of every request line and log."* Two tokens,
one threat model, opposite handling. The report pointed at the rule the project had already
written down, and at the claim in `SECURITY.md` that the pidfile and the state file were the
only on-disk copies: there was a third.

**Verified by execution, not by reading.** A script imported the real module, installed the
same root-logger configuration `server.py` installs, stubbed `uvicorn.run`, and called the real
`run_networked`: token present in `server.log`, state file absent after shutdown. The POSIX
mode contrast was read from code (the run was on Windows) and the report said so.

**What limited it.** Opt-in transport only; the default stdio mode never reaches the code.
`logs/` is gitignored. A pinned token never hit the `if generated:` branch. Graded Low on a
single-user desktop, Medium on a shared host or an agent-readable checkout.

**Fix, as shipped in `9f955ab5` / v2.212.1.** The maintainer took the report's primary
suggestion — the log line now names the state file's path instead of the value — and added an
`isatty`-guarded echo of a generated token to an interactive stderr for hand-launched
operators, so a redirected stderr gets nothing. `SECURITY.md` now states the rule outright: the
pidfile and the transport state file are the only on-disk copies of either token, and neither
is ever written to `logs/server.log`. The module docstring no longer describes the token as
"logged at startup". A regression test runs the real `run_networked` against a root
`FileHandler` configured the way `server.py` configures it and asserts the token never reaches
the file — against the previous code it fails with the token found in the log, which is this
finding reproduced in the suite. The advisory's workaround section tells existing users to
treat any token in `server.log` as exposed, truncate the log, and restart.

**And the channel.** The report opened with a process note: `SECURITY.md` named a GitHub
security advisory as its first channel, but private vulnerability reporting was disabled, so
the endpoint answered `403` to an outside reporter. It is enabled now.

### Everything else — 96 findings, none of them real

Set out in full below, because the ratio is the point.

## Patterns observed

**This is the best-defended repository the series has scanned.** That is worth saying before
anything else, because the headline number — 97 findings, one real — reads like a scanner
failure and is actually a description of the codebase. Every security claim I tested held.

The repository ships a SECURITY.md that does something unusual: instead of the customary
"report issues to X", it enumerates its own defenses in specific, checkable terms. The control
panel "refuses any bind host other than `127.0.0.1`". Every route except the static shell
"returns 401 without" a token. It "rejects any request whose `Host` header is not a loopback
host, any request carrying a non-loopback `Origin`, and any `POST` that is not
`Content-Type: application/json`", and "never answers a CORS preflight". It then invites the
reader to falsify it: "If you find a route that can be reached without the token, or a way to
satisfy the Host/Origin checks from a non-loopback page, that is a security bug."

So I took the document as a test oracle and went through it claim by claim. The panel's gate
runs before every route, in both `do_GET` and `do_POST`, and there are no other `do_*` methods
— so `OPTIONS` gets a 501 from the base class, which is a more reliable way of never answering
a preflight than writing code to refuse one. A missing `Host` header fails closed rather than
open. The cross-site paths are covered twice over: a form POST cannot set a JSON content type,
a `fetch()` that can needs a preflight that never comes, and the fallback session cookie is
`HttpOnly; SameSite=Strict`, so it does not ride along on the `<img>`-tag GETs that carry no
`Origin` at all. The path-traversal guard on the doc-asset route is the textbook form —
`realpath`, then `startswith(base + os.sep)`, then an extension allowlist, then `isfile`. Every
claim in that document that I could test, held.

**The one thing the document does not cover is the thing I found**, which is the general shape
of these write-ups worth generalising: a threat model is a map of the risks its author has
already thought about, so the finding is rarely inside it. It is in the gap between two
correct decisions in two different files — each defensible alone, neither aware of the other.
No static rule can see that composition, because neither half is a bug.

**The 36 SQL findings are the same false positive this series has now logged ten times.**
Thirty `sqlalchemy-execute-raw-query` at high plus six `formatted-sql-query` at medium, and
every one is an f-string that interpolates a *fixed* fragment while the values ride on
placeholders: `where = " WHERE clip_uuid = ?"` composed into `f"SELECT * FROM clips{where}"`
with the argument bound, or the classic `placeholders = ",".join("?" for _ in keys)` expansion.
The remaining interpolations are PRAGMA statements and table names from an internal migration
registry — identifiers, which cannot be parameterised in SQLite anyway, and which no end user
selects. Two file reads collapsed the entire cluster.

**Three separate clusters were the tool objecting to correct code.** Semgrep's
`insecure-file-permissions` fired on a `os.makedirs(path, mode=0o700)` — flagging a
deliberately restrictive mode as a weakness, the active-harm false positive class where acting
on the advice would loosen security. The four `insecure-hash-algorithm-sha1` hits are all
`hashlib.sha1(...).hexdigest()[:16]` used for content addressing and job identifiers, never
for authentication. And the eight high-severity `detect-child-process` hits sit on
`spawnSync(bin, ['-v', 'error', ...])` calls into `ffmpeg` and `ffprobe` — argv arrays, no
`shell: true`, which is precisely the pattern a scanner should be looking *for*. Shelling out
to ffmpeg is not incidental to a video-post MCP server; it is the product. I did check the one
thing that would have made it real — whether the binary path itself could be steered from an
MCP tool parameter — and it cannot; `opts.ffmpeg` is only ever set by internal callers.

**The dependency tier splits cleanly along reachability, in both directions.** Trivy reported
around twenty CVEs in the Node tree: seven in `fast-uri`, four in `ip-address`, seven across
`hono` and `@hono/node-server`, plus `qs` and `uuid`. The Hono ones are SSR context leaks,
CORS middleware ReDoS and a `serve-static` traversal — all of which require a Hono application,
and there is not one. `hono` is transitive, declared in neither manifest, and never
instantiated anywhere in the repository; the Node servers here speak stdio. Same for the
URL-parser SSRF cluster, which needs someone to parse an attacker's URL, in a codebase that
parses project files. But the split runs the other way too, and that is the part a
reachability filter usually gets wrong: the `adm-zip` and `fast-xml-parser` denial-of-service
advisories *are* reachable, because chewing through untrusted `.drp` and `.drt` archives is
exactly what this code does. They stay low because the archive is one the user chose to open
on their own desktop. "Is this dependency reachable" is not one question with one answer per
project — it is one question per advisory.

**Credit where the code is defensive and no tool noticed.** The vendored archive reader ships
a `safe-archive.js` that rejects absolute paths, Windows UNC paths, null bytes, any `..`
segment, and — a nice touch — any segment named `__proto__`, `constructor` or `prototype`,
because entry names get used as object keys. The XML-assembly regex escapes its interpolated
filename correctly. The publish workflow runs on tag-push and manual dispatch only, holds
`contents: read` with `id-token: write`, and publishes with `--provenance`, so its three
mutable-action-tag findings are the only hardening note I would make, and a weak one.
`_request_is_loopback` — the kind of helper that is often defined once and never called — turns
out to be wired into twenty privileged routes as a second layer beneath the token gate.

## Notes on the tool

- **The real finding was already in the output, ranked as noise.** Semgrep flagged it as a
  medium in a 51-high report. This is the first entry in the series where the tool found the
  one true positive and the ranking buried it: 51 findings it should not have raised sat above
  the one it should have. Severity here is a property of the rule, not of the code — the same
  rule fires identically on a line that matters and a line that does not, and what separates
  them is context the rule cannot reach from where it is standing. Nothing in the pipeline can
  currently promote the one or demote the other.
- **A second data point for the "read the security policy first" backlog item.** Curating this
  repo against its own SECURITY.md was worth more than the entire scanner output. Every real
  question I asked came from that document, including the one that paid off — which came from
  a claim it *did not* make. A curation step that ingests SECURITY.md, extracts its falsifiable
  assertions, and diffs them against the code would have gone straight to the answer. This is
  the document-level form of the docstring-contract-oracle item already in the backlog; they
  should be the same feature.
- **`sqlalchemy-execute-raw-query` is now the single most expensive rule in the series** —
  ten appearances, several hundred findings, zero true positives. The discriminator is
  mechanical and has never once failed: if every `?` in the statement corresponds to a bound
  argument and the interpolated text contains no user-controlled value, it is not a finding.
  A pre-filter implementing exactly that would have removed 36 of this scan's 97 findings, and
  the remaining 61 would still contain the one that mattered.
- **The dependency layer needs the "reachable here?" column per advisory, not per package.**
  This scan is the clean demonstration: `hono` and `adm-zip` sit in the same lockfile, and the
  correct verdict is "ignore" for one and "note" for the other, for reasons that have nothing
  to do with either version number.
- **Semgrep declared its own coverage gap, and it mattered less than usual.** The run reported
  one rule timeout (`hardcoded-token` on `media_analysis.py`) and a `PartialParsing` error on
  `.github/workflows/npm-publish.yml` — a publish workflow holding `id-token: write`, i.e. the
  supply-chain surface, partly unparsed. I read it by hand instead and found nothing
  exploitable. The `errors` array continues to earn its place; `paths.skipped` was empty again.

## Disclosure timeline

- 2026-09-03 — scan run at `619d473`; mechanism reproduced against the real module
- 2026-09-03 — reported privately by email to the maintainer, per SECURITY.md. GitHub private
  vulnerability reporting is the first channel that policy names, but it is disabled on the
  repository, so an outside reporter cannot use it; the report notes this alongside the finding.
- 2026-09-03 — this page published with the finding withheld
- 2026-09-08 00:37 UTC — private report delivered by email to the address `SECURITY.md`
  points to. The draft had sat unsent for five days; the send is a manual step in this
  pipeline, and the delay was on the reporting side, not the maintainer's
- 2026-09-08 00:49 UTC — **fixed** in `9f955ab5` and released as
  [v2.212.1](https://github.com/samuelgursky/davinci-resolve-mcp/releases/tag/v2.212.1),
  twelve minutes after the email; regression test included
- 2026-09-08 00:55 UTC — advisory
  [GHSA-8f4v-j8rq-hj47](https://github.com/samuelgursky/davinci-resolve-mcp/security/advisories/GHSA-8f4v-j8rq-hj47)
  published (Low, `< 2.212.1`); private vulnerability reporting switched on for the repository
- 2026-09-08 01:16 UTC — maintainer's reply: *"The report was exact, and the reproduction
  matched what I found in the code."* Mechanism cleared for publication
- 2026-09-08 — this page updated with the full detail

## Resolution

Thirty-nine minutes from the email leaving to the maintainer's reply, with a fix, a release, an
advisory and a regression test in between — the fastest resolution in the series by a wide
margin, and the clearest case yet that the slow part of coordinated disclosure was the
reporter. The report was written on 2026-09-03 and delivered on 2026-09-08; the maintainer
needed twelve minutes.

Three things about the fix are worth recording. It adopted the report's *pointer-in-the-log*
suggestion rather than the alternative the report also offered, and then solved the usability
question the report had deliberately left to the maintainer (how does a hand-launching operator
see the token?) with an `isatty` guard — a better answer than either option as written. The
regression test does not merely assert the new behaviour; it reproduces the finding against the
old code, which means the suite now carries the negative control. And the documentation was
corrected in the same release, so the `SECURITY.md` claim this post used as an oracle is true
again — the third on-disk copy is gone, and the policy now says so explicitly.

The advisory credits *"an external security researcher"*; the maintainer offered a named
credit, which is the reporter's call and has not been taken up as of this update.

## Reproduce

```bash
git clone https://github.com/samuelgursky/davinci-resolve-mcp /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/samuelgursky-davinci-resolve-mcp --min-severity medium
```
