---
layout: default
title: "mljar/mercury: security scan"
date: 2026-09-11
---

# mljar/mercury — security scan

**Repository:** [mljar/mercury](https://github.com/mljar/mercury)
**Commit scanned:** `b02bca0`
**Scan date:** 2026-09-11
**Disclosure status:** reported privately — detail withheld pending maintainer response

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 66 |
| Medium | 71 |
| Low | 0 |
| Info | 2 |

**Total findings:** 140 (1 real after curation, reported privately)

## Top findings

**Withheld.** Mercury has GitHub private vulnerability reporting enabled, which is a
signalled preference for a private channel, so the report went there
(GHSA-8hq5-94w5-f4ff, filed 2026-09-11, currently in triage) rather than into a public
issue — the more so because the finding is a *working, unauthenticated* request against
the exact boundary the product advertises, and a public issue would be a copy-paste
recipe against live deployments before a fix exists. What can be said without handing
anyone that recipe:

- **One Medium finding**, reported privately. The class is an **intra-repo guard
  differential**. Mercury's standalone app is designed to be published as a *public*
  web page — its default start disables the Jupyter token, and it ships an execution
  "firewall" that blocks the dangerous authenticated endpoints so that anonymous
  visitors can only do safe things. Two sibling handlers list the available notebooks
  from the same configured directory. One of them trusts a caller-supplied path to
  choose *which* directory to list; the other ignores it and always uses the configured
  one. In the shipped default (no token), the trusting one is reachable without
  authentication.
- **Impact is bounded, and the bound was verified.** The divergent handler lets an
  unauthenticated caller escape the configured notebook directory to enumerate notebooks
  elsewhere on the host and read their title/description metadata, and it doubles as a
  directory-existence oracle for arbitrary paths. It does **not** yield arbitrary file
  *content*: the notebook read/render path goes through Jupyter's contents manager, which
  correctly rejects `..` traversal, and the listing code reads only metadata, not cell
  source. So this is a reconnaissance and information-disclosure primitive, not file read
  or code execution. The report says so plainly — over-claiming a metadata leak as
  "arbitrary file read" would be the fastest way to lose a careful maintainer.

The thing worth saying publicly is *how* it was found, because no scanner emitted it.
**The firewall is its own specification.** A deny-list of endpoints that a project has
deliberately blocked is a list of things the maintainers already know are (a) reachable
by anonymous users and (b) dangerous. That single fact — *they had to block
authenticated endpoints, therefore `@authenticated` does not stop anonymous callers in
this mode* — turns the review into a mechanical sweep: enumerate every request handler
the app registers, subtract the ones on the block-list and the ones replaced by safe
custom versions, and look hard at whatever remains. What remained was one listing route
that its own sibling shows how to write safely. The report ships with a runnable
reproduction that has a positive control (the legitimate served notebook still lists),
a negative control (the confined read path still returns `404` on traversal), and the
firewall's own blocked endpoints as a third control (all `403`, proving the mode and
that the decorator is not the gate).

## Patterns observed

**140 findings, and the one Critical is in the documentation website.** Trivy's single
Critical — an Astro AVIF-optimization RCE — lives in `docs/package-lock.json`, and the
bulk of the 66 High and 71 Medium are npm advisories in `yarn.lock` and `docs/`
(vega, form-data, and friends). Mercury ships to its users as a **Python package**; the
`docs/` tree and the root JavaScript lockfiles are the Astro documentation site and the
JupyterLab extension build. None of those advisories are reachable by a person running
`pip install mercury` and serving a notebook. This is the reachability-blindness pattern
in its purest form: a software-composition scanner faithfully scores every lockfile it
can find, and on a repository whose product is Python but whose *repository* is mostly a
docs website, the headline severity describes the website. The useful first act of
curation here was not reading code — it was separating the shipped artifact from the
things that merely live in the same repo.

**On code this careful, the only findings left are self-inconsistencies.** The parts of
Mercury that matter are well made. The execution path never runs client-supplied code:
the browser sends a cell *identifier* and the server resolves the source from its own
server-side manifest, rejecting stale revisions and unknown actions. The contents
manager confines path traversal. The firewall blocks terminals, arbitrary contents,
shutdown, the file browser, and the Lab UI. Notebook rendering is sanitized. When a
codebase has already done everything on the generic checklist, the checklist is
worthless, and the only class of finding that survives is *where the project disagrees
with itself* — one route written to a weaker standard than its sibling two files over.
That is the same shape as most of the real findings in this series, and it is the shape
no single-file rule can see.

**"Simple and safe" is a threat model, and it should be tested as one.** Mercury's own
welcome copy tells the visitor that "everything is designed to be simple and safe." That
is a promise about a specific deployment: an app anyone can open, with no login. The
firewall exists to keep that promise. A finding here is not "this endpoint has a bug" in
the abstract — it is "this endpoint breaks the specific promise the firewall is there to
keep," which is exactly why it belongs in a private report to the people who made the
promise rather than in a public issue.

## Notes on the tool

- **SCA has no notion of "shipped artifact versus repository."** The Critical and most
  of the High findings are the documentation site's npm tree. A high-value improvement
  would be a heuristic that separates the packaged distribution (here, the Python wheel
  built from `mercury/` + `mercury_app/`) from co-located sub-projects (`docs/`, a
  JavaScript `app/` build) and labels findings by which artifact actually carries them.
  Right now "1 Critical" reads as a product RCE when it is a docs-build advisory.
- **Semgrep coverage was healthy:** 14 results, 2 errors, 375 files scanned, 0 skipped.
  No rule-timeout coverage gap this run, unlike the recent large-file scans.
- **SHA-1 false positive.** `mercury/manager.py` uses a truncated SHA-1 as a
  configuration-cache key, over inputs first passed through a `_safe_str` sanitizer.
  It is not a security hash; flagging `insecure-hash-algorithm` here is the usual
  non-cryptographic-use false positive.
- **The Jinja `autoescape-disabled` hit** was operator-controlled welcome copy from
  `config.toml`, not attacker-reachable input — a false positive in this context, though
  the general rule is worth keeping.
- **The real finding is invisible to both SAST and SCA**, again. It is an
  absence-of-a-check combined with an intra-repo divergence: no signature matches "this
  handler trusts a parameter its sibling does not," and no dependency database contains
  a project's disagreement with its own other file.

## Disclosure timeline

- 2026-09-11 — scan run
- 2026-09-11 — reported privately via GitHub private vulnerability reporting
  (GHSA-8hq5-94w5-f4ff), including a runnable reproduction with positive and negative
  controls; state: triage
- 2026-09-14 — **report accepted by the maintainers** (`submission.accepted: true`); the
  advisory moved out of triage into a draft advisory on the repository, crediting this
  report as reporter. Accepted is not the same as fixed — a draft advisory means the
  maintainers agree there is something to advise on, and the fix and publication are
  still theirs to schedule.
- *pending* — fix and advisory publication
- *pending* — public detail here, once fixed or after a reasonable window

## Reproduce

```bash
git clone https://github.com/mljar/mercury /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/mljar-mercury --min-severity medium --ignore-samples
```
