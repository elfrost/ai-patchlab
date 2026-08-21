---
layout: default
title: "83 scans of AI agents and MCP servers: 10,635 findings, 56 that mattered"
description: "What four security scanners actually produce across 83 open-source AI agent and MCP projects, which findings survive curation, and the six classes of real bug no rule can see."
date: 2026-08-21
---

# 10,635 findings, 56 that mattered

*What 83 security scans of open-source AI agents and MCP servers actually found.*

Between 12 May and 20 August 2026 I scanned 83 public repositories — agent
frameworks, MCP servers, RAG pipelines, inference proxies, a robot OS, a
desktop AI companion — one commit each, same four tools every time: Semgrep,
Gitleaks, Trivy and pip-audit. Every report was generated locally. No code went
to a third party and no model was asked for an opinion.

Every scan was published the day it ran, findings and non-findings alike. This
is what the whole series says when you look at it end to end.

---

## The headline: one in 190

Across the 67 scans where both numbers were stated precisely, the tools
produced **10,635 findings**. After curation, **56** were real — a defect worth
a maintainer's attention, reachable in a deployment the project actually ships.

That is **0.53%**. One finding in 190.

| | |
|---|---:|
| Raw findings | 10,635 |
| Real findings | 56 |
| Signal rate | 0.53% |
| Scans with **zero** real findings | 34 of 67 |
| Median real findings per scan | 0 |
| Most in one scan | 6 |

Half the scans found nothing. That is not a failure of the method — it is the
method working. A tool that returns 200 findings on a well-built codebase is
not telling you the codebase has 200 problems; it is telling you it does not
know what a problem is here.

The corpus itself is bigger — 12,982 findings across 87 reports, of which
Semgrep produced 52%, Trivy 37%, Gitleaks 10% and pip-audit 0.4%. The 10,635
figure is scoped to the scans where the published write-up states both a raw
count and a curated count, because I would rather quote a smaller honest number
than a bigger inferred one.

---

## Part 1 — What the tools produce

The output is not random noise. It is a small number of very loud clusters,
and they are the same clusters in almost every repository.

**Three rule families are 52% of all Semgrep output** — 3,521 of 6,796 hits.

| Cluster | Hits | Share of Semgrep output |
|---|---:|---:|
| SQL-identifier rules (4 rules) | 1,802 | 26.5% |
| `github-actions-mutable-action-tag` | 1,341 | 19.7% |
| `logger-credential-leak` | 378 | 5.6% |

The SQL cluster is the single most persistent false positive in the series,
appearing in 46 of the 83 repositories. These rules fire when *any* part of a query
string is interpolated. In every confirmed case across the series, the data was
bound and only identifiers — table names, column names, `PRAGMA` keys — were
formatted in, which an end user cannot reach. The rule cannot tell the
difference between an interpolated identifier and an interpolated value, so it
flags both. The sharpest instance: **157 hits from a SQLAlchemy rule in a
project with no SQLAlchemy dependency at all**, firing on stdlib `sqlite3`
`PRAGMA` statements with a coerced integer — a value SQLite will not bind under
any circumstances.

**85% of secret findings are not secrets.** Gitleaks produced 1,326 hits;
1,126 of them came from the single entropy-based rule `generic-api-key`, across
52 repositories. Hand review found the overwhelming majority to be
`.env.example` placeholders, README snippets, i18n strings and test fixtures.
The best variety in the whole series was a `gcp-api-key` hit on YouTube's public
INNERTUBE web key — a genuine Google API key that youtube.com ships to every
browser that loads the page.

**Every "critical" in 83 scans came from one tool.** Trivy produced all 108
critical-severity findings; Semgrep, Gitleaks and pip-audit produced none. The
most common critical title, 16 occurrences, is *"Secrets passed via build-args
or envs or copied secret files"*. In the most recent scan, that critical was
matching on a variable **name** — an environment variable holding the
filesystem *path* to a TLS key, not the key. The word "critical" in a scanner
report is a statement about a rule's category, not about your system.

