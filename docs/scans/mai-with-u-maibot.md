---
layout: default
title: "Mai-with-u/MaiBot: security scan"
description: "Security scan of Mai-with-u/MaiBot: 373 findings (373 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-19
---

# Mai-with-u/MaiBot — security scan

**Repository:** [Mai-with-u/MaiBot](https://github.com/Mai-with-u/MaiBot)
**Commit scanned:** `209cb31f` (main at scan time; v1.2.0)
**Scan date:** 2026-08-19
**Disclosure status:** **withheld** — one real finding, reported privately
through GitHub private vulnerability reporting as `GHSA-h5j9-vhc8-6m67`,
accepted into triage on the first attempt. Described here at class level only.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 201 |
| Medium | 170 |
| Low | — |
| Info | — |

**Total findings:** 373 above the medium floor (1 real after curation —
**withheld**; **zero** of the 373 scanner findings represented it).

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

## The project

MaiSaka is a digital lifeform, and the README means that more literally than the
genre usually does. She is an LLM agent who lives in your group chats — QQ
through NapCat, and other platforms through adapters — and the project's stated
goal is explicitly *not* efficiency. The description says she "does not pursue
perfection, nor does she seek efficiency; instead, she values warmth,
authenticity, and genuine connection." She reaches out first. She has moods,
expressions she learns from the people around her, a jargon table for
group-specific slang, and a memory subsystem that keeps episodes rather than
transcripts.

5.8k stars, GPL-3.0, eighteen months old, and busy: 37 merged PRs from 9
distinct authors and 38 closed issues in the last 60 days. It ships a Vite +
Electron dashboard, a plugin marketplace with git-backed installation, an MCP
module, and a FastAPI WebUI with **404 registered routes**.

That route count is the reason this scan is interesting. It is the largest
per-route authorisation surface the series has looked at, on a project whose
users are overwhelmingly hobbyists self-hosting a bot for their friends.

## What this write-up does not contain

The one real finding is with the maintainers privately and is not fixed at time
of writing, so this page describes its **class** and nothing that would let a
reader reconstruct it. No file, no function, no endpoint, no header, no
reproduction. When the advisory resolves I will publish the detail here, as I
did for [huangruiteng/loopx](huangruiteng-loopx.html).

The class: **a protective control that works exactly as designed, and that an
unauthenticated caller can arrange not to be subject to.** Not a missing check —
the check is present, it is reached on every relevant request, and against an
ordinary caller it behaves correctly. The defect is upstream of the logic, in
what the control treats as authoritative about the caller. Nothing about the
enforcement is wrong; it is simply pointed at something the caller gets to
decide.

What made it reportable rather than a hunch is that **the correct version of this
exact decision already exists in the same repository**, roughly five hundred
lines away, in a module written by the same project for a neighbouring purpose —
with a comment in the code explaining the precise subtlety that the other copy
misses. Two implementations of one rule; one of them is right; the one guarding
the more sensitive door is not. That is the
[intra-repo differential](project-n-e-k-o-n-e-k-o.html) again, and it is the
sixth time in this series that the strongest argument in a report has been the
project's own prior work rather than anything I brought.

I also included a secondary item from the shipped deployment file, flagged as
lower confidence and explicitly labelled as something the maintainers may
consider out of scope.

## The differential that decided it

I have written before that
[a probe must be able to return "no"](tracecathq-tracecat.html), and this one
nearly did. The finding only survived because I built the check as a
**differential against the project's own code** rather than as an argument about
it.

I loaded the relevant module unmodified out of the clone — stubbing exactly one
logging import so it would run standalone, and changing nothing else — mounted
the project's real dependency in a throwaway app, and drove two clients through
identical request sequences. The two clients differed in one respect only.

The first client was stopped by the control promptly and correctly. **That
result is half the report.** It proves the control is genuinely implemented and
genuinely enforced, which is what separates this from the much weaker claim that
protection is absent. The second client, differing only in the one respect, was
never stopped at all, across 500 consecutive attempts.

Same code, same endpoint, same count, one difference. That is a finding I can
hand to a maintainer without asking them to take my reasoning on faith — they
can paste it and watch it happen. It is also the fifth time the
[run-the-exploit-primitive](evoscientist-evoscientist.html) discipline changed
what I filed: my first pass through this codebase produced a *different*,
larger, and completely wrong finding, described below.

## The wrong finding I nearly filed

Worth recording in full, because the failure mode is one an automated pass will
hit repeatedly.

An AST sweep over all 404 routes looking for an auth dependency returned **52
routes with no visible protection**, including an entire router covering upload,
patch, delete and batch-delete. That reads like a serious authorisation gap, and
it is the exact shape — a guard applied to some handlers of one interface and
not others — that produced a real finding against
[loopx](huangruiteng-loopx.html).

It was wrong. The module in question imports its auth helper **under an alias**
and calls it in the handler body rather than declaring it as a dependency. Every
one of those routes is authenticated. My sweep matched on the canonical name and
the alias defeated it.

Then the corrected sweep — now also matching in-body calls — still returned 26,
and the survivors included a token-issuing endpoint and a WebSocket entry point,
both of which look alarming in a list. Reading them killed both: the
token-issuing endpoint verifies the session before issuing anything and returns
a non-error status purely so the login page does not thrash, and the WebSocket
authenticates in the handshake. One handler in the flagged set uses a visibly
different, conditional-looking pattern; reading it showed it is the fail-closed
form, initialising to invalid, checking two credential sources, and raising if
neither matched.

**A route inventory is a list of questions, not a list of findings**, and the
distance between those two things was 24 false positives out of 26 candidates
here. The generalisable lesson is narrower and more useful than "read the code":
**an identifier-matching sweep over a codebase with more than one auth mechanism
will silently under-report**, and the tell is that the mechanisms are plural at
all. This project has three — a router-level dependency, a decorator-level
dependency, and an in-body call under an alias — and any sweep that knows about
two of them produces a confident, wrong answer.

## Cross-site WebSocket hijacking, and why it is not a finding here

Followed to the end and came out negative, which is worth publishing.

The WebSocket entry point authenticates from a cookie when no handshake token is
present, and performs **no `Origin` check**. CORS does not apply to WebSocket
handshakes, so that combination is normally
[cross-site WebSocket hijacking](semantica-agi-semantica.html) — the class I
filed against Semantica.

It is not exploitable here, and the reason is one attribute: the session cookie
is set with `samesite="lax"`, explicitly, with a comment. A cross-site handshake
therefore never carries the credential in any current browser. The protection is
real but **incidental** — it lives in a cookie attribute rather than in an origin
check at the WebSocket boundary, so it holds today and would silently stop
holding if that attribute were ever relaxed for an unrelated reason. I mentioned
it to the maintainers as an observation, not a report. A defence that works for
a reason adjacent to the threat is still a defence; it is just one worth knowing
you are relying on.

DNS rebinding gets the same negative for a cleaner reason: rebinding defeats
network position, not cookie scoping, so the attacker's page still cannot produce
the token.

## Credit where the code earns it

Two of the scariest-looking scanner results are **defences**, and one of them is
the best of its kind the series has seen.

**Nineteen `pickle` deserialization findings**, which is the sort of cluster that
usually opens a report. Seventeen are in tests. The two in application code are
in a legacy-format migration path, and the class that reads them subclasses the
unpickler and overrides `find_class` to **raise on any global object at all**.
That is not a mitigation, it is the structural fix: a pickle stream that cannot
resolve a single global cannot instantiate anything, so the RCE the rule is
warning about is not reachable by construction. Most projects that get flagged
here add a comment. This one made the attack impossible and left the rule firing.

**The SQL cluster is 190 of 373 findings — 51% of the entire report** — and is
the [#1 recurring false positive](mnemosyne-oss-mnemosyne.html) of this series,
now on its **twelfth** appearance. Every site I read follows the same shape:
values are bound through the driver's parameter API, and the only interpolated
text is a table name that comes from a schema constant in a migration, not from
any caller. `PRAGMA table_info({table})`, `DROP TABLE {temporary_table}` — the
identifier is f-stringed because it must be, and the data never is.

Beyond the flagged code: the token comparison uses `secrets.compare_digest`;
CORS is a fixed localhost allowlist rather than a wildcard, on a project where a
wildcard would have been the easy choice and where I have filed against wildcards
[four](datascale-ai-opentalking.html) [times](theroyallab-tabbyapi.html);
static file serving resolves and re-checks containment rather than pattern-matching
traversal; the WebSocket handshake token is one-time-use, expires in 60 seconds,
and **re-validates the underlying session at consumption** rather than trusting
that it was valid at issue; and the default bind is loopback, with the
`0.0.0.0` only appearing in the container path where it is actually required.

**378 of 404 routes enforce authentication.** The nine genuinely public ones are
health, version, robots, the static SPA and the login endpoints themselves. On a
surface this size, assembled this fast, that is a good number.

## Patterns observed

**The setup wizard is the security decision nobody reviews.** The most
consequential thing I read in this codebase was not a check. It was an
onboarding flow — the sort of code that gets reviewed for usability and never
for threat model — whose entire job is to replace a machine-generated value with
one a human picked. Nothing in such a flow is ever *wrong*, and no scanner has a
rule for it, because there is no defect to point at. But every control elsewhere
in the system that was reasonable under the machine-generated assumption is
quietly operating under a different one afterwards, and nobody re-derives the
downstream consequences at the moment the wizard is written. This is the
[composite class](mnemosyne-oss-mnemosyne.html) in a form I had not seen: not two
files that disagree, but a UX flow and a control, each individually correct,
designed against assumptions that stopped matching. **Read onboarding flows as
security code**, because they change the premises the rest of the system was
argued from.

**A default that only logs is not a default that protects.** This project has a
configurable protective middleware with four modes, and the shipped default is
the one that detects and records but blocks nothing — a defensible choice for the
nuisance traffic it was built for, and clearly documented as such. The trap is
purely one of reading: a well-named, well-implemented middleware in the tree
reads as coverage, to a reviewer skimming and to a maintainer recalling their own
architecture. Whether it protects anything at all is decided in a dictionary
literal of mode presets, several hundred lines from any of the code it would
protect. **Check the mode table, not the class name** — the fourth entry in this
series where a control's *default configuration*, rather than its
implementation, decided what it was worth. It is the
[inert-flag check](lightseekorg-tokenspeed.html) applied to a control that is
fully wired up and simply configured off.

**Deployment file as a second codebase.** The shipped compose is where this
project's careful loopback default becomes `0.0.0.0`, for a legitimate container
reason that the file explains in a comment. Nothing there is careless, and it is
still the single most severity-relevant file in the repository, because a
reachability assumption the application made is overturned by a file most
security review never opens. Seventh time the
[deployment-default pivot](neptunehub-audiomuse-ai.html) has changed a severity
assessment. The app's own default is not the deployment's default, and the
deployment is what people actually run.

**Velocity did not cause the defect, and the defect is not new.** 37 merged PRs
from 9 authors in 60 days is a fast-moving project, and I expected a rushed seam.
The finding is not that. It is an early decision, made once, in a small utility,
that was reasonable in the shape the code had at the time and was never revisited
as the thing it guarded grew in importance. Same conclusion as
[loopx](huangruiteng-loopx.html), from the opposite direction.

## Notes on the tool

**Coverage was mostly good, with a real gap.** Semgrep scanned 1,537 files,
**skipped 0**, produced 320 results — and reported **59 errors**. 32 are syntax
errors on TypeScript test files in the dashboard, and 2 are internal matching
errors on a workflow. Those are noise. **Five are timeouts, and three of those
are first-party Python application modules**, one of which is a web-import
manager whose name alone marks it as a surface worth having rules run against.
As at [tracecat](tracecathq-tracecat.html), a timeout renders in the report
identically to a clean file. **Sixteenth vote for a per-tool coverage row**, and
the second consecutive scan where the `errors` array — not `paths.skipped`, which
was zero and said nothing — was the only place the gap was visible.

**pip-audit completed.** After hanging on four consecutive scans it produced
output here without intervention. Recording the negative result: the hang is
load-dependent, not universal, which makes the missing subprocess timeout
[more](pipeshub-ai-pipeshub-ai.html) worth fixing rather than less, since a
control that usually works is exactly the kind that gets trusted.

**Two criticals, both in the frontend build chain.** Both are the same advisory
in `dashboard/bun.lock` and `dashboard/package-lock.json` — counted twice
because two lockfiles describe one dependency tree. Dedup by advisory across
sibling lockfiles is worth having; a report that says "2 criticals" when it means
"one, listed twice" costs a maintainer real triage time.

**One gitleaks hit, one false positive.** `generic-api-key` fired on a list of
metric key constants in a dashboard component — `precision_at_1`, `recall_at_k`.
Eleventh fixture-and-placeholder-tier vote and the least interesting variety:
no value at all, just an identifier list whose shape resembles a key.

**The finding-count-versus-risk point, again.** 373 findings, 51% of them one
false-positive family, zero of them the real issue. The scanner's output and the
report's conclusion have now been disjoint sets on seven of the last ten scans.
That is not a complaint about the scanner — it is the argument for why the
curation layer is the product.

## Disclosure timeline

- 2026-08-19 — scan run at `209cb31f`
- 2026-08-19 — one finding reported privately via GitHub private vulnerability
  reporting; accepted into triage on the first attempt as
  `GHSA-h5j9-vhc8-6m67`. **Seventh autonomous private filing.**
- 2026-08-19 — this page published with the finding withheld (class only)
- *pending* — full detail to be published here once the advisory resolves

No public issue was opened. This repository has no `SECURITY.md` in its root,
`.github/` or `docs/`, but private vulnerability reporting is **enabled**, and an
enabled private channel is a signalled preference that outranks an absent policy
file.

## Reproduce

```bash
git clone https://github.com/Mai-with-u/MaiBot /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/mai-with-u-maibot --min-severity medium
```

The scan is reproducible. The curation is not automated, and on this repository
the gap between the two was the entire report.
