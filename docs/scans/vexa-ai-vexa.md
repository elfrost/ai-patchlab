---
layout: default
title: "Vexa-ai/vexa: security scan"
description: "Security scan of Vexa-ai/vexa: 297 findings (270 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-05
---

# Vexa-ai/vexa — security scan

**Repository:** [Vexa-ai/vexa](https://github.com/Vexa-ai/vexa)
**Commit scanned:** `1f6898cf`
**Scan date:** 2026-08-05
**Disclosure status:** withheld — one real finding held for private disclosure;
the project's `SECURITY.md` directs reports to email, and the GitHub private
advisory API is returning `500` for this repository (see *Channel* below)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 16 |
| High | 65 |
| Medium | 189 |
| Low | — |
| Info | — |

**Total findings:** 297 raw / 270 at `--min-severity medium` (1 real after
curation — withheld)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

## The project

Vexa (2.6k★, Apache-2.0) is an **open-source, self-hosted meeting bot and
transcription API**. Bots join Google Meet, Microsoft Teams and Zoom calls,
stream transcription in real time over WebSockets, and feed a workspace that is
a git repository of Markdown the operator owns. Around that sits a genuinely
large system: a gateway, an identity service, a meeting service, an agent
control plane, a runtime kernel, a Next.js terminal UI, a dashboard, an MCP
server, browser and terminal clients, and three separate deployment paths —
Docker Compose, a single-container "lite" image, and a Helm chart for
Kubernetes and OpenShift.

It is a **FINOS incubation project** tracking the
[OSPS Baseline](https://baseline.openssf.org/) at Maturity Level 2, with a dated
self-assessment committed in the repository (2026-07-02, 28 passed / 0 failed).
Maintenance is real and concentrated: 36 of the 40 pull requests merged in the
last 60 days come from the lead maintainer, with two other contributors, and 30
issues closed in the same window.

## Channel, and what this write-up does not contain

Vexa's `SECURITY.md` is explicit: *"Please do not report security
vulnerabilities through public GitHub issues, discussions, or pull requests."*
It names an email address, offers to copy FINOS, commits to a five-business-day
acknowledgement, and describes a coordinated-disclosure process. That is a hard
post-only signal, and it means the finding is withheld from **this page** as
well — not merely kept out of an issue.

The repository also has **private vulnerability reporting enabled**, which would
normally let this pipeline file the report end-to-end with no human step. It
did not work here. `POST /repos/Vexa-ai/vexa/security-advisories/reports`
returned **HTTP 500 with an empty body on four consecutive attempts**, with a
token carrying the scopes that have worked elsewhere. This is the third distinct
state this series has now recorded for the private channel:

| State | What it means | Seen on |
| --- | --- | --- |
| (a) PVR disabled | email only; the advisory link in `SECURITY.md` is unreachable | rocketride |
| (b) PVR enabled, API accepts | filed autonomously, no human step | Observal, ArcReel |
| (c) PVR enabled, API `500`s | web form or email only — a human must send it | repowise, **Vexa** |

State (c) is worth naming because from the outside it is *indistinguishable*
from state (b) until you actually attempt the POST. The
`private-vulnerability-reporting` endpoint reports `{"enabled": true}` in both.
Probing the toggle is not the same as probing the channel, which is why the
rule here is to attempt the submission rather than infer from configuration.

So this page describes the **shape** of the finding and the reasoning that
produced it, with the components, the mechanism, the constants and the
reproduction left out.

One consequence stated plainly, as on previous withheld scans: **the tooling
section below is deliberately incomplete.** Publishing an exhaustive "here is
every bucket and why each is dismissable" list would identify the withheld item
by subtraction. What is listed is real and accurate; it is not the whole list.

## The one real finding, at class level

Every individual decision involved in this finding is defensible, and several
are better than what most projects in this series ship. The finding is what they
add up to.

The project maintains a **machine-readable declaration of its own configuration
requirements**, in which certain keys are marked as *must be set explicitly* —
with a written rationale, tied to a dated production incident, explaining that a
missing value must cause the service to **refuse to boot** rather than start
successfully and then reject every request. The enforcement code for this exists
and is correct. Its own documentation states that the developer-convenience
toggle does not relax it.

The shipped deployment artifacts supply a literal value for one of those keys.
All of them do, by different mechanisms. The consequence is that the
refuse-to-boot check can never fire on any path an operator would actually use,
and the value it settles on is a constant that is readable in the public
repository. On one of the three deployment paths, the surface that value
protects is additionally reachable from further away than on the other two — and
the reason that reads as an oversight rather than a decision is that the *same
project*, in a *sibling file*, does the restrictive thing consistently and
correctly.

Three properties made this worth reporting rather than filing under
best-practice noise:

**No rule can see it.** The check is correct. Each default is, in isolation,
ordinary out-of-the-box convenience. The declaration is correct. The defect
exists only in the relationship between a contract and the artifacts that are
supposed to satisfy it — which is a comparison no static rule in any of the four
tools performs. It is not that the tools ranked it low; they did not represent
it at all.

**The project's own contract is the oracle.** This is the same move that
converted a "looks wrong" into an "is a defect" on
[rocketride](rocketride-org-rocketride-server.html), where a function's docstring
documented the opposite of what it did. Here the contract is not prose but a
committed, machine-readable declaration with an explicit class field — so the
mismatch between "this key must be set explicitly" and "every shipped artifact
sets it for you" is not a judgement call. It forecloses the by-design rebuttal
before it is made.

**The fix already exists in the codebase, applied elsewhere.** The most useful
thing a report can say is not "here is a vulnerability" but "you already wrote
this correctly five times; here is the sixth place." The idiom that would
enforce the requirement is used repeatedly in the same directory for
less-sensitive configuration. The patch is one line in the project's own style,
plus a regression test that the existing machine-readable contract makes
straightforward to write.

The report also proposes that test explicitly, because the durable fix is not
the one line — it is the assertion that no shipped deployment artifact may
supply a value for a key the contract classes as must-be-set-explicitly. That
generalises past this instance.

## What is well built

Enough of this codebase is careful that the interesting question was never
"where is the sloppy code" — there is very little — but "where do two careful
things meet."

**The privileged client surface is gated properly, and hidden rather than
refused.** The terminal's admin routes verify the caller before proxying,
return `404` rather than `403` to non-admins so the surface does not advertise
itself, never let the server-side credential reach the browser, and refuse to
serve at all when their upstream is unconfigured instead of degrading to
something permissive.

**Identity is resolved by an oracle, not derived from client-sendable data.**
The server treats a single verified lookup as the only identity it trusts, and
the codebase carries an explicit written note that the companion display cookie
is *display-only* — with the reasoning spelled out: `httpOnly` prevents
JavaScript reads but not a hand-crafted `Cookie` header, therefore nothing
security-relevant may ever be derived from it. That is a distinction a great
many projects get wrong, and it is documented at the point of use rather than in
a wiki.

**Secret comparisons use `hmac.compare_digest` consistently**, and the internal
checks are re-asserted at each endpoint rather than assumed from a middleware
layer — with a comment noting that the check must hold whether the request
arrives directly or through the proxy.

**The rate-limiting and IP-guard layer is reasoned about out loud.** The
exclusion list carries a comment explaining that the underlying library matches
paths by *prefix*, so a bare `/` entry would match every path and silently
neuter the entire guard — and that the root route is therefore deliberately not
excluded. Elsewhere the integration explains which of the library's features are
turned off because the project ships its own, and keeps them off so a future
addition cannot double up. Body-scanning is off with a stated reason: the
gateway proxies arbitrary user text, and signature-based scanning would
false-positive on legitimate transcript content.

**Supply-chain and process discipline is above the series average.** A
third-party source archive is fetched by pinned version *and* verified against a
committed SHA-256 before use, with a comment requiring the hash be updated in
lockstep. Contracts are golden-file tested. There is an ADR directory, a
`db-budget.json` capturing connection-pool limits learned from a dated outage,
and the OSPS Baseline self-assessment is committed rather than claimed.

A recurring quality throughout: **comments cite the incident that motivated the
code**. Several defensive branches carry a date and an issue number explaining
the failure they exist to prevent. That is unusual, it is genuinely useful, and
it is what made the withheld finding findable — the code states its intent
precisely enough that you can check whether the deployment honours it.

## Patterns observed

**"Well built" and "correct" are not the same property, and the gap is where
composites live.** This is now the second consecutive scan where the real
finding lives between two files that are each right —
[ArcReel](arcreel-arcreel.html) was a documented, build-enforced exemption
crossing an unrelated shipped default. Vexa is a machine-readable requirement
crossing the artifacts meant to satisfy it. In both cases the individual
reviewer of either file would sign it off, and correctly. The generalisation:
on a codebase with few defects, stop reading files and start reading *pairs* —
specifically, pairs where one file states a requirement and another decides
whether it is met. Those pairs are enumerable, and there are far fewer of them
than there are files.

**A machine-readable contract is a security asset, and this is the argument
for writing one.** The reason this finding is a defect rather than an opinion is
that the project itself declared, in a committed file with a typed class field,
what the requirement was. Projects that keep that knowledge in prose — or in a
maintainer's head — make the same class of mistake unfalsifiable from outside.
The irony is exact: Vexa is more auditable than its peers *because* it wrote the
contract down, and the finding is that an artifact contradicts the contract. A
project with no contract would have had the same defect and no way to
demonstrate it.

**Three deployment paths is three chances to diverge.** Compose, a
single-container image, and a Helm chart all have to independently satisfy the
same requirements, and nothing checks that they agree. The general lesson for
this series is that when a project ships N deployment paths, the security
question is not "is the default safe" but "do the N defaults agree, and does
anything verify that they do?" The answer is almost always no, and divergence
between siblings is a strong signal of oversight rather than intent — which is
precisely what makes it reportable rather than arguable. This is the same
intra-repo differential that made the [N.E.K.O](project-n-e-k-o-n-e-k-o.html)
report land: *you already wrote this fix elsewhere* is a framing maintainers act
on, because it costs them no argument about threat models.

**Attempt the channel; do not infer it.** The `500` here would have been
invisible to any amount of configuration probing. `{"enabled": true}` was
returned by the same endpoint that returns it for repositories where the
submission works. The general rule this series now follows — probe the toggle
*and* attempt the POST — exists because those two facts are independent, and
only one of them is observable without trying.

## Notes on the tool

*Deliberately incomplete, per the withholding note above.*

**pip-audit produced no output file at all — the fourth consecutive scan.**
This now spans PipesHub, Observal, open-wearables and Vexa. Its
`not-installed` / `scan-error` meta finding is `info` severity, so
`--min-severity medium` filters it out and the report renders a Python
dependency surface of *zero* identically to one that was never analysed. On a
repository with multiple `uv.lock` files across separate service directories,
that is a large silent gap. **Exempting scanner-infrastructure meta findings
from `--min-severity` is now the top backlog item by a wide margin — this is
its eighth vote.** A scan cannot honestly report a clean dependency surface it
did not measure. Trivy did carry the dependency load here (a routine but real
tail: Next.js SSRF and DoS advisories, two Auth.js criticals, PostCSS path
traversal, `sharp`/libvips, `uuid`, `aiohttp`, `cryptography`,
`brace-expansion`), which is the only reason the gap was not total — and is a
second data point for the *report tool disagreement, do not union it* note from
the previous scan.

**Same-rule flooding, third vote in three scans.** 92 of the 189 mediums —
nearly half the entire medium tier — are a single GitHub Actions rule about
mutable action tags, firing once per `uses:` line across the workflow
directory. Following open-wearables (36 in one file) and ArcReel (34 of 43),
this is a settled pattern: one rule that matches a repo-wide convention drowns
the tier it lands in. These should collapse to one finding with a count and a
representative location. The underlying observation is legitimate — the actions
here are pinned to tags rather than commit SHAs, which for a project tracking
OSPS Baseline is a real if minor gap — but it is *one* observation, not 92.

**A systemic container-hardening item the count buries:** 15 of 15 Dockerfiles
in the repository run as `root`, with no `USER` directive. Scattered across 15
separate high-severity findings it reads as noise; stated once as "no image in
this project drops privileges" it is a coherent hardening recommendation worth
a maintainer's attention. This is the inverse of the flooding problem —
same-rule collapse would help here too, but the collapsed form is *more*
actionable, not less.

**Reachability annotation remains the highest-value missing feature.** The
critical and high tiers are dominated by npm advisories against the two
Next.js client surfaces. Sorting "reachable in shipped code" from "present in a
lockfile" is still entirely manual, and it is the single largest consumer of
curation time on every scan in this series.

## Disclosure timeline

- **2026-08-05** — Scan run at commit `1f6898cf`. Raw scanner outputs verified
  non-zero (semgrep 719 KB, gitleaks 6 KB, trivy 784 KB); pip-audit produced no
  output file and its meta finding was filtered by `--min-severity medium`.
- **2026-08-05** — Private advisory submission attempted via the GitHub API;
  `HTTP 500`, empty body, four consecutive attempts. Channel recorded as
  state (c).
- **2026-08-05** — Public post (this page), finding withheld. Private
  disclosure to the address in `SECURITY.md` pending.

## Reproduce

The scan is reproducible; the curation that produced the withheld finding is
not published.

```bash
GIT_LFS_SKIP_SMUDGE=1 python scanner/run_scan.py \
  --from-git-url "https://github.com/Vexa-ai/vexa" \
  --reports-dir reports/vexa-ai-vexa \
  --min-severity medium
```