**A name-matched sweep will lie to you.** The most instructive false positive
of the series was mine, not a tool's. An AST sweep over one project's 404 routes
reported 52 as unauthenticated, including an entire 14-route router that
visibly lacked the dependency all sixteen sibling routers carried. It looked
like a textbook intra-repository differential. It was wrong: the module
imported the auth function under an alias and called it in the handler body.
378 of the 404 routes enforce auth; the 9 genuinely public ones are health,
version, robots, login and static assets. The generalisable tell is that the
project had **more than one** auth mechanism — three, in fact. Any
identifier-matching sweep over a codebase with plural auth mechanisms
under-reports, and the plurality itself is the warning.

---

## Part 2 — What the tools miss

This is the part that matters, and it is why the signal rate above is not an
argument for turning the scanners off. They are cheap and they anchor the
review. But in the scans that produced something real, the real thing was
frequently **not in the output at all**.

Three write-ups say so in as many words. In a self-evolving research agent, the
report held 39 findings and the real one was not among them; the same sentence —
*"and no tool ranked it"* — appears again on an agentic document-ETL engine. In
an MCP server, four scanner findings became six confirmed-real items, and only
one of the six came from a scanner.

Six recurring shapes account for most of what rules cannot see.

### The composite

Two individually correct decisions in two different files that compose into a
defect. No rule can see a composite, because each half is defensible where it
sits and the rule only ever looks at one file.

The clearest example: an inference server registers an `--api-key` flag,
stores it, and never reads it — the enforcing middleware exists with zero call
sites. Separately, the control server binds `0.0.0.0` by default. Either
decision alone is arguable. Together they are ~40 unauthenticated routes
including a weight-transfer group, on a project whose own quickstart passes
`--host 0.0.0.0` three times.

### The inert flag

A security control that is declared, documented, and never invoked. Grep finds
the flag and concludes the protection exists. The test is to count *consumers*
of the flag and *call sites* of the enforcing symbol — defined-and-never-called
is the stronger half of the evidence.

The inverse also happens and is worth crediting: a mode that defaults off is
**not** an inert flag if the other branch sets an explicit fallback and a
migration declares the rollout. I have been wrong in that direction too.

### Verify-then-branch, inverted

An authentication check placed inside a condition the caller controls. Two
webhook channels verified their signature only when a caller-supplied flag
asked them to — `if encrypt and self._crypto` rather than `if self._crypto`.
The fix inverts the conditional and returns 403 when the flag is absent. A
passer-by contributor reproduced the bypass on both channels and shipped it
with nine regression tests. No tool in the series ranked it.

### The contract the artifacts break

A project declares a configuration value as mandatory, enforces it correctly in
code, and then ships deployment artifacts that all supply a default — so the
check can never fire. One project's config schema marks its internal API secret
as `required-explicit` and cites the exact incident that motivated the rule;
compose, the lite Makefile and the Helm chart each supply a literal.

The generalisation: **N deployment paths are N chances to diverge**, and where
there is no stated contract, the majority sibling *is* the contract. One
project prefixed `127.0.0.1:` on all eleven published ports in its compose file
and on none in its lite Makefile. That eleven-to-zero contrast is the evidence.

### The install path nobody audited

Two dependency scanners disagreed on one project: Trivy read the lockfile and
reported 63 advisories, 36 of them high; pip-audit resolved the declared
version floors and reported zero across 73 dependencies. Both were correct.
They read different files, and the project ships both as real install paths —
the README's recommended one-liner runs `uv sync` against the pinned lockfile,
while the Dockerfile never reads the lock at all and installs current releases
from the floors.

The containerised deployment was clean and the recommended host install was
not, from the same commit. **When two tools disagree, do not reconcile them —
ask which install path each one described.** The maintainer bumped the pinned
package in the lockfile about six hours after the issue was filed, deliberately
upgrading that one package rather than the whole lock so as not to drag three
major-version jumps in with it.

### The absence

The finding that is a missing control rather than a present bug: no rate limit,
no Origin check on a WebSocket handshake, no lockfile so "not scanned" renders
identically to "clean". Rules match on things that exist. Nothing in a static
ruleset can flag the guard that was never written.

---

## Part 3 — Publishing the negatives

Thirty-four of sixty-seven scans found nothing real, and every one of them was
published saying so.

