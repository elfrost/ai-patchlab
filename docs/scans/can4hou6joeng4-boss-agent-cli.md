---
layout: default
title: "can4hou6joeng4/boss-agent-cli: security scan"
description: "Security scan of can4hou6joeng4/boss-agent-cli: 26 findings at medium+, 1 real — withheld, filed privately. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-09-23
---

# can4hou6joeng4/boss-agent-cli — security scan

**Repository:** [can4hou6joeng4/boss-agent-cli](https://github.com/can4hou6joeng4/boss-agent-cli)
**Commit scanned:** `73e020f`
**Scan date:** 2026-09-23
**Disclosure status:** withheld — one real finding filed privately as
[GHSA-xp54-2hxc-w78q](https://github.com/can4hou6joeng4/boss-agent-cli/security/advisories/GHSA-xp54-2hxc-w78q)
(High, state `triage`). The project's `SECURITY.md` asks that vulnerabilities not
be opened as public issues and points to GitHub private vulnerability reporting,
which is enabled; the report went through that channel and was accepted into
triage on the first attempt. Detail below is kept at class level until the
advisory resolves.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 7 |
| Medium | 16 |
| Low | — |
| Info | 3 (scanner meta) |

**Total findings:** 26 at `--min-severity medium` (1 real after curation — withheld).
The one real finding is **not among the 26** — no rule reported it. It came from
a structural question about a local bridge, not a pattern match.

boss-agent-cli (2.0k★, MIT) is a **CLI for the BOSS Zhipin recruitment platform**
that a human can drive from a terminal wizard and an agent can drive over a
JSON-envelope API, an MCP server exposing ~77 tools, or a Python SDK. It runs
searches, filters, shortlists, and messaging, with a resumable crawler that
checkpoints to SQLite, and it authenticates by reusing the operator's own browser
session — either through cookie extraction or through an optional **Browser
Bridge** (a local daemon plus a Chrome extension) that reuses an already-open,
logged-in tab so the tool never handles the password.

Maintenance is responsive: 67 merged PRs in the last 60 days from seven distinct
human authors, and a long tail of closed bug/feature issues with real
back-and-forth. That responsiveness is why it cleared the pre-check — a report is
worth what the project does with it.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | did not cover every file it was pointed at (`semgrep-partial-coverage`) |
| `gitleaks` | `ran` | no coverage problem reported |
| `trivy` | `ran` | no coverage problem reported |
| `dependency-scan` | `partial` | a shipped lockfile was not covered (`dependency-scan-unaudited-lockfile`) |
| `ai-security-review` | `not_run` | disabled by default (ADR-010) |

**Coverage complete:** no. Semgrep reported partial file coverage, and the
dependency scan did not audit a shipped lockfile (`uv.lock`) — Trivy read the
lockfile in the same run, which is what carried the dependency picture, but the
two dependency tools examining different inputs is exactly the gap this project
records on every partial run. Neither gap touches the real finding, which is in
first-party code the scanners did read.

## The one real finding, at class level

**Severity: High. Class: a loopback control channel with no origin binding —
the desktop-loopback-inversion pattern.**

When everything binds to `127.0.0.1`, the instinct is that the surface is safe
because it is not on the network. The question that actually matters is *what can
a web page reach* — because a browser the victim is already using will happily
send requests to `127.0.0.1` on their behalf.

This project has a local component that accepts commands and carries out
privileged browser actions on the operator's behalf, against a site where the
operator is **logged in**. The component checks neither *who* is asking (no origin
binding of any kind) nor that the request is coming from the tool that is supposed
to be its only client. Two consequences follow, and I confirmed both against the
shipped code rather than reasoning about them:

- A request shape that a browser is allowed to send **cross-origin without a
  preflight** reaches the command channel intact. That makes the channel drivable,
  blind, by any page the victim happens to have open elsewhere — and "blind" does
  not blunt it, because the action it triggers can carry its own payload.
- Because the channel does not bind the request to a trusted host either, a
  second, well-known browser technique turns the blind path into a **readable**
  one, which exposes the credential material for the logged-in session directly.

The precondition is honest and worth stating plainly: this is only exploitable
while the bridge component is actively running, which is a bounded window, not an
always-on service — and the sensitive scope is the one site the tool is built
around. That is why it is a High and not a Critical, and I graded it that way in
the report rather than inviting the maintainer to discover the scope themselves.

**No rule described it.** Every scanner here looks for a dangerous *thing that is
present* — a tainted sink, a bad call, a known-vulnerable version. This is the
*absence* of a check on a channel that is otherwise working exactly as designed,
which is the shape no pattern matcher can see. It is the same class as several
earlier findings in this series where a loopback surface was guarded on its
control plane but not on the plane that actually mattered.

**The fix was written before it was named.** The legitimate callers are the
project's own CLI and its own extension, and both are distinguishable from a web
page by properties they already carry — so a check that rejects the web-page shape
does not break either one. That is the version of the fix in the private report:
narrow, and verified not to break the tool's own two clients.

## Why the rest were dismissed

| Reason | Count | |
| --- | ---: | --- |
| `by-design` | 12 | non-security or intended behaviour |
| `sql-identifier-fp` | 8 | identifier-only interpolation, values bound |
| `not-reachable` | 2 | local/dev URL, not attacker-controlled |
| `product-surface` | 1 | the plugin loader's dynamic import |
| `confirmed-real` | 1 | the withheld finding |

The largest survivors are the recurring ones. All eight SQL hits (five graded
high) are the **#1 identifier false positive**: every `f"… FROM {table}"` /
`f"… {column} …"` interpolates a hardcoded table or column name chosen at the call
site (`"greet_records"`, `"apply_records"`, `"greeted_at"`), while every *value*
rides in as a bound `?` parameter — settled by reading the call sites, not by
enumerating the eight. Of the sixteen mediums, eight are one
`github-actions-mutable-action-tag` rule across the workflow files — supply-chain
hardening worth a SHA pin, not a vulnerability, and a same-rule flood that inflates
the band. The rest: two `sha1()[:16]` digests used to derive a dedup/reference id
(non-security), two `urllib` calls to a local DevTools endpoint and a build
script, a React rule firing on a loopback health-check `fetch`, and a Python 3.7
compatibility rule that is not a security check at all.

## Notes on the tool

- **The real finding was invisible to all four scanners, and that is the point.**
  26 findings at `medium+`, zero of them the vulnerability. It came from asking a
  structural question — *what can a web page reach on this loopback surface, and is
  the channel bound to who may call it?* — which no per-file rule can pose.
- **Coverage was partial in two ways, and the report says so rather than rendering
  it as clean.** Semgrep did not cover every file, and the dependency scan left a
  shipped `uv.lock` unaudited (Trivy read it, which is the luck that carried the
  run). Both are recorded in the coverage block above; neither touches the finding.
- **Same-rule flooding, again.** Half the medium band is one unpinned-action rule.
  Collapsing repeated same-rule hits into one entry with a count remains a standing
  backlog item across the series.

---

*Scanned with [AI PatchLab](https://github.com/elfrost/ai-patchlab). Findings are
curated by hand; scanner output alone is not a vulnerability report. This page
will be updated with full technical detail once the advisory resolves.*

## Reproduce

```bash
git clone https://github.com/can4hou6joeng4/boss-agent-cli /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/can4hou6joeng4-boss-agent-cli --min-severity medium --ignore-samples
```

---

## More from this series

- **Previous scan:** [overwirehq/claude-code-telegram](overwirehq-claude-code-telegram.html) — 2026-09-22, 0 first-party
- [Every scan in the series]({{ '/' | relative_url }}) — 110 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 25 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
