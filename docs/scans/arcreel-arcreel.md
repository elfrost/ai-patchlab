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
**Disclosure status:** ✅ **resolved** — filed privately as
[GHSA-5r36-2f3p-5q87](https://github.com/ArcReel/ArcReel/security/advisories/GHSA-5r36-2f3p-5q87),
accepted on 2026-08-06, fixed in
[v0.31.0](https://github.com/ArcReel/ArcReel/releases/tag/v0.31.0) and
**published by the maintainers on 2026-09-23**, fifty days after filing. The
embargo has lifted; the specifics are below.

## Update — 2026-09-23: fixed and published

The advisory is public, so this page no longer needs to talk around the finding.

**[GHSA-5r36-2f3p-5q87](https://github.com/ArcReel/ArcReel/security/advisories/GHSA-5r36-2f3p-5q87)**
— *Anonymous project-file endpoint served any file inside a project directory.*
High (CVSS 3.1 7.5, `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`), CWE-200 / CWE-862,
vulnerable `< 0.31.0`, patched in **0.31.0**, credited to
[@elfrost](https://github.com/elfrost) as reporter.

**What was withheld.** The reviewed exception was `GET
/api/v1/files/{project_name}/{path}`, which lives on a separate `public_router`
mounted with no authentication dependency (`server/app.py:609` at the scanned
commit). The decision was deliberate and tested, since the route sits in the
auth-coverage test's `PUBLIC_OPERATIONS` list, and it was justified in writing:
`<img src>` and `<video src>` cannot carry an `Authorization` header. But the
route served **any** file inside the project directory, not only media. That
included the project manifest, the source manuscript, scripts, drafts and agent
state. The unremarkable default was `CORS_ORIGINS`, which fell back to `*`
(`server/app.py:479`), so every response carried `Access-Control-Allow-Origin:
*`. With that header, any web page the operator visited could `fetch()` those
files from their instance and **read** them, with no credentials and no
position on their network. The `<img src>` justification never needed that
header, because images render cross-origin without it; the wildcard only
granted the programmatic read the exemption was never meant to allow. Neither
bundled compose file set `CORS_ORIGINS`, and the SPA is served same-origin, so
the shipped deployment did not need the wildcard at all.

**The fix they shipped is not the one I proposed, and it is stronger where it
matters.** I offered a one-line default change (an empty CORS allow-list) plus
two token-based media routes the codebase already used elsewhere.
[#2601](https://github.com/ArcReel/ArcReel/pull/2601) attacked the other half
of the composite instead. It narrowed **what** the anonymous route will serve,
not **who** may read it:

- files only from an allow-list of eleven media directories, their `versions/`
  snapshot buckets, and the root `style_reference` image;
- seven media extensions (`png jpg jpeg webp mp4 wav mp3`, case-insensitive);
- everything else answers with the same 404 as a missing file;
- `X-Content-Type-Options: nosniff` on every response;
- the same extension allow-list on the global-assets route.

My one-liner would have closed the cross-origin read and left manuscripts
readable by anyone who can reach the port, which on the README's Compose path
means the whole LAN. Theirs closes the content class for **every** anonymous
reader. It also covers an impact I had not reported, which the advisory
documents: files were served inline with a type inferred from the name, so HTML
or SVG placed in a project could run in the ArcReel origin. ADR 0071 and the
threat model now define exactly which media stays anonymous, and the pull
request records its own residue (two response fields that still point `source/`
and `output/` entries at the now-404ing route).

**Re-verified, not assumed.** I lifted `serve_project_file`'s decision logic
verbatim from v0.31.0 and ran 31 request paths against a synthetic project tree.
It uses `safe_join` from `lib/infra/path_safety.py` plus the new
`is_public_media_path`. Before the fix, **14 non-media files** were served:

- nine by their direct path;
- two through `storyboards/../`;
- three through Windows filename aliases (`::$DATA`, a trailing dot, a trailing
  space) that all resolve to `project.json`.

At v0.31.0 the count is **0**, and all six media files are still served. The
allow-list is evaluated on the **resolved real path**, the same path
`FileResponse` then opens. There is no gap between how the check parses the
request and how the file server does, which was the flaw in
[sie's first Host allowlist](superlinked-sie.html). One case was not run here:
symlinks, because this machine has neither symlink privilege nor a Linux VM.
The maintainers' own `test_media_named_symlink_to_non_media_file_returns_404`
covers exactly that case, and the check works on the resolved path by
construction.

**A correction to this page.** Below, I described a third element that turned
"you would have to already know what to ask for" into "you can find out". It
was the route's two distinguishable 404 bodies: project missing versus file
missing. The difference is real, and it is still there at v0.31.0. **The
conclusion I drew from it was overstated.** The UI never sends a project name.
Identifiers are generated as `<title-slug>-<8 random hex>` (`secrets.token_hex(4)`,
32 bits), and they were at the scanned commit too. So the oracle confirms a
guessed identifier but cannot practically find one. Only a name chosen by hand
through the API is guessable. The real precondition, which the advisory states
correctly, was **knowing the project identifier**.

**What is unchanged, and why I am not reporting it again.** `CORS_ORIGINS`
still defaults to `*` (now in `server/cors_config.py`), so the media that ADR
0071 keeps anonymous by design is also readable cross-origin. Both that and
the 404 difference sit behind the same 32-bit identifier. I count them as
hardening, not a residual vulnerability. One reading note on the advisory: it
says a strictly loopback-only deployment is the default. The README's
documented install path is Docker Compose, and the README itself says that
Compose publishes port 1241 on every host interface. Before 0.31.0, the
wildcard also made even a loopback-only instance readable from a web page,
given the identifier. Upgrading is the answer either way.

**Timeline.** Filed 2026-08-04 through private vulnerability reporting ·
accepted 2026-08-06, High kept as filed · still unfixed at `main` on 2026-08-19,
after two releases · fix merged 2026-09-21 (#2601) · v0.31.0 released and
advisory published 2026-09-23 · re-verified the same day. The **25th** fix in
this series. Three advisories in this series had been accepted and left
unpublished; ArcReel is the first of them to be published, 48 days after
acceptance and with no nudge. Acceptance is not resolution, but here it
predicted it.

The rest of this page is the original write-up, unchanged apart from this
section and the status line, and kept as it was published under embargo.

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
curated by hand; scanner output alone is not a vulnerability report. Full
technical detail was added on 2026-09-23, when the advisory was published.*

---

## More from this series

- **Next scan:** [Vexa-ai/vexa](vexa-ai-vexa.html) — 2026-08-05, 1 real — withheld
- **Previous scan:** [the-momentum/open-wearables](the-momentum-open-wearables.html) — 2026-08-03, 2 real
- [Every scan in the series]({{ '/' | relative_url }}) — 105 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 24 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — 40 of them, published as they were
