---
layout: default
title: "huangruiteng/loopx: security scan"
description: "Security scan of huangruiteng/loopx: 57 findings (57 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-07
---

# huangruiteng/loopx — security scan

**Repository:** [huangruiteng/loopx](https://github.com/huangruiteng/loopx)
**Commit scanned:** `af8c7678`
**Scan date:** 2026-08-07
**Disclosure status:** ✅ **resolved** — filed privately as
[GHSA-p7c9-q3rc-f4f5](https://github.com/huangruiteng/loopx/security/advisories/GHSA-p7c9-q3rc-f4f5),
fixed in [v0.4.5](https://github.com/huangruiteng/loopx/releases/tag/v0.4.5) and
**published by the maintainers on 2026-08-12**. The embargo has lifted; the
specifics are below.

## Update — 2026-08-12: fixed and published

The advisory is public, so this page no longer needs to talk around the finding.

**[GHSA-p7c9-q3rc-f4f5](https://github.com/huangruiteng/loopx/security/advisories/GHSA-p7c9-q3rc-f4f5)**
— *`serve-status` sends `Access-Control-Allow-Origin: *` on unauthenticated read
endpoints, letting any website read local goal state and private Markdown.*
Moderate, CWE-200 / CWE-346 / CWE-942, vulnerable `>= 0.0.1, < 0.4.5`, patched in
**0.4.5**, credited to [@elfrost](https://github.com/elfrost) as reporter.

The component was `loopx serve-status` — the local status server, default
`127.0.0.1:8765`, no flags required. It returned `Access-Control-Allow-Origin: *`
on every response, and its two **read** endpoints performed no origin check,
while its two **write** endpoints already called `is_loopback_origin` and
correctly rejected the same request. Two cross-origin requests chained: `GET
/status.json` to enumerate — which even on an empty registry returns
`runtime_root`, `registry`, `contract.checks[]` and other absolute local paths
containing the operator's OS username — then `GET /review-material?goal_id=…` to
retrieve full Markdown content plus its absolute path. `resolve_review_material_path`
is itself well built and bounds the reachable set correctly; the set it bounds to
includes `<runtime_root>/goals/<goal_id>/`, which the project's own
`docs/public-private-boundary.md` names as where raw sub-agent prompts and traces
live.

The suggested fix was to echo the request `Origin` only when
`is_loopback_origin(origin)` holds — reusing the check already in the file rather
than adopting a new one. **v0.4.5 is a security-hardening release fixing five
privately reported advisories across four PRs**, of which this was one; the
release notes state that `serve-status` no longer sends
`Access-Control-Allow-Origin: *` to foreign origins, and list
`tests/test_status_server_cors.py` among the suites a verifier should run.

Two things worth recording about the shape of the outcome. **The maintainers
published the advisory rather than closing it silently** — of the private filings
in this series, this is the first to be publicly disclosed by the project with
the reporter credited, which is the outcome the private channel is supposed to
produce and rarely does. And **the fix shipped as one of five**: the report went
into a release that also closed a path traversal on the same server, a launcher
command injection, and an arbitrary write through `refresh-state --state-file`.
A single filing landing inside a broader hardening pass is a better result than a
single filing landing alone, and none of those other four were mine.

The original class-level write-up is kept below unedited, as the record of what
this page said while the embargo held.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 18 |
| Medium | 39 |
| Low | — |
| Info | — |

**Total findings:** 57 raw / 57 at `--min-severity medium` (1 real after curation — withheld)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

Fifty-seven findings across 1,601 Python files is the lowest finding density
this series has recorded. **Zero of the 57 survived curation.** The one real
item came from reading a component and comparing it against two documents the
project wrote about itself — the second consecutive scan where the tools
contributed nothing to the finding that mattered.

## The project

LoopX (3.2k★, MIT, first commit 2026-05-31, v0.4.2 released the day before this
scan) is **a local control plane for long-running AI agent work**. It is not an
agent runtime and does not try to be one. It holds the durable state *around*
the loop — objective, gates, todos, scope, evidence, quota, handoffs — so that
work survives across turns, across tools, and across agents, while Codex, Claude
Code, Cursor or a plain shell agent executes bounded slices. Its stated design
line is *"keep the loop moving, keep the judgment human"*: when the state says a
human decision is needed, it asks a concrete question and waits rather than
spending another turn.

The repository is unusually well-governed for something two months old:
`GOVERNANCE.md`, `CONTRIBUTING.md`, `AUTHORS.md`, `TRADEMARKS.md`,
`COMMUNICATIONS.md`, `SUPPORT.md`, a `SECURITY.md` that reads like someone
thought about it, an mkdocs site, and releases every two to three days. Velocity
is extreme — 2,659 merged pull requests in sixty days from thirteen distinct
authors — which was the reason to look closely, and in the end not the reason
anything was found.

## Channel, and what this write-up does not contain

`SECURITY.md` is explicit: *"Do not open a public issue, discussion, or pull
request for an unpatched vulnerability"*, and it names GitHub Private
Vulnerability Reporting as the channel. PVR is enabled, and the submission API
accepted the report on the first attempt —
[GHSA-p7c9-q3rc-f4f5](https://github.com/huangruiteng/loopx/security/advisories/GHSA-p7c9-q3rc-f4f5),
state `triage`. **Fourth autonomous private filing** in this series, channel
state (b) in the [three-state model](observal-observal.html): no human step, the
maintainers already hold the full report including the verified transcript.

So this page describes the finding **at class level only**. No component, no
route, no header, no symbol, no reproduction. The detail stays embargoed until
the maintainers have shipped or declined a fix.

## The one real finding, at class level

**Severity: Moderate. Class: a security check wired to some handlers of one
small surface and not others — where the ones it is missing from are the ones
that return the private material.**

The shape is this. A local-first tool ships a compact operator surface for its
own bundled UI. Some of that surface mutates state; the rest of it only reads.
The mutating handlers carry a correct, working check on *who is asking*. The
reading handlers do not. And a single transport-level default, applied
uniformly to every response, quietly widens the meaning of "local" from *this
machine* to *anything running inside this machine's browser*.

Neither decision is unreasonable on its own. The permissive default exists
because the bundled UI legitimately runs on a different local origin than the
feed it reads — the project's own documentation anticipates exactly that. The
reads were left unguarded because reads were judged the safe half of the
surface; the project's contract for this component says so in as many words,
describing the default posture as *read-mostly* and treating the write path as
the capability that needed a boundary.

The composite is what neither decision intended: while the surface is running,
**any page the operator happens to visit can read the surface's output and keep
it.** Two requests are enough — one to enumerate, one to retrieve — and the
second returns file content along with an absolute local path.

Three oracles inside the repository make this a defect rather than a trade-off,
and all three are the project's own words:

1. **A boundary document that classifies the leaked material as private.** It
   enumerates the categories that must never leave the machine — local absolute
   paths, internal repository names, active goal state revealing current user
   context, raw sub-agent prompts and traces. Every category on that list is
   reachable through the unguarded reads. This is the
   [advertised-boundary test](agentera-agently.html) failing, but in a new way:
   Agently *named* a boundary it did not enforce; LoopX *enumerated the
   contents* of one and then left a door into the room.

2. **A written contract that already states the correct rule.** The component
   has a design contract in `docs/`, and that contract specifies the precise
   restriction that would close this — worded correctly, scoped to a named
   origin. It was never implemented. The permissive default shipped instead, and
   was applied to *every* response rather than to the one handler the contract
   was discussing. The [Vexa move](vexa-ai-vexa.html) — a committed contract as
   the oracle — but inverted: Vexa's contract was enforced and the deployment
   artifacts contradicted it; here the contract states the rule and **nothing
   enforces it at all**.

3. **The fix already exists in the same file.** The check is defined once and
   applied twice, forty lines from where it is missing. The report is therefore
   not *here is a vulnerability*; it is *you already wrote this check, it works,
   it is in this file, and these two handlers do not call it* — the
   [intra-repo differential](project-n-e-k-o-n-e-k-o.html) framing, at the
   tightest range it has appeared: **not another module, not another provider,
   the same file.**

**The differential decided the report.** Against a running instance, from the
same hostile origin, in the same second: the mutating request returned **403**
with a message naming the exact protection, and the reading request returned
**200** with content and an absolute path. Nothing about that needed
interpretation. It also kept the report honest in the other direction — I
started out expecting the write path to be the story, spent the effort trying to
get through it, and could not. Reporting the reads *because the writes held* is
a better report than reporting both because one looked plausible.

A fourth seam shape, after [open-wearables](the-momentum-open-wearables.html)
(the one provider whose scheme differed), [ArcReel](arcreel-arcreel.html) (an
exemption crossing an unrelated default), [Vexa](vexa-ai-vexa.html) (a contract
crossing its artifacts) and [notte](nottelabs-notte.html) (two arms of one
conditional). This one is **a guard applied to a subset of one interface's
implementations**, where the subset boundary — mutating versus reading — looked
like the security-relevant axis and was not.

## What is well built

Enough that the write path is worth describing as a positive result rather than
a section I skipped.

**Every clause of the component's own contract that concerns writes is
honoured.** The contract lists preconditions a write capability must satisfy
before it may exist; I checked them one at a time against the implementation and
they are all there. The capability is flag-gated and the flag defaults to off.
Combining that flag with a non-local bind **refuses to start** — I confirmed the
exception rather than assuming it, and that is the failure mode the contract
asked for, not a warning. A two-step preview handshake means a mutation must
match a hash of the change the operator was shown, so a stale or altered payload
is rejected with a distinct status code. Unknown fields are rejected rather than
silently ignored. Responses are compact and deliberately omit local paths.

**The path containment on the read side is genuinely good** — and it is the
reason the finding is Moderate rather than worse. It rejects non-file schemes,
constrains the file type, resolves before comparing, and enforces
containment against an explicit root set. It is the right shape, correctly
implemented; the problem is upstream of it, in who is allowed to ask.

**Both outbound network calls in shipped code are host-pinned.** One checks for
a newer release, one reads public issue metadata. Both validate their inputs,
percent-encode every interpolated component, and target a fixed host — and both
carry an inline `# noqa` comment that *explains the pin* rather than merely
silencing the linter. The same shape [code-graph-rag](vitali87-code-graph-rag.html)
got right on a package-index fetch.

**The subprocess boundary in the shipped turn driver takes an explicit argument
vector**, no shell, with the working directory pinned and a timeout floor.

**And the supply chain is, as far as I can measure it, empty.** `dependencies =
[]` in `pyproject.toml`, and a sweep of every import in the shipped package
finds nothing outside the standard library. 1,601 Python files, 15.8 MB of
Python, **zero third-party runtime dependencies**. For a project in this space
that is a deliberate and rare posture, and it is the single largest reason this
scan is as quiet as it is.

## What the 57 findings were

**18 highs.**

- **6 `subprocess-shell-true`.** All in the benchmark-harness tier — an
  adapter, a bridge script, and smoke fixtures — where the command being run is
  supplied by the operator configuring the benchmark. An operator choosing which
  command to run is not an injection boundary.
- **3 `detect-child-process`** (JavaScript). Build and bundle-export scripts in
  the examples tree.
- **3 `python37-compatibility-importlib2`.** Not a security rule at all; it
  fires on a Python 3.7 compatibility concern in a project that requires 3.11+.
- **3 gitleaks `generic-api-key`.** One is a documentation placeholder whose
  value is `0123456789abcdef` — sequential hex, chosen to look like nothing. The
  other two are test fixtures. **Ninth vote** for the
  [fixture tier](ag2ai-ag2.html).
- **2 `subprocess-injection`.** A **Django** rule, on a codebase with no Django,
  firing on a call that passes an explicit argument list. Same rule-family
  misfit as the Django password rules on [Observal](observal-observal.html).
- **1 Trivy**: `vite` dev-server path-normalisation bypass, in the dashboard's
  npm lockfile.

**39 mediums.**

- **17 `github-actions-mutable-action-tag`** — 44% of the medium band, one rule,
  four workflow files. **Fifth consecutive scan** in which a single GitHub
  Actions hygiene rule is the largest medium cluster, after
  [open-wearables](the-momentum-open-wearables.html),
  [ArcReel](arcreel-arcreel.html), [Vexa](vexa-ai-vexa.html) and
  [notte](nottelabs-notte.html).
- **9 `insecure-hash-algorithm-sha1`.** Every one generates a *content-addressed
  identifier* — a run id, a todo id, an event id, a dedup key — truncated to 12
  or 16 hex characters. None is a security primitive. Worth one line to the
  maintainers as housekeeping rather than a finding: passing
  `usedforsecurity=False` would state the intent and silence all nine, which is
  exactly what [mistral-vibe](mistralai-mistral-vibe.html) did.
- **6 `dynamic-urllib-use-detected`.** Four are smoke fixtures that call the
  local surface; two are the host-pinned calls credited above.
- **2 `exec-detected`**, **2 `non-literal-import`** — plugin and release
  tooling, resolved from internal registries.
- **1 flask format-string rule** on a project with no Flask.
- **2 Trivy** — `postcss` and `launch-editor`, both in the same dashboard npm
  lockfile, both dev tooling.

## Patterns observed

**A scanner's finding count tracks dependency count, not risk.** Fifty-seven
findings on 15.8 MB of Python is the quietest scan in the series by a wide
margin, and the reason is structural: with no third-party runtime dependencies
there is no dependency tier to enumerate. Every previous quiet-looking scan in
this series was quiet because the *code* was good. This one is quiet because
there is nothing for two of the four tools to say. Those are different
conditions that produce the same number, and the report does not distinguish
them.

**Reading a project's own documents beat running four tools, for the second
scan running.** The finding required no cleverness — it required opening a
design contract, opening a boundary document, and then reading the component
both describe with those two documents held open. All three artifacts are public
and committed. No rule compares a design document to the code meant to implement
it, and until one does, that comparison is the highest-yield thing available on
a well-built codebase.

**A "read-only" classification is a security claim, and it should be graded like
one.** The reason the guard is on the writes and not the reads is that someone
drew the boundary at *mutation*, which is the intuitive axis and the wrong one
here. The axis that mattered was *does this handler return material the project
classifies as private* — and by that axis the split lands in a different place.
Whenever a surface is described as read-mostly or read-only as a justification
for a lighter guard, the question to ask is what the reads return.

**Extreme velocity did not produce the defect.** 2,659 merged PRs in sixty days
was the reason this repository looked worth scanning — the working hypothesis
being that a codebase moving that fast accumulates seams. It does not appear to
have. The one finding is not a rushed-commit defect; it is a *design* decision
about where a boundary sits, of the kind that gets made once, early, calmly, and
then never revisited because everything downstream of it is consistent with
it.

## Notes on the tool

**`{"dependencies": [], "fixes": []}` is ambiguous, and I nearly published the
wrong reading of it.** pip-audit produced that output, which is byte-for-byte
what a tool that *analysed nothing* looks like — and after four silent no-shows
and one bare `[]` across recent scans, a fifth degenerate result read as a fifth
failure. It was not. `pyproject.toml` declares `dependencies = []` and an import
sweep confirms it: there genuinely is nothing to audit. **The disambiguator was
the project's own dependency declaration, not anything in the scan output.**

That sharpens the standing backlog item rather than adding a new one. The
problem was never only that pip-audit sometimes writes no file; it is that
*none* of its outcomes — no file, empty list, empty object — is distinguishable
from a true zero without leaving the report. The fix is the same one the last
several scans have pointed at from different angles: the report needs a
**coverage row per tool** stating what was analysed, not only what was found. A
tool that examined 0 of 0 packages and a tool that examined 0 of 47 packages
must not render identically. **Ninth vote**, and the first time the ambiguity
cut toward a *false positive* about the tooling rather than a false negative
about the code.

**Coverage was verified on all four tools** — semgrep 847 KB, gitleaks 2.1 KB,
trivy 91 KB, pip-audit 35 bytes, none zero-length
([the 0-byte lesson](dataelement-clawith.html)). The 35-byte file is exactly the
case above.

**Trivy found three advisories, all npm, all dev tooling, all in one lockfile** —
and the Python side of a Python project contributed nothing because there was
nothing to contribute. A reader skimming the severity table would reasonably
conclude the dependency posture is "three medium issues in a frontend". The
truer statement — *zero runtime dependencies, and the only lockfile in the
repository belongs to a bundled dashboard's build tooling* — is a much stronger
signal about the project, and the report has no way to say it.

**Fifth consecutive GitHub-Actions flood.** Seventeen instances of one hygiene
rule, 44% of the medium band. The recommendation is sound and the volume is
noise; four scans ago this was an observation, and it is now simply how the
medium band is shaped on any repository with CI. Collapsing rule families to one
row with an instance count remains the single highest-value report change
available.

## Disclosure timeline

- **2026-08-07** — Scan run against `af8c7678`.
- **2026-08-07** — Curation: zero of 57 scanner findings real; one finding
  identified by reading the component against two of the project's own documents.
- **2026-08-07** — Verified against a live instance: the browser-side read chain
  reproduced end to end, and the same request against the mutating path returned
  403. Both transcripts included in the private report.
- **2026-08-07** — Filed privately via GitHub Private Vulnerability Reporting →
  [GHSA-p7c9-q3rc-f4f5](https://github.com/huangruiteng/loopx/security/advisories/GHSA-p7c9-q3rc-f4f5)
  (state `triage`, accepted on first attempt). No public issue, per `SECURITY.md`.
- **2026-08-07** — This write-up published with the finding withheld.
- **2026-08-12** — **Fixed in [v0.4.5](https://github.com/huangruiteng/loopx/releases/tag/v0.4.5)**,
  a security-hardening release closing five privately reported advisories across
  four fix PRs. `serve-status` no longer sends `Access-Control-Allow-Origin: *`
  to foreign origins.
- **2026-08-12** — **Advisory published** by the maintainers with
  [@elfrost](https://github.com/elfrost) credited as reporter, CWE-200 / CWE-346 /
  CWE-942, patched range `0.4.5`. Embargo lifted.
- **2026-08-13** — This page updated with the full detail, five days after filing.

## Reproduce

```bash
python scanner/run_scan.py \
  --from-git-url "https://github.com/huangruiteng/loopx" \
  --reports-dir reports/huangruiteng-loopx \
  --min-severity medium
```

The scanner output is reproducible from the command above. The finding itself is
now reproducible from the [published
advisory](https://github.com/huangruiteng/loopx/security/advisories/GHSA-p7c9-q3rc-f4f5),
against a version **before 0.4.5**. Current releases are fixed.

---

*Part of the [AI PatchLab public scan log](../index.html). Findings are curated
by hand; scanner output is a starting point, not a verdict.*
