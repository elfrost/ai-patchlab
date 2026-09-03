---
layout: default
title: "samuelgursky/davinci-resolve-mcp: security scan"
date: 2026-09-03
---

# samuelgursky/davinci-resolve-mcp - security scan

**Repository:** [samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp)
**Commit scanned:** `619d473`
**Scan date:** 2026-09-03
**Disclosure status:** reported privately — detail withheld pending a coordinated fix

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

### 1. A credential-handling weakness in the opt-in networked transport — withheld

- **Tool:** semgrep — raised at medium, promoted by curation
- **Confidence:** high — mechanism executed against the real module
- **Status:** reported privately to the maintainer on 2026-09-03

SECURITY.md asks that exploit detail not be published before a coordinated fix, and that
request is being honoured: the file, the line and the mechanism are not in this post. What
can be said without helping anyone is the scope. It affects only the opt-in networked
transport, not the default stdio mode, and only for users who did not pin their own token. It
is a local exposure — it gives nothing to a remote attacker, and needs someone who already
shares the machine or the checkout. The fix is one line, and the repository already contains
the pattern it should follow.

This entry will be filled in once a fix ships, or dropped entirely if the maintainer would
rather it stayed private.

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
- Detail withheld from this page pending a coordinated fix.

## Reproduce

```bash
git clone https://github.com/samuelgursky/davinci-resolve-mcp /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/samuelgursky-davinci-resolve-mcp --min-severity medium
```
