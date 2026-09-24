---
layout: default
title: "superdesigndev/treg: security scan"
description: "Security scan of superdesigndev/treg: 96 findings at medium+, 1 real — withheld, reported privately. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-09-24
---

# superdesigndev/treg — security scan

**Repository:** [superdesigndev/treg](https://github.com/superdesigndev/treg)
**Commit scanned:** `240c595`
**Scan date:** 2026-09-24
**Disclosure status:** withheld — one real finding reported privately by email, per the
project's `SECURITY.md` (which asks that vulnerabilities not be opened as public
issues; GitHub private vulnerability reporting is disabled on the repo, and the
policy names an email address, so email is the channel). Detail below is kept at
class level until the maintainer has had a chance to respond. **The private send
is the operator's step and had not gone out when this page was published.**

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 23 |
| Medium | 69 |
| Low | — |
| Info | 3 (scanner meta) |

**Total findings:** 96 at `--min-severity medium` (1 real after curation — withheld).
The one real finding is **not among the 96** — no rule reported it. It came from a
structural question about the server's outbound requests, not a pattern match.

treg (3.0k★, source-available) is **"OpenRouter for agent tools"**: a multi-tenant
server that holds a team's provider credentials (Fernet-encrypted, server-side) and
proxies tool calls to 3,000+ upstream endpoints, injecting the credential so it never
reaches the caller. It runs hosted at treg.to and is self-hostable. A security model
like that lives and dies on two promises its own `SECURITY.md` makes plainly: the
proxy never hands a key to the caller, and outbound requests are re-resolved at call
time so they cannot be aimed at internal or cloud-metadata hosts.

Maintenance is responsive: hundreds of merged PRs from several human authors in the
last 60 days, with real back-and-forth on closed issues. That responsiveness is why
it cleared the pre-check.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | did not cover every file it was pointed at (`semgrep-partial-coverage`) |
| `gitleaks` | `ran` | no coverage problem reported |
| `trivy` | `ran` | no coverage problem reported |
| `dependency-scan` | `partial` | a shipped lockfile was not covered (`dependency-scan-unaudited-lockfile`) |
| `ai-security-review` | `not_run` | disabled by default (ADR-010) |

**Coverage complete:** no. Semgrep hit a per-file error on five large modules — a
Windows temp-file permission error mid-scan, not a parse failure — so I re-ran those
five files on their own and folded the two recovered findings (both dev-script
`urllib` calls) into the curation below. The dependency scan left the shipped
`uv.lock` unaudited by pip-audit; Trivy read it in the same run, which is what
carried the dependency picture. Neither gap touches the real finding, which is in
first-party code the scanners did read — they simply had no rule for its shape.

## The one real finding, at class level

**Severity: Medium. Class: a server-side outbound request path, reachable by any
member, that skips the call-time host check the main proxy enforces — an SSRF on the
unguarded sibling of a guarded transport.**

The interesting thing about treg's SSRF posture is that it is *mostly right*. It has a
proper call-time guard that resolves a target host and refuses internal, loopback,
link-local, CGNAT, NAT64 and cloud-metadata addresses — I tried the whole zoo of
obfuscated IPv4 literals (decimal, hex, octal, short-form) and the NAT64 prefix, and
every one was refused. That guard is wired into the main proxy path, exactly where the
threat model expects it.

The finding is that the same server makes outbound requests on **more than one** path,
and the call-time guard is applied on one of them and not on a sibling that an
ordinary member can drive. The registration-time check that *does* run on the sibling
is, by its own documented design, a static check that deliberately allows any DNS
name — so a name that resolves to an internal address passes it, and nothing
re-resolves-and-checks before the request goes out. The result is a member-authenticated
server-side request reachable from the product's own egress, with enough of a
status/error signal returned to make it useful.

I confirmed the gap the way this series always tries to: not by reading that a check
was missing, but by running the project's *own* two guard functions side by side on a
host that resolves internally. One returns "allowed" (the registration check); the
other returns "refused" (the call-time check the sibling path never calls). That one
differential is the whole finding, and it is decisive because it uses treg's code, not
my reasoning about it.

