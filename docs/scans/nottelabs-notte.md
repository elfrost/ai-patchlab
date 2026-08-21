---
layout: default
title: "nottelabs/notte: security scan"
description: "Security scan of nottelabs/notte: 226 findings (206 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-06
---

# nottelabs/notte — security scan

**Repository:** [nottelabs/notte](https://github.com/nottelabs/notte)
**Commit scanned:** `255d11b5`
**Scan date:** 2026-08-06
**Disclosure status:** withheld — one real finding filed privately as
[GHSA-w5rf-44xh-5rq7](https://github.com/nottelabs/notte/security/advisories/GHSA-w5rf-44xh-5rq7),
embargoed pending maintainer response

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 3 |
| High | 83 |
| Medium | 120 |
| Low | — |
| Info | — |

**Total findings:** 226 raw / 206 at `--min-severity medium` (1 real after
curation — withheld; **zero** of the 206 scanner findings survived)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

## The project

Notte (2.0k★, SSPL-1.0) is a **framework for building reliable web-automation
agents**. You give it a goal in natural language; it drives a real browser
through Playwright, converts each page into a structured representation the
model can reason over, and executes the actions the model picks. It is a
six-package monorepo — core, browser, agent, LLM, SDK, integrations — plus a
CLI, a workflow runtime, and a hosted control plane at `console.notte.cc`.

Maintenance is real and concentrated: 23 pull requests merged in the last 60
days from three maintainers, with outside issues getting closed. There is no
`SECURITY.md` at any of the three standard locations, but **private
vulnerability reporting is enabled** — which is the signal that mattered here.

## Channel, and what this write-up does not contain

Private vulnerability reporting is off by default on GitHub. Turning it on is a
deliberate act, and this series now treats it as **signalled consent to a
private channel that outranks a missing policy file** — the rule adopted after
[ArcReel](arcreel-arcreel.html), which was the same configuration.

The submission was accepted on the first attempt. That makes notte the **third
autonomous private filing** in this series, and the third data point for the
three-state channel model:

| State | What it means | Seen on |
| --- | --- | --- |
| (a) PVR disabled | email only; the advisory link is unreachable | rocketride |
| (b) PVR enabled, API accepts | filed autonomously, no human step | Observal, ArcReel, **notte** |
| (c) PVR enabled, API `500`s | web form or email only — a human must send it | repowise, Vexa |

Because the report is under embargo, this page describes the **shape** of the
finding and the reasoning that produced it. The component, the symbols, the file
paths, the constants and the reproduction are left out. The proof-of-concept
script exists and was run; it is not published.

One consequence stated plainly, as on every withheld scan in this series: **the
tooling section below is deliberately incomplete.** An exhaustive "here is every
bucket and why each one is dismissable" list would identify the withheld item by
subtraction. What is listed is accurate; it is not the whole list.

## The one real finding, at class level

The class is **an asymmetric guard inside a single function**.

Two classes of sensitive value flow through the same code path. One of them is
bound, correctly, to the context that makes releasing it safe — and when that
context does not match, it fails closed with an explicit error. The other class
is not bound to anything. The two lookups are adjacent lines of the same
`if`/`else`. The unbound class is the more sensitive of the two, and the public
API offers **no parameter with which a user could bind it** even if they
understood the exposure and wanted to.

Standing in front of the unbound path is one check. Every input that check
consults is supplied by the untrusted side of the boundary. It is a good check
that the *right element* was chosen; it is not a check that the *right party* is
asking. That is the [tautological-guard](project-n-e-k-o-n-e-k-o.html) shape
again, in its third costume: *what value would fail this check, and who gets to
choose that value?*

Three properties made it worth reporting rather than filing under best-practice
noise:

**No rule represented it.** Not ranked low — absent. All four tools produced
206 findings above the medium floor and **none of them described this**. There
is no dangerous function here, no injection sink, no missing `check=`. Both
branches are ordinary attribute lookups. The defect exists only in the
*asymmetry between them*, which is a comparison no static rule in Semgrep,
Gitleaks, Trivy or pip-audit performs.

**The fix already exists in the codebase, on the adjacent line.** The most
useful sentence a report can contain is not "here is a vulnerability" but "you
already wrote this correctly, immediately next to the place it is missing." The
sibling branch does the exact thing the vulnerable branch omits, in the same
function, with the same variable already in scope. That framing costs the
maintainer no argument about threat models, which is why
[N.E.K.O](project-n-e-k-o-n-e-k-o.html) and
[open-wearables](the-momentum-open-wearables.html) both landed on it.

**The differential is the proof.** The report does not assert that the
behaviour is wrong; it demonstrates that the *same component, in the same
state, in the same call* refuses one value and releases the other. A maintainer can
disagree with a threat model. It is much harder to disagree with the project's
own code doing the safe thing eight lines away. This is the
[docstring-oracle move](rocketride-org-rocketride-server.html) with the code
itself as the oracle instead of prose — and it forecloses the by-design
rebuttal before it is offered, because "by design" would have to explain why
the design applies to one branch and not its neighbour.

Running the primitive mattered here, as it did on
[Observal](observal-observal.html). The finding was legible from reading, but
reading could not distinguish "the real value is released" from "a masked stand-in
is released" — the intermediate type deliberately hides itself in `repr()`. Only
executing it showed the literal string that reaches the far side. A report that
had guessed would have been coherent and wrong in the one detail that decides
severity.

## What is well built

The scanners found nothing real in this codebase, and that is not an accident of
the ruleset — most of it is careful.

**The user-script runtime is a real sandbox, and it defaults to on.** Workflow
scripts compile through `RestrictedPython` with a policy subclass that tightens
the default further, and unrestricted compilation is an explicit opt-in
parameter rather than the fallback. This is the [advertised-boundary
test](agentera-agently.html) passed rather than failed: the sandbox exists, is
enforced, and the code it guards is the user's own — so the honest threat model
and the implemented one agree.

**One lockfile for six packages.** A monorepo is normally where dependency drift
hides — [Kiln](kiln-ai-kiln.html) and
[open-wearables](the-momentum-open-wearables.html) both turned on splitting the
lockfiles before splitting the severities. Notte resolves all six packages
through a single root `uv.lock`, so there is no drift to find and no
sub-project quietly running a two-year-old resolver output.

**Scheme handling preserves rather than hardcodes.** The one place the code
derives a WebSocket URL maps `https://`→`wss://` and `http://`→`ws://`, so it
inherits the transport security of whatever base URL it was given instead of
pinning a plaintext scheme. A rule flagged the `ws://` literal; reading the line
shows it is the *mirror* of the secure branch, not a downgrade.

**Errors are written for three audiences.** The error hierarchy carries separate
developer, user and agent messages, so what gets surfaced to a model is a
deliberate choice at the point of raise rather than whatever the stack trace
happened to contain. That is an unusually thoughtful piece of plumbing in a
codebase whose consumer is a language model.

## Patterns observed

**A guard can be correct about the noun and silent about the context.** Every
scan in this series that found something in well-built code found it at a
seam — [open-wearables](the-momentum-open-wearables.html) at the one provider
whose scheme differed, [ArcReel](arcreel-arcreel.html) where an exemption
crossed a default, [Vexa](vexa-ai-vexa.html) where a contract crossed its
artifacts. Notte adds a fourth shape and the tightest one yet: **the seam is
inside a single function, between two arms of one conditional.** The
generalisation is getting sharper each time — when a function handles N
categories of the same sensitive thing, enumerate the categories and check that
each one passes through *every* gate, not just the gate that its own type
suggested. Asymmetry between siblings is the signal, and the closer the siblings
sit, the less likely the asymmetry was intentional.

**Ask what the guard's operands are controlled by, not what the guard tests
for.** The check in front of the unbound path is well written and does what its
name says. It is defeated not by evading it but by *satisfying* it, because
everything it reads comes from the party it is meant to constrain. This is now
the third instance of the tautological-guard class in this series, and the
common tell is unchanged: the check reads its inputs from the same side of the
boundary it is defending.

**Reachability, not version-matching, is the whole story in the dependency
tier — and it collapsed the entire critical tier here.** All three criticals are
unreachable, by two different mechanisms. Two are LiteLLM advisories describing
**Proxy Server** features — OIDC cache-key collisions, admin key generation,
user-role modification, host-header handling on the management API. Notte
imports LiteLLM as a client SDK (completion calls, exception types, a response
model) and never starts the proxy, so the vulnerable surface is code it does not
run. This is the same finding as
[code-graph-rag](vitali87-code-graph-rag.html) in reverse: there the transport
*was* live, so the CVEs *were* real. The third critical is an Authlib
authentication bypass — and Authlib appears in the lockfile only because an
**optional integrations dependency** pulls it in. The two apparent references to
that dependency in shipped code are an attribution comment and an unrelated
string constant. **Version-match to reachable to actually-shipped is three
gates, and the critical tier failed at gate two or three in every case.**

**A monorepo can be the good news.** The counting failure this series usually
reports on multi-package projects is over-count via vendored code
([harbor](harbor-framework-harbor.html)) or under-count via unscanned lockfiles
([open-wearables](the-momentum-open-wearables.html)). Notte is the control case:
one lockfile, one resolution, 135 dependency findings that all describe the same
real dependency set. The count was still misleading — but by *reachability*, not
by attribution, and that is a much easier problem to reason about.

## Notes on the tool

*Deliberately incomplete, per the withholding note above.*

**The headline number is the story: 206 findings above the medium floor, zero
real.** Not "mostly false positives with a couple of real ones underneath" —
zero. The one finding on this page came from reading a function, and the tools
did not rank it low, they had no representation for it. That is the strongest
argument yet for the direction this series keeps pointing at: on a well-built
codebase the scanner's job is to be *quickly dismissable*, and the finding comes
from a structural question asked by hand.

**pip-audit produced a file this time — and it was empty.** After four
consecutive scans where it produced no output at all, it wrote `[]` here. That
looks like recovery and is worth being precise about: an empty array on a
project whose root `uv.lock` Trivy mined for 135 advisories is not agreement,
it is a second way of reporting nothing. The renderer cannot distinguish "no
Python advisories" from "no Python dependency surface analysed." **Exempting
scanner-infrastructure meta findings from `--min-severity` remains the top
backlog item — ninth vote** — and this scan adds a corollary: the report should
also surface *tool disagreement* on the same target, because one tool finding
135 advisories where another finds zero is a fact about the tools that a union
or an intersection both destroy.

**Same-rule flooding, fourth vote in four scans.** 54 of the 120 mediums are two
GitHub Actions rules — 31 for mutable action tags and 23 for secrets in workflow
env — firing once per matching line across the workflow directory. Following
[open-wearables](the-momentum-open-wearables.html) (36 in one file),
[ArcReel](arcreel-arcreel.html) (34 of 43) and [Vexa](vexa-ai-vexa.html) (92 of
189), the pattern is settled and the fix is unambiguous: collapse to one finding
with a count and a representative location. Both underlying observations are
legitimate; neither is 31 or 23 observations.

**All 28 gitleaks hits are fixture-tier, and the fixture tier now needs a
sub-category.** Most sit in saved third-party HTML pages used as offline test
data — real API keys, belonging to *other people's* websites, captured
incidentally by archiving a page. That is not a leak by this project, but it is
also not the same thing as a placeholder in `.env.example`, and a scanner that
called it "third-party content captured in a fixture" would be more useful than
one that calls it `generic-api-key`. **Eighth vote** for the fixture tier,
first with this wrinkle.

## Disclosure timeline

- **2026-08-06** — Scan run at commit `255d11b5`. Raw scanner outputs verified
  non-zero (semgrep 333 KB / 63 results, gitleaks 24 KB / 28 results, trivy
  594 KB / 135 vulnerabilities); pip-audit wrote an empty array.
- **2026-08-06** — Finding confirmed by executing a proof-of-concept against
  the installed package rather than by reading alone.
- **2026-08-06** — Filed privately via the GitHub advisory API, accepted on the
  first attempt:
  [GHSA-w5rf-44xh-5rq7](https://github.com/nottelabs/notte/security/advisories/GHSA-w5rf-44xh-5rq7)
  (state: triage).
- **2026-08-06** — Public post (this page), finding withheld under embargo.

## Reproduce

The scan is reproducible; the curation and the proof-of-concept that produced
the withheld finding are not published.

```bash
GIT_LFS_SKIP_SMUDGE=1 python scanner/run_scan.py \
  --from-git-url "https://github.com/nottelabs/notte" \
  --reports-dir reports/nottelabs-notte \
  --min-severity medium
```