That is not modesty, it is the load-bearing part. **A method that can only
return "yes" is not a method.** If every write-up in the series ended in a
finding, the correct inference would be that the series manufactures findings.
The clean scans are what make the other 33 worth reading.

Some of the negatives were expensive. On one scan the strongest lead ran like
this: a function treats any `chrome-extension://` origin as trusted-local
without pinning the project's own extension IDs, which clears a path to the
admin endpoint — and the project's **own design document** lists "do not treat
the browser-provided extension origin as an identity credential" under
non-goals, and records that the enforcement was deleted with no migration.
Stated non-goal, deleted enforcement, live path doing the forbidden thing. It
looked certain.

It is not exploitable. Four lines further down, the same function ends with
`if not origin: return True` — a loopback caller sending no Origin header is
trusted anyway, so forging an extension origin buys nothing. The lesson is
narrow and useful: **a design-doc non-goal is an oracle for intent, not for
reachability.** It tells you what the authors meant to forbid, not whether the
forbidden thing grants privilege. Finish reading the function before believing
the document.

A large share of the curation effort goes into the opposite of finding things.
At least 24 of the 83 write-ups explicitly credit a defence that a scanner had
flagged as a vulnerability. The best-defended auth layer in the series produced
two frightening results, and both were defences: an unverified-JWT-decode that
turned out to be a textbook two-pass verification, and a hardcoded bcrypt hash
that turned out to be a constant-time dummy for the no-user-matched path — one
that is genuinely invoked, which I checked before believing it.

---

## What maintainers actually did

Seventeen findings were fixed. When a report lands well, it lands fast:

- one project shipped the fix about six hours after the issue was filed, and
  cut a release nine minutes after closing it
- another merged ~14 hours later, another the same day, another in ~5 days
- the slowest was ~11 days, a silent merge after CI review

Two were fixed by people other than me. In one case a passer-by contributor
adopted a filing concrete enough to act on and wrote the patch themselves; in
another the maintainer wrote their own diff because my pull request was blocked
behind a contributor licence agreement that expired, and said so explicitly in
the release notes. **The residual blocker can be legal rather than technical** —
worth checking for a CLA bot before writing the patch, not after.

---

## What I would change about the tools

Not "add more rules". The rules are not the constraint.

1. **Report coverage, loudly.** Semgrep's `errors` array — not `paths.skipped`
   — is where a rule that failed to run on a file shows up. Across the whole
   series `paths.skipped` was empty on *every* run where rules timed out. In
   the sharpest instance, both subprocess-injection rules timed out on the
   20,000-line file that was the entire API surface: the rules that mattered,
   on the file that mattered, and the report looked complete. A scan that did
   not run is not a clean scan, and the two must never render identically.

2. **Name the install path.** A single merged dependency verdict is wrong for
   at least one of a project's own users whenever it ships both a lockfile and
   open version floors. Report them as separate rows.

3. **Check rule applicability.** A SQLAlchemy rule should not fire 157 times in
   a project with no SQLAlchemy dependency. The manifest is right there.

4. **Grade the match, not just the pattern.** A provider-format placeholder is
   still a placeholder. Confidence should key on the matched text, not only on
   which rule fired.

The first, second and fourth are now implemented in
[AI PatchLab](https://github.com/elfrost/ai-patchlab). Applied retroactively to
this corpus, the confidence changes alone move roughly half of all Semgrep
findings and 93% of Gitleaks hits out of the top-ranked block — not deleted, just no longer
competing for attention with the things that turned out to be real.

---

## The short version

The scanners are a net, not a detector. They are worth running: cheap,
deterministic, and they occasionally catch the thing directly. But across 83
projects the ratio was one in 190, half the scans ended in nothing, and the
findings that mattered most were frequently composites, absences, or
divergences between two files that were each individually correct.

That gap is not a tooling problem to be solved by better rules. It is reading.

---

*Every scan in this series, with its full write-up:
[the scan log]({{ '/' | relative_url }}). Methodology, tooling and reports are
open source at [github.com/elfrost/ai-patchlab](https://github.com/elfrost/ai-patchlab).*

*Want this run privately against your own codebase?
[Work with me →]({{ '/work-with-me' | relative_url }})*