**Why Medium, and stated plainly:** the credential injected on the affected path is the
member's *own*, so this is not a route to another tenant's key — it is internal
reconnaissance and metadata reach, not cross-tenant theft. It needs an authenticated
member, which on a self-service product is a low bar but not zero. I graded it Medium
in the private report rather than inviting the maintainer to discover the scope
themselves.

**The fix is one guard, applied at the outbound path, and it changes nothing for a
legitimate public target** — it only refuses the hosts the project's own documentation
already says are refused at call time. The private report gives the exact call sites
and the one-line change at each, plus a few clearly-labelled lower-confidence
authorization observations for the maintainer to assess. The org boundary itself held
everywhere I looked — I found no way for one tenant to reach another's data, and I say
so because a probe that can only ever return "yes" is not worth much; this one could
have returned "no" on the isolation question and did.

**No rule described it.** Every scanner here looks for a dangerous *thing that is
present* — a tainted sink, a bad call, a known-vulnerable version. This is a check that
is present and correct on one path and simply *absent* on its sibling, which is the
shape no per-file pattern matcher can see. It is the same class as several earlier
findings in this series where a control guarded one transport and not the one beside
it.

## Why the rest were dismissed

| Reason | Count | |
| --- | ---: | --- |
| `by-design` | 45 | non-security, intended behaviour, or supply-chain hardening |
| `not-reachable` | 19 | dev/operator scripts, or a transitive CVE not on a request path |
| `sql-identifier-fp` | 17 | identifier-only interpolation, values bound |
| `credited-defense` | 6 | the rule fired on the project's own guard |
| `active-harm-fp` | 4 | the suggested change would *loosen* a `0o700` tightening |
| `domain-noun-collision` | 3 | a "token"/"key" that is a pagination cursor or a family id |
| `dependency-currency` | 1 | one lockfile bump worth making, not a first-party defect |

The two biggest survivors are the recurring ones. Seventeen `sqlalchemy-text` hits are
the **#1 identifier false positive**: sixteen are Alembic migrations setting
`lock_timeout` from module constants and building `CREATE INDEX CONCURRENTLY` DDL, and
the last is a test-reset `TRUNCATE` over ORM-metadata table names quoted by the
dialect's own identifier preparer — no value is ever interpolated. Eighteen `v-html`
hits render the project's *own* static tutorial and syntax-highlighted snippet HTML,
where every interpolated tool field is passed through an `esc(&<>)` helper before
wrapping and a source comment says why. Four `insecure-file-permissions` hits are the
project **tightening** to `0o700` on its sandbox directories — the rule's looser
suggestion would weaken them, the [active-harm false-positive](realiti4-claude-swap.html)
shape. And the one Trivy critical (`anyio` 4.14.1 → 4.14.2, an IDNA hostname-confusion
issue) is a real lockfile bump worth making, reachable only by a network-positioned
attacker against a non-ASCII upstream host — hardening, not a first-party vulnerability.

## Notes on the tool

- **The real finding was invisible to all four scanners, and that is the point.** 96
  findings at `medium+`, zero of them the vulnerability. It came from tabulating the
  server's outbound request paths and asking which ones the call-time host guard
  actually covers — a question no per-file rule poses.
- **Coverage was partial in two ways, and the report says so.** Semgrep hit a
  Windows-side per-file temp error on five large modules (recovered by a targeted
  re-run), and pip-audit left `uv.lock` unaudited while Trivy read it. Both are in the
  coverage block above; neither touches the finding.
- **Same-rule and same-shape flooding, again.** The 96 collapse to a handful of
  families — eighteen `v-html`, seventeen `sqlalchemy-text`, fourteen unpinned-action
  hits. Collapsing repeated same-rule hits into one entry with a count remains a
  standing backlog item across the series.

---

*Scanned with [AI PatchLab](https://github.com/elfrost/ai-patchlab). Findings are
curated by hand; scanner output alone is not a vulnerability report. This page will be
updated with full technical detail once the maintainer has responded and a fix has
shipped.*

## Reproduce

```bash
git clone https://github.com/superdesigndev/treg /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/superdesigndev-treg --min-severity medium --ignore-samples
```

---

## More from this series

- **Previous scan:** [can4hou6joeng4/boss-agent-cli](can4hou6joeng4-boss-agent-cli.html) — 2026-09-23, 1 real — withheld
- [Every scan in the series]({{ '/' | relative_url }}) — 111 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 25 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
