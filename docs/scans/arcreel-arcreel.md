---
layout: default
title: "ArcReel/ArcReel: security scan"
description: "Security scan of ArcReel/ArcReel: 82 findings (77 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-04
---

# ArcReel/ArcReel — security scan

**Repository:** [ArcReel/ArcReel](https://github.com/ArcReel/ArcReel)
**Commit scanned:** `a7e78bdb`
**Scan date:** 2026-08-04
**Disclosure status:** withheld — one real finding filed privately as
[GHSA-5r36-2f3p-5q87](https://github.com/ArcReel/ArcReel/security/advisories/GHSA-5r36-2f3p-5q87),
still embargoed. **Accepted by the maintainers on 2026-08-06**: the submitted
report was converted into a draft advisory (`submission.accepted: true`,
state `triage` → `draft`), the **High** severity was kept as filed, CWE-200 and
CWE-862 were assigned, and the reporter was credited. No patched version is
published yet, so the finding stays withheld here.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 34 |
| Medium | 43 |
| Low | — |
| Info | — |

**Total findings:** 82 raw / 77 at `--min-severity medium` (1 real after curation — withheld)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

ArcReel (3.9k★, AGPL-3.0) is an **open-source AI video generation workbench**:
you feed it a novel, and an agent pipeline carries it through character and
scene design, script, storyboard, and finished video. It orchestrates the
Claude Agent SDK over a skill-plus-subagent layout, fans image and video
generation out across eight-plus providers (Gemini, Volcengine Ark, Grok,
OpenAI, Vidu, Bailian, MiniMax, Kling) with per-project override, and runs an
async task queue with RPM limiting, independent image/video/audio concurrency
channels, lease-based scheduling and resumable jobs. A FastAPI backend, a React
19 workbench, SQLite or Postgres via Alembic, and a published container image.

Maintenance is unusually responsive: **360 issues closed in the last 60 days**
and ~97 pull requests merged, though almost entirely by a single maintainer.
CodeQL runs on the repository, Codecov is wired, and there is a
pre-commit config, a release-please setup and an `openspec/` directory of
written design proposals.

**This is, by a clear margin, the best-defended codebase in this series so far.**
That is not a throwaway compliment — it is the reason the one real finding is
interesting, and it is why most of this page is about things that are *not*
findings.

### A note on what this write-up does not contain

ArcReel ships no `SECURITY.md` in any of the three conventional locations, which
by the usual test here would make a public courtesy issue the proportionate
move. But the repository has **GitHub private vulnerability reporting explicitly
enabled** — a setting that is off by default and has to be deliberately turned
on. That is a signalled preference, and for a genuine unauthenticated
data-disclosure it outranks the absence of a policy file. The report went
through the private channel, and the submission API accepted it on the first
attempt.

So this page describes the *shape* of the finding and the reasoning that
produced it, with the components, the mechanism and the reproduction left out
until the advisory resolves.

One consequence worth stating plainly: **the tooling section below is
deliberately incomplete.** On previous withheld scans the finding was invisible
to every rule, so the rule inventory could be published whole. That is not the
case here, and an exhaustive "here is every bucket, and here is why each one is
dismissable" list would identify the withheld item by subtraction. Withholding
is a property of the whole document, not of one section. The dismissals below
are real and complete as far as they go; they are simply not the entire list.

## The one real finding, at class level

**Severity: High. Class: two deliberate, individually-defensible decisions that
compose into a capability neither one intended to grant.**

Neither half is a bug. That is the whole point.

The first half is an explicit, documented, *tested* exception to a security
invariant that the project otherwise enforces uniformly. ArcReel does something
here that almost no project in this series has done: it has a test that
enumerates every API operation from the generated OpenAPI schema, fires an
unauthenticated request at each one, and asserts the exception list is exact —
stale entries fail the build, and any newly added route that forgets its guard
fails it too. The exception carries a written justification, and on its own
terms that justification is sound.

The second half is a **default value**, set in an unrelated part of the
application, which ships unchanged into the production deployment because
nothing in the bundled deployment configuration overrides it.

Separately: a reviewed exception, and an unremarkable default. Together: the
exception's blast radius stops being "whoever can already reach the service" and
becomes something substantially wider, reachable without credentials and without
any privileged network position. The written justification for the exception
does not actually require the default that widens it — the two were decided in
different files, for different reasons, by reasoning that was locally correct
each time.

There is a third, smaller element that turns "you would have to already know what
to ask for" into "you can find out" — and, in a detail I found genuinely
striking, the codebase **already contains the exact reasoning needed to close
it**, written as an inline comment, correctly applied to a neighbouring case a
few lines away in the very same handler. The author saw the class. They just
applied the insight one level too narrowly.

The recommended fix is a **one-line default change** that breaks nothing,
because the capability the default enables is not needed by the shipped
deployment at all. Two deeper hardening options were also offered, and both are
patterns **already implemented elsewhere in this same codebase** for exactly the
problem the exception was created to solve — which is the framing most likely to
get a fix merged: *you already wrote this fix, twice; here is the third place it
belongs.*

**No rule described the composite.** A composite is not the kind of thing a
pattern matcher finds — each half is unremarkable on its own, and only the pair
is a problem. It came out of asking a structural question, not a syntactic one:
*which routes are exempt from the guard every other route has, and what else in
the request path changes who can reach them?*

## What the other 76 findings were

### The dependency tier, and reachability

The high tier's dependency CVEs include three separate **MCP Python SDK**
advisories: HTTP transports serving session requests without verification,
experimental task handlers reachable by any client, and a WebSocket transport
that does not validate where the connection came from. All three describe
**network server transports**.

ArcReel starts none of them. Its agent tools are built with
`create_sdk_mcp_server` and handed to the Agent SDK as an **in-process** server —
there is no HTTP listener, no WebSocket endpoint, and no stdio transport for the
MCP surface at all. The version matches; the transport does not exist. This is
the [version-match-versus-reachability](q00-ouroboros.html) distinction in its
cleanest form yet, and the mirror image of
[code-graph-rag](vitali87-code-graph-rag.html), where the identical class of MCP
advisory *was* live precisely because the project bound a StreamableHTTP
transport on `0.0.0.0`. Same CVEs, opposite verdicts, and the deciding fact is
one function call.

The remaining dependency hits — `aiohttp`, `cryptography` PKCS#7, `pyasn1`
(three DoS advisories), `soupsieve`, DOMPurify, `pydantic-settings` — are
routine drift worth a refresh, none reachable in a way that changes the risk
picture.

### The secrets tier

All **18** gitleaks hits are `generic-api-key`, and all 18 are in `tests/` or
`docs/`: eleven in the custom-provider API test module, the rest spread across
auth, logging, and config test files plus two written design plans. Test
fixtures and documentation prose. This is the **seventh** independent vote for
the generated/fixture-secret tier — after
[AG2's](ag2ai-ag2.html) `# pragma: allowlist secret` docstrings,
[Kiln](kiln-ai-kiln.html), [IBM's](ibm-mcp-context-forge.html) own
`.secrets.baseline`, [N.E.K.O's](project-n-e-k-o-n-e-k-o.html) i18n strings and
[pipeshub's](pipeshub-ai-pipeshub-ai.html) generated specs. Zero real secrets.

### The SQL tier

Five `avoid-sqlalchemy-text` hits: four are **Alembic migrations** — DDL, the
long-standing [candidate-FP tier](soju06-codex-lb.html) — and the fifth is the
[#1 recurring identifier FP](mnemosyne-oss-mnemosyne.html) in its textbook form.
The task-repository query interpolates exactly one thing into its `text()`
block: a **constant clause chosen by an `if`**, containing no user data. The
values ride in as `:media_type` and an expanding `:providers` bindparam. Nothing
user-supplied is ever formatted into the string. One representative read settles
it; enumerating the other four would have been busywork.

### The workflow and container tier

**34 of the 43 mediums** are `github-actions-mutable-action-tag` — unpinned
action tags. This is the pattern noted on
[open-wearables](the-momentum-open-wearables.html) a day earlier: a single rule
firing dozens of times floods the medium band and buries everything else. It
should collapse to one finding with a count.

The Dockerfile runs as **root** with no `USER` directive, and both compose files
add `seccomp:unconfined`, `apparmor:unconfined` and `CAP_NET_ADMIN`. In most
projects that stack would be a finding. Here it is a documented, reasoned
trade-off: those relaxations exist so that **bubblewrap can nest a user
namespace inside the container**, which is what sandboxes the agent's Bash tool.
The project is deliberately trading a slice of the Docker boundary to obtain a
stronger inner one, and it says so in a comment at the point of decision. Worth
raising as a hardening conversation — running the app as a non-root user is
compatible with the bwrap requirement — but it is not a defect, and reporting it
as one would misread the design.

## Credit where it is due

This section is longer than usual because the codebase earned it.

**The auth-coverage test.** Deriving the list of API operations from the
application itself rather than from a hand-maintained fixture, asserting every
one of them rejects an unauthenticated caller, and failing the build when the
list drifts — this is the single best answer to "a router registration lost its
guard and nobody noticed" that I have seen on this series. It is the reason the
finding above is a *composition* problem rather than an *oversight* problem:
oversights cannot survive this test.

**The path-safety module.** One function, documented as the project's only
containment check, implemented with `realpath` plus a prefix comparison — and
the docstring explains that this shape was chosen **because CodeQL recognises it
as a sanitizer** while `Path.resolve()` with `is_relative_to()` is not
recognised and would generate permanent noise. It handles the filesystem-root
edge case where naive separator-appending breaks the prefix test, converts
embedded-NUL `ValueError`s into its own exception type so callers cannot leak a
500, and returns the *realpath* rather than the caller's string so the tainted
value stops propagating. 98 call sites go through it.

**The archive importer.** ZIP member validation rejects encrypted entries,
absolute paths, Windows drive-letter prefixes, `..` segments, and symlink
entries — before extraction. Complete zip-slip coverage.

**The Bash fallback whitelist.** The docstring for the Windows degraded-mode
command check *enumerates its own three bypass classes* — metacharacter
chaining, command-name prefix collision, and path traversal out of the skills
directory — and then defends each: metacharacters rejected outright with no
attempt to parse quoting context, `..` rejected across the raw string *and* two
normalisation variants because a shell would collapse `".."` and `.\.` back into
`..`, whitelist matching on token boundaries so `ffmpegX` cannot pass as
`ffmpeg`, and script entry points constrained by regex to
`<skill>/scripts/<name>.py` rather than anything under the skills tree. Writing
down the attacks against your own mitigation is a discipline worth naming.

**Refusing to degrade on supported platforms.** Sandbox tooling missing on macOS
or Linux is a **hard startup failure**, not a warning. Only Windows, which the
Agent SDK genuinely does not support, falls back — loudly, to the whitelist
above. Compare [Agently](agentera-agently.html), where a component named
`PythonSandbox` did not enforce a sandbox: this is the opposite, an honest
boundary that fails closed where it can and announces itself where it cannot.

**Keeping provider secrets out of the parent process.** A startup assertion
scans `os.environ` for provider keys and **refuses to boot** if any are present,
because the sandboxed Bash child inherits the parent environment by fork; keys
live in the database and are injected per-child explicitly. There is a matched
pair of methods with the mutual constraint that the env-scrubbing wrapper must
not run in Windows fallback mode — because the wrapped command would begin with
`env -u` and could never match the prefix whitelist — and the two methods are
deliberately kept adjacent with that coupling documented. That is a rare
quality: two safety mechanisms that would silently cancel each other, held
together in one place with the reason written down.

**Credential masking is uniform.** Every path that returns provider
configuration to the client goes through one `mask_secret` helper. There is no
[N.E.K.O-style](project-n-e-k-o-n-e-k-o.html) endpoint handing back raw keys.

**The auth module refuses to fail open.** The set of values that disable
authentication deliberately **excludes the empty string**, with a comment
explaining that a malformed `.env` line should fall back to enabled rather than
silently disabling it. Password comparison performs the hash verification even
when the username is wrong, to avoid a timing oracle. API keys are stored as
SHA-256 hashes with negative caching, and the positive-cache TTL is **bounded by
the key's own expiry** so a revoked key cannot ride a stale cache entry. Compare
[rocketride](rocketride-org-rocketride-server.html), where an unset credential
variable skipped the guard entirely: this is the same decision point, reasoned
through to the opposite outcome.

## Notes on the tool

- **Coverage verified on all four scanners** ([the 0-byte
  lesson](dataelement-clawith.html)): Semgrep 340 KB, Gitleaks 13 KB, Trivy
  426 KB, pip-audit 6 KB — all non-empty.
- **pip-audit completed for the first time in four scans.** It had silently
  produced no output file on the previous three runs
  ([pipeshub](pipeshub-ai-pipeshub-ai.html), Observal,
  [open-wearables](the-momentum-open-wearables.html)) while its `info`-severity
  "did not run" meta finding was filtered out by `--min-severity medium`. Here
  it resolved 105 dependencies and reported zero vulnerabilities. That is a
  *real* zero — but the only reason I can say so is that the output file exists
  and has content. Exempting scanner-infrastructure meta findings from the
  severity floor remains the top backlog item: "the tool found nothing" and "the
  tool never ran" must not render identically.
- **A tool-disagreement worth noting.** pip-audit reported 0 across 105
  resolved dependencies while Trivy reported roughly a dozen Python advisories
  over the same project. Different databases and different resolution targets,
  but a scan that ran only one of them would have drawn a different conclusion.
  Worth surfacing the disagreement in the report rather than silently unioning.
- **Same-rule flooding, again.** 34 identical-rule hits occupying 79% of the
  medium band, one scan after the same thing happened with 36 hits in a single
  file. Collapsing repeated same-rule findings into one entry with a count is
  now a two-vote backlog item.
- **Structural questions beat syntactic ones on well-built code.** 82 raw
  findings on a codebase this careful, and the one real item was not among
  them. It came from asking which routes are exempt from an invariant — a
  question about the *shape* of the application, which no per-file rule can pose.

---

*Scanned with [AI PatchLab](https://github.com/elfrost/ai-patchlab). Findings are
curated by hand; scanner output alone is not a vulnerability report. This page
will be updated with full technical detail once the advisory resolves.*
