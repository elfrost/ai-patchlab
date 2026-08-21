---
layout: default
title: "liaohch3/claude-tap: security scan"
description: "Security scan of liaohch3/claude-tap: 104 findings (104 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-16
---

# liaohch3/claude-tap — security scan

**Repository:** [liaohch3/claude-tap](https://github.com/liaohch3/claude-tap)
**Commit scanned:** `901b856f` (main at scan time)
**Scan date:** 2026-08-16
**Disclosure status:** withheld — strict-norm repo (`SECURITY.md` forbids public
vulnerability issues), one real finding described here at class level only. The
private report is a manual step this pipeline cannot take — see the channel note.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 37 |
| Medium | 67 |
| Low | — |
| Info | — |

**Total findings:** 104 above the medium floor (1 real after curation —
**withheld**; **zero** of the 104 scanner findings represented it).

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

## The project

`claude-tap` (3.1k★, MIT) is a **local traffic tap for AI coding clients**. You
point Claude Code, Codex, Cursor and friends at it as a proxy, and it records
every request and response — prompts, system instructions, tool schemas, model
output, file paths — into a local SQLite store, then serves a browser dashboard
that lets you replay and export any session. It ships a reverse proxy, a forward
proxy, a WebSocket proxy, generated CA certificates for TLS interception, and an
HTML trace viewer. It is, by construction, the single point in a developer's
setup through which *all* of their AI-session content flows.

The maintainer is a solo developer building in the open, and the project is
alive: 40 pull requests merged in the last 60 days from five distinct
contributors, 13 issues closed in the same window. That is a responsive
maintainer, which is why it cleared the pre-check.

It is also **strict-norm**, and unusually thoughtfully so. There is a real
`SECURITY.md` — not a template — and it does the one thing a good policy does:
it **names its own threat model**. In scope, it says, are "API key, auth token,
cookie, or header handling," "trace redaction and export behavior," "reverse
proxy and forward proxy routing," "`--tap-host`... and remote binding behavior,"
"generated CA certificates," and "generated viewer HTML that may contain private
trace data." It warns, correctly, that trace files "can contain prompts, tool
schemas, file paths, response bodies, and other private context **even when API
keys are redacted**." A policy that hands you the list of places to look is a
policy written by someone who has looked. The finding lives on that list.

## Channel, and what this write-up does not contain

`SECURITY.md` says plainly: *"do not open a public GitHub issue for
security-sensitive reports"* and *"contact the maintainer privately before
sharing exploit details."* Its preferred private channel is GitHub private
vulnerability reporting — but PVR is **disabled** on this repository
(`repos/.../private-vulnerability-reporting → {"enabled":false}`), so the one
channel the policy names first is unreachable for an outside reporter, and no
email is published. That is [rocketride](rocketride-org-rocketride-server.html)'s
channel state (a) again: the working channel is a private message the maintainer
has to be reachable on, and **this pipeline has no way to send it.** The private
report is the operator's to make. (As with rocketride, the PVR toggle is one
click; enabling it would give every future reporter a working channel and is
worth doing regardless of this finding.)

Because the report has not reached the maintainer privately yet, this page
describes the **shape** of the finding and the reasoning that produced it. The
specific component, the port, the exact endpoints, the header, the
redaction asymmetry, and the reproduction are left out. As on every withheld
scan in this series, **the tooling section below is therefore deliberately
incomplete** — an exhaustive "every bucket and why it is dismissable" list would
identify the withheld item by subtraction. What is listed is accurate; it is not
the whole list.

## The one real finding, at class level

The class is **a correct same-origin guard wired to the control plane and not to
the data plane of a loopback HTTP service.**

The codebase runs a local HTTP server bound to `127.0.0.1`. Everything about
that binding is defensively reasoned: it stays on loopback by default, it drops
to a wider bind only in the one mode where that is the operator's explicit
intent, and — this is the part that matters — **the maintainer wrote exactly the
right defense against the loopback attacker.** There is a function in the tree
that validates a request's `Host` header is loopback and its `Origin`, if
present, is same-origin, and refuses otherwise. It is the textbook mitigation for
DNS rebinding, which is the whole threat model for a service that binds
`127.0.0.1` but is reachable by any web page the victim visits. The check is
correct. The problem is **where it is called.**

It guards the one *control* action — the request that can change the server's
state. It does **not** guard the requests that *read* the server's data, or the
ones that export it, or the ones that delete it. Those handlers were written
without it. So the server that carefully refuses a cross-site request to change
its state will answer a cross-site request to hand over everything it has stored
— which, for this project, is the developer's entire history of AI-session
content: the prompts, the model's replies, the tool schemas, the file paths.
Header-level secrets (API keys) are redacted at capture, exactly as the policy
promises; the *bodies*, which the policy explicitly flags as sensitive "even
when API keys are redacted," are not.

