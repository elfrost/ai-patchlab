---
layout: default
title: "mims-harvard/ToolUniverse: security scan"
date: 2026-09-09
---

# mims-harvard/ToolUniverse — security scan

**Repository:** [mims-harvard/ToolUniverse](https://github.com/mims-harvard/ToolUniverse)
**Commit scanned:** `7a0ceb2`
**Scan date:** 2026-09-09
**Disclosure status:** reported privately — detail withheld pending maintainer response

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 140 |
| Medium | 140 |
| Low | 0 |
| Info | 3 |

**Total findings:** 284 (1 real after curation, reported privately)

## Top findings

**Withheld.** ToolUniverse has GitHub private vulnerability reporting enabled, which
is a signalled preference for a private channel, so the report went there
(GHSA-mv53-jxjr-hp8g, filed 2026-09-09, currently in triage) rather than into a public
issue. The specifics stay out of this page until the maintainers have had a chance to
respond. What can be said without handing anyone a recipe:

- **One Medium finding**, reported privately. The class is an **intra-repo guard
  differential**: the project has a well-reasoned shared security module that documents
  two independent controls for its network servers, and applies both consistently across
  every network server it fronts — except for two, which install one control and not
  the other. In the shipped default configuration the missing control is the only one that
  would have applied.
- Two smaller supporting items were included in the same report: a dependency-pinning
  issue described below, and three calls that disable TLS certificate verification.

The thing worth saying publicly is *how* it was found, because no rule found it. No
scanner emitted this finding. It came out of taking the security module's own docstring
as a specification and checking it against every implementation — the same
contract-versus-artifact move that has produced most of the real findings in this
series. The module's docstring states plainly which control is the one that protects the
default deployment. Once that sentence is read as a requirement rather than as prose, the
question becomes mechanical: *which surfaces satisfy it?* Building that table is what
surfaced the two that do not.

The report shipped with a runnable differential: two apps built from the project's own
security helpers, imported verbatim, differing only in the guard wiring each surface
actually installs. It has a positive control (the legitimate local client still gets
`200`, so the proposed fix does not break normal use) and a negative control (the
project's own sibling surface rejects the attack request). A finding that can show the
maintainer their own code both accepting and rejecting the same request is much harder to
misread than a prose description of a threat.

## Patterns observed

**284 findings, one of them real, and the ratio is not an indictment of anything.**
ToolUniverse wraps several hundred scientific and biomedical APIs. That means the
repository is full of accession identifiers (`4DNEXHVF8WA9`), dataset UUIDs, and species
strings — which is to say, full of high-entropy tokens. Gitleaks produced 82 hits. Every
one of them is a biomedical identifier, a test fixture, or documentation, except a single
hardcoded key that the line above it documents as the vendor's *public demo key*, with
the URL where anyone can get their own. This is the clearest example yet in the series of
a rule I keep re-learning: **finding count scales with surface richness, not with risk.**
A repo that integrates 600 scientific databases will out-score a genuinely dangerous
500-line service on every secret scanner, forever.

**The two dependency tools disagreed, and both were right.** pip-audit reported
**0 vulnerabilities** across 156 packages. Trivy reported **97**, including the only
Critical. The instinct is to decide which one is broken. Neither is: they opened
different files. pip-audit resolved `pyproject.toml`, where every declared floor is open
(`flask>=2.0.0`), so it described the install path a user gets — current, patched
versions. Trivy read `uv.lock`, which pins specific older versions, and described the
path a *contributor* gets, because the project's own developer guide tells contributors
to run `uv sync`. Both install paths are real, both are documented, and they resolve to
materially different dependency trees. My own scanner flagged this as a coverage gap
before I noticed it — the `dependency-scan-unaudited-lockfile` meta-finding fired,
saying pip-audit had not read the shipped lockfile. That check has now paid for itself
twice in three days.

**Where the noise came from is itself a finding about scanning tool platforms.** The
`exec()`, `pickle`, and dynamic-import hits are not defects here; running
caller-supplied tool definitions is what ToolUniverse *is*. For projects whose purpose is
executing code, those primitives are product surface, and the useful question is not "is
there an `exec`?" but "is there an *unintended* path to it, and is the one real trust
boundary guarded?" The answer here was reassuring: the one endpoint that deserializes a
caller-supplied pickle path is behind the request guard, and its docstring explains
exactly why. Similarly, four workflow shell-injection hits all sit in workflows triggered
by `workflow_dispatch`, tag push, or schedule — an attacker needs write access before any
of them matter. There is no `pull_request_target` anywhere in the repo.

**A note on what "well-built" changes about a review.** This is a codebase where the
security module anticipates DNS rebinding, refuses to bind off-loopback without a token,
fails closed when its auth backend cannot initialize, and uses `hmac.compare_digest` for
token comparison. On code like this the generic checklist is exhausted almost
immediately — everything on it is already done. What is left is looking for places where
the project is inconsistent with *itself*, which is the only kind of finding that
survives when the maintainers are already better than the rulebook. That is also why the
report leads by quoting their own docstring back to them: the ask is self-consistency,
not compliance with an outside standard.

## Notes on the tool

- **The lockfile coverage meta-finding worked.** `dependency-scan-unaudited-lockfile`
  correctly identified that pip-audit had resolved `pyproject.toml` and never opened
  `uv.lock`. Without it the honest-looking headline would have been "pip-audit: 0
  vulnerabilities", which describes one install path and hides the other.
- **Semgrep partial coverage, 18 rule timeouts.** All in the `insecure-transport` family,
  across biomedical tool modules. Low-value rules in this case, but the meta-finding
  named each `rule -> file` pair, which is the point: absence of a result is not
  evidence of absence.
- **The secret scanner has no notion of domain identifiers.** 82 hits, 0 secrets. A
  future improvement worth considering: a confidence penalty for high-entropy strings
  that appear inside `data/*.json` fixture files or match known accession-ID shapes.
- **`render_template_string` produced a false positive** on a static template literal
  passed with bound variables. The rule fires on the call, not on whether the template
  itself was built from formatting.
- **The parameterized-SQL identifier false positive appeared again** — its tenth
  appearance in this series. Both hits f-string only a generated `?,?,?` placeholder
  list and bind every value. This is now far and away the most repeated false positive
  in the corpus and deserves a dedicated suppression heuristic rather than a manual
  read every time.

## Disclosure timeline

- 2026-09-09 — scan run
- 2026-09-09 — reported privately via GitHub private vulnerability reporting
  (GHSA-mv53-jxjr-hp8g), including a runnable differential repro; state: triage
- *pending* — maintainer response
- *pending* — public detail, once fixed or after a reasonable window

## Reproduce

```bash
git clone https://github.com/mims-harvard/ToolUniverse /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/mims-harvard-tooluniverse --min-severity medium --ignore-samples
```