This is the **exact inverse of [jupyter-mcp](datalayer-jupyter-mcp-server.html)**,
and the two scans are worth reading as a pair. On jupyter-mcp I drafted a
loopback-CORS finding and then killed it, because the scary line was *inert*: an
origin check from the framework ran **first** and shadowed it, so the dangerous
configuration never got a turn. Here the ingredients are identical — a loopback
listener and a correct origin/Host check — but the outcome is reversed, because
this time the correct check is the project's own and it is wired to the wrong
subset of routes. Same two parts, opposite result, and the entire difference is
*which handlers the guard sits in front of*. jupyter-mcp was safe because a guard
it did not write ran everywhere; this is exposed because a guard it did write
runs in one place.

Three properties made it worth reporting rather than filing as best-practice
noise:

**No rule represented it.** Not ranked low — absent. All four tools produced 104
findings above the medium floor and **none of them described this.** There is no
dangerous sink, no injection, no missing `check=`. Every handler in question is
an ordinary read that returns stored data. The defect exists only in the
*asymmetry* between which routes carry the guard and which do not — a comparison
no static rule in Semgrep, Gitleaks, Trivy or pip-audit performs. This is the
[N.E.K.O](project-n-e-k-o-n-e-k-o.html) tautological-guard family and the
[docetl](ucbepic-docetl.html) unconfined-local-route family meeting the
[notte](nottelabs-notte.html) asymmetric-guard shape: the seam is not between two
files or two arms of one conditional, but between two *sets of routes on one
server*, one set defended and one set forgotten.

**The fix already exists in the codebase, one call away.** The most useful
sentence a report can carry is not "here is a vulnerability" but "you already
wrote the defense correctly; here are the routes that are missing the call to
it." The maintainer does not need to be convinced the check is right or design
it — it is right, it is theirs, and it is in scope. It needs to run on the read,
export and delete paths too. That framing costs no argument about threat models,
which is the property that made [N.E.K.O](project-n-e-k-o-n-e-k-o.html) and
[open-wearables](the-momentum-open-wearables.html) land.

**It is squarely on the project's own published list.** "`--tap-host`... and
remote binding behavior" and "trace redaction and export behavior" and
"generated viewer HTML that may contain private trace data" are three of the
seven scope bullets in `SECURITY.md`. The finding is not a threat model I am
importing; it is the intersection of three bullets the maintainer wrote down as
the things to worry about. That is the strongest possible
[contract-versus-artifact](vexa-ai-vexa.html) footing — the contract is the
project's own security policy, and the artifact is one guard short of honouring
it.

## What is well built

The scanners found nothing real here, and — as with
[notte](nottelabs-notte.html) and [tracecat](tracecathq-tracecat.html) — that is
not luck. Most of this codebase is careful, and the finding is a single misplaced
call in an otherwise defensive design.

**Header redaction is real and centralised.** Authorization, cookies, API-key
headers and their siblings are stripped at capture through one filter with a
frozen key set, and two keys get prefix-preserving redaction so a trace stays
diagnostic without carrying the secret. The policy's promise that "API keys are
redacted" is kept. The gap is that redaction was applied to the *header* class
and the read-path guard was not extended to the *body* class — two correct
instincts that don't quite meet.

**The DNS-rebinding defense exists at all.** This is rarer than it should be.
Most local-listener projects in this series never wrote a `Host`-header check —
[docetl](ucbepic-docetl.html) and the first draft against
[jupyter-mcp](datalayer-jupyter-mcp-server.html) both turned on the *absence* of
one. Here the check is present, correct, and even validates `Origin` port
against `Host` port. The maintainer understood the exact attack. The finding is
not "they missed DNS rebinding"; it is "they solved it and applied the solution
to one route."

**Scheme handling preserves rather than downgrades**, and the binding default is
reasoned in a comment that distinguishes the launch-locally case from the
proxy-only case rather than hardcoding one. **The control action is
double-gated** — the same-origin check *and* a per-process random token — which
is precisely the belt-and-braces treatment the read paths deserve and don't yet
get. The instinct is right; it just stopped at the door marked "state change."

## Patterns observed

**A guard is only as good as the set of routes it is wired to.** This series
keeps finding that well-built code fails at a seam, and the seams keep getting
more specific: [open-wearables](the-momentum-open-wearables.html) at the one
provider whose scheme differed, [ArcReel](arcreel-arcreel.html) where an
exemption crossed a default, [Vexa](vexa-ai-vexa.html) where a contract crossed
its artifacts, [notte](nottelabs-notte.html) between two arms of one conditional.
claude-tap adds another: **between two groups of handlers on one HTTP server,
where the group that changes state is defended and the group that reads state is
not.** The generalisation for a reviewer is a checklist item, not an intuition:
when a server has one authorization or origin check, *enumerate every route and
confirm the check runs on each one that touches sensitive data* — because the
route the developer was thinking about when they wrote the guard is rarely the
only route that needs it.

**When everything binds `127.0.0.1`, the attacker is a web page, and the defense
is a `Host` check — on the data, not just the controls.** The reflex for a
loopback service is to feel safe because nothing is exposed to the network. But a
browser the victim already has open can rebind a hostname to `127.0.0.1` and
reach the listener same-origin, and CORS never enters the picture. The right
defense is server-side `Host`-header validation, which this project has. The
lesson is the one [jupyter-mcp](datalayer-jupyter-mcp-server.html) taught from
the safe side and claude-tap teaches from the exposed side: **the check has to
stand in front of the thing worth stealing, and on a trace recorder the thing
worth stealing is the reads.**

**Redacting the secret is not the same as protecting the record.** The policy
says it, in one of the clearest sentences any `SECURITY.md` in this series has
offered: trace bodies are sensitive *even when API keys are redacted*. A tool
whose entire product is a faithful recording of your AI sessions has, as its
crown-jewel asset, the recording itself — not the credentials that happened to
ride along in the headers. Header redaction handled the credentials. The finding
is about the crown jewels.

## Notes on the tool

*Deliberately incomplete, per the withholding note above.*

**The headline is the same as it has been for the last several well-built
targets: 104 findings above the medium floor, zero real.** The one finding on
this page came from reading a route table against the project's own security
policy, and the tools did not rank it low — they had no representation for
"correct guard, wrong route set." On a careful codebase the scanner's job is to
be *quickly dismissable*, and the finding comes from a structural question asked
by hand. This is now the settled shape of the series.

**The recurring SQL cluster is the recurring SQL cluster — tenth appearance.**
The single largest bucket (37 of the 104, across two rule names) is
raw-SQL-execution warnings on the trace store. Every one of them interpolates
only SQL *clause fragments* (a `WHERE` built by the query helper, a `LIMIT`
suffix) and `?`-placeholder strings; every user-supplied value is bound as a
parameter. It is the [#1 identifier false-positive](mnemosyne-oss-mnemosyne.html)
class in its purest form, and it collapses on two reads. A curation layer that
understood "the f-string contains no value, only a placeholder count" would drop
all 37 without a human.

**pip-audit produced a file this time, and it agreed with Trivy on the one
dependency both parsed.** After a long run of empty or absent outputs, pip-audit
wrote real content — three advisories on the same directly-used async HTTP
library that Trivy also flagged from the lockfile. Two tools, one reachable
dependency, the same answer: the useful case, and worth recording precisely
because the recent story has so often been the opposite (one tool's `[]`
rendering identically to the other's real findings). The dependency tier here is
routine upgrade hygiene on a live library set — real, reachable, and a
maintenance PR rather than a disclosure.

**Same-rule flooding on GitHub Actions, again.** A large share of the mediums are
two workflow rules — unpinned mutable action tags and secrets-in-workflow-env —
firing once per matching line across the CI directory. This is the same
observation as every recent scan: both underlying points are legitimate, neither
is thirty separate observations, and the fix is to collapse each to one finding
with a count and a representative location.

## Disclosure timeline

- **2026-08-16** — Scan run at commit `901b856f`. Raw scanner outputs verified
  non-zero (semgrep 248 KB / 104 curated above the medium floor, gitleaks a
  single fixture-tier hit, trivy 51 KB, pip-audit produced content). No 0-byte /
  crash output.
- **2026-08-16** — One real finding confirmed by reading the server's route
  table against its own guard function and its own `SECURITY.md` scope.
- **2026-08-16** — Public post (this page), finding withheld at class level.
  Private disclosure to the maintainer is a manual step (PVR disabled, no
  published email); it has not yet been made.

## Reproduce

The scan is reproducible; the curation that produced the withheld finding is
described but not published as a proof-of-concept.

```bash
GIT_LFS_SKIP_SMUDGE=1 python scanner/run_scan.py \
  --from-git-url "https://github.com/liaohch3/claude-tap" \
  --reports-dir reports/liaohch3-claude-tap \
  --min-severity medium --ignore-samples
```
