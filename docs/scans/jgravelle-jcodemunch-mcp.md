---
layout: default
title: "jgravelle/jcodemunch-mcp: security scan"
date: 2026-08-12
---

# jgravelle/jcodemunch-mcp — security scan

**Repository:** [jgravelle/jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp)
**Commit scanned:** `9cfa6d21`
**Scan date:** 2026-08-12
**Disclosure status:** disclosed — [issue #444](https://github.com/jgravelle/jcodemunch-mcp/issues/444) (quality pass, filed on the project's own multi-finding template), fix in [PR #443](https://github.com/jgravelle/jcodemunch-mcp/pull/443).
**Outcome (2026-08-12/13):** all three accepted, split one-per-issue; ✅ **items 2 and 3 shipped in
[v1.108.274](https://github.com/jgravelle/jcodemunch-mcp/releases/tag/v1.108.274) the same evening**;
item 1 open on the PR pending a CLA signature. See [Outcome](#outcome--triage-two-corrections-and-a-repro-that-did-not-reproduce).

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 29 |
| Medium | 18 |
| Low | — |
| Info | — |

**Total findings:** 49 raw, 47 at `--min-severity medium` — **zero real**

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

## The project

jCodeMunch (2.5k★) is an **MCP server for symbol-level code retrieval**. It
parses a repository with tree-sitter, indexes the symbols, and lets an agent ask
for exactly the function it needs instead of reading whole files — the pitch is
a 95% reduction in tokens spent on code exploration. It indexes local folders
and GitHub repositories, ships a VS Code extension, a CLI, an optional login-time
file watcher, a published GitHub Action (`speedreview`), and a paid tier for
team rollups.

The human axis is the healthiest of the candidates I checked this week: 77
closed issues and merged PRs from **eight distinct authors** in the last 60
days, most of them outside contributors, pushed to on the day of the scan.

It is also the most **document-dense** target in the series. Thirty-four
Markdown files at the repository root, and a `SECURITY.md` that is 26 KB long
and is not a disclosure policy at all — it is a **controls specification**. It
enumerates the path-traversal validator by function name, the symlink-escape
rule, the secret-file classifier group by group, the file size and count caps,
the cache-directory tagging spec, the release-signing trust shape, every
background thread, every network call, and a per-extra table of "system
surfaces" for SOC 2 / HIPAA-adjacent deployments.

That document is why I picked this repository, and it is the reason the write-up
below is shaped the way it is.

## A 26 KB controls document is an oracle, not a brochure

The recurring problem in this series is that a well-built codebase gives you
nothing to push against. Every rule fires on something intentional, and
"suspicious" never converts into "defective" because the maintainer can always
answer *that is by design* — and usually be right.

A document like this one removes that escape hatch in both directions. It is a
set of **precise, checkable assertions** about what the code does. Every claim
is a test I can run. And it cuts against me as often as for me: three of the
leads I chased died because the document told me exactly where to look and the
code was doing precisely what it said.

The method for the day was therefore not "find bugs" but **diff the document
against the tree**, claim by claim. This is the [contract-versus-artifact](vexa-ai-vexa.html)
move applied to prose rather than to a typed config schema.

## Where that method found nothing — which is most of it

Worth stating plainly, because it is the bulk of the day's work and it is the
honest headline.

**The fail-open shape I went looking for first is explicitly closed.** The
Starlette bearer middleware is built by a factory that returns `None` when
`JCODEMUNCH_HTTP_TOKEN` is unset — the exact
[fail-open pattern](rocketride-org-rocketride-server.html) where a guard
evaporates because the operator never configured a secret. I expected the write
endpoints to inherit that hole. They do not. There is a helper whose entire job
is to notice it:

> Fail closed when an ingest endpoint is enabled but no token is set. […]
> Without it the write endpoint would accept unauthenticated writes (only a
> startup warning today), so we refuse (503) rather than warn.

Somebody sat down, worked out that the middleware would silently do nothing, and
wrote a per-handler 503 rather than trusting the layer above. That is the
finding I was hunting, already found and already fixed, with the reasoning left
in the docstring.

**The credential-injection class is anticipated by name.** The GitHub fetch path
pins a hardcoded `api.github.com` host and attaches the token only there — and
the comment beside it reasons explicitly about redirects and cross-origin
header-dropping, which is the precise mechanism behind the
[Observal finding](observal-observal.html), the strongest thing this series has
filed privately.

**The cache writer is confined properly.** Every write of repository content to
disk goes through a helper that resolves the candidate path and compares
`commonpath` against the base, on all four call sites. A repository is untrusted
input by the time its file paths reach the disk, and the code treats it that way.

**Per-project config cannot escalate.** A repository can ship a `.jcodemunch.jsonc`
that overrides settings, which sounded like a config-injection vector — index a
hostile repository, let it disable the secret classifier or turn on symlink
following. Two independent controls close it. The project-scoped values are only
consulted on reads that explicitly pass a repository, so a repository's config
governs its own indexing and nothing global. And `trusted_folders` — the one key
where a repository could grant itself reach outside its own tree — has a bespoke
containment check that raises if an entry escapes the project root. That check
existing at all tells you the author already treats a project config as
attacker-influenced.

**Both HTTP transports warn identically.** I specifically checked whether the
*recommended* transport (streamable-http) had the non-loopback warning that the
*deprecated* one (SSE) has, because "the path you are told to prefer is the one
that stopped warning" is a seam I have found before. Both warn, in the same
words. No asymmetry.

**And the scanners found nothing.** 47 findings above the floor, zero real. 31
of them — 66% — are the [SQL identifier interpolation FP](mnemosyne-oss-mnemosyne.html),
**eighth appearance**, settled by reading three sites rather than enumerating
thirty-one: every interpolated name is a column or table name drawn from a
literal tuple in the same function, and every data value is bound with `?`. Four
gitleaks hits are all in `tests/` (**eleventh** fixture-tier vote). Three
`run-shell-injection` and three mutable-action-tag hits are GitHub Actions —
**ninth consecutive scan** where a GitHub-Actions rule is a leading cluster. Four
SHA-1 hits are cache keys, not authentication.

## What the diff did turn up

Three items, none of which is a vulnerability, all of which are gaps between the
document and the tree. The project ships an issue template explicitly inviting
**adversarial multi-part reviews** — with a question that reads *"which of these,
if any, blocks you today?"* and the answer *"None, this is a quality pass"*
listed as completely fine. So this went upstream in that format, as a quality
pass, honestly labelled.

### 1. The pack installer's archive guard misses Windows absolute paths

`install-pack` downloads a pre-built index pack over HTTPS and extracts it into
the index directory. There **is** a traversal guard — the author clearly
intended to prevent zip-slip — and it rejects any member name starting with `/`
or containing `..`. Neither test catches a drive-absolute Windows path, and
`pathlib` treats one as absolute, so joining it to the destination **discards the
destination entirely**.

Verified rather than asserted, on Windows, against the guard as written:

```
guard_pass=True   rel='C:/Windows/Temp/evil.txt'      -> escapes base? True
guard_pass=True   rel='C:\Windows\Temp\evil2.txt'     -> escapes base? True
guard_pass=False  rel='../escape.txt'                 (correctly blocked)
```

The reason to report it despite the weak threat path — the archive comes from
the project's own endpoint, so an attacker needs a hostile response from that
endpoint, not a network position — is the **intra-repo differential**, the
framing that has [worked before](project-n-e-k-o-n-e-k-o.html). The correct
version of this check already exists in this codebase, applied to untrusted
repository paths, resolving and comparing `commonpath`. Run the three cases
above through *that* helper and all three are rejected. The ask is not "adopt my
fix"; it is "you already wrote this correctly, use it in the second place."

It also sits oddly against the document's own supply-chain posture: release
wheels are signed with Sigstore, specifically so a downloaded artifact can be
tied back to the workflow that built it. Packs are downloaded and extracted into
a directory the same document flags as needing file-integrity monitoring, and
they get neither a signature nor a complete extraction guard.

Third time this series has filed an archive-extraction item —
[pixeltable](pixeltable-pixeltable.html) and
[fast-agent](evalstate-fast-agent.html) were the first two, **both fixed** — and
the first time the project had already written a guard.

### 2. The document's division of labour has a hole where contents are returned

`SECURITY.md` explains that the secret classifier judges by filename and path
shape only, and hands off the other half of the job:

> it never reads file contents (that is response-level redaction's job, in
> `redact.py`)

Response-level redaction is real and is wired into the central tool dispatcher,
so it covers every tool — except an explicit exemption set of the three that
return file contents. The code comment gives the reason (a per-byte regex sweep
over hundreds of KB is wasted latency) and that is a legitimate engineering
tradeoff.

But it means the stated division of labour has a gap exactly where contents are
returned. A credential hardcoded inside an ordinary source file is caught by
neither half: not by the filename classifier, because the filename is ordinary,
and not by the redactor, because those three tools are exempt. The
`SECURITY.md` "Summary of Controls" table does not list response redaction at
all, so a reader auditing against that document cannot discover the exemption.

I did not file this as a defect in the code. The cheap fix is to the document —
name the exemption where the handoff is described — and the audience that
document is explicitly written for is the one that would care.

### 3. "The only route that accepts writes from another computer" is not

The document says of the org-rollup endpoint:

> This is the only route in jCodeMunch that accepts writes from another
> computer, so it is gated three ways

There are three more `POST` routes mounted on the same app, for runtime trace
ingest. The security posture is **not** the problem — they are gated
equivalently, by the same fail-closed helper quoted earlier, and they are off by
default. It is purely a stale sentence in the document that undercounts the
write surface, in a paragraph whose whole purpose is to enumerate it exhaustively.

Minor, and I would not mention it about a project that had not set the bar
itself. This one wrote "Everything jCodeMunch does beyond answering a tool call
is listed here," so the enumeration being complete is a promise.

## Tooling notes

**All four scanners reported honestly, and this time the dependency coverage is
genuinely complete** — which is worth saying because the last several scans
could not claim it. Trivy parsed `uv.lock` and the `Dockerfile`; pip-audit
resolved 38 dependencies. Both returned zero. Because a real lockfile was parsed
by both, this is a **true zero with real coverage**, not the
[over-optimistic clean](semantica-agi-semantica.html) that a `>=`-floored
`pyproject.toml` with no lockfile produces. Semgrep wrote 246 KB, gitleaks four
hits — no 0-byte failures, and pip-audit did not hang for once.

It remains the case that the report cannot tell you any of that. "Zero because
we parsed your lockfile" and "zero because we found nothing to parse" render
identically. **Twelfth vote for a per-tool coverage row** — the difference here
is that the answer came out in the project's favour, and I still had to open the
raw JSON to know it.

## The honest verdict

Twenty-sixth clean scan. Zero of 47 findings survived, and the three items I did
file are documentation gaps and a defense-in-depth hardening of a guard that
already exists — nothing here is exploitable by a remote attacker against a
default install.

The lesson I am taking is about **what makes a codebase auditable**. This one is
not quiet because it is small — it is 258 Python files with an HTTP transport, a
GitHub fetcher, an archive installer, a file watcher, a login-time service and a
published Action. It is quiet because someone wrote down what they thought the
security properties were, in enough detail to be wrong, and then mostly was not.
Every lead I chased was one the document pointed at, and the document is why the
three that survived are worth a maintainer's attention at all: without it, item
2 and item 3 would not exist as findings, because there would be no claim to
contradict.

That is the trade a controls document makes. It converts "looks fine to me" into
something falsifiable, and it invites a stranger to check. This project also
ships an issue template that says adversarial multi-part reviews are *"some of
the most valuable things this project receives."* Both of those are choices, and
they are the reason a scan of a well-built repository produced anything at all.

## Outcome — triage, two corrections, and a repro that did not reproduce

Triaged the same day. **All three findings accepted as real**, and split
one-per-issue per the project's own policy that a three-finding issue closes only
when the last item settles: [#447](https://github.com/jgravelle/jcodemunch-mcp/issues/447)
(the `install-pack` guard), [#448](https://github.com/jgravelle/jcodemunch-mcp/issues/448)
(response-level redaction absent from `SECURITY.md`),
[#449](https://github.com/jgravelle/jcodemunch-mcp/issues/449) (the stale
"only route that accepts writes" sentence).

**Both documentation items shipped in
[v1.108.274](https://github.com/jgravelle/jcodemunch-mcp/releases/tag/v1.108.274)
that evening**, on PyPI the same night. `SECURITY.md` gained a Response-Level
Secret Redaction section and a controls-table row naming the three exempt tools
and the reasoning; the remote-write paragraph now enumerates all four routes with
their separate gates, and states the property I had singled out as worth keeping
— with `JCODEMUNCH_HTTP_TOKEN` unset those routes return **503 rather than
running unauthenticated**. The more durable half is that the release also added
`tests/test_security_disclosure.py`, which asserts the document against the tree.
My finding was the *second* instance of this failure mode in this project, so the
fix they chose was not to correct two sentences but to make the next drift fail
CI instead of waiting for a stranger.

**Two corrections came back, and the second one is mine to record.** Both came
from the maintainer re-deriving my evidence rather than reading it.

**The repro I filed does not reproduce.** `_install_pack` strips one leading
`<pack-id>/` segment from every member before the join, and my three evidence
rows never survive it: `C:\Windows\Temp\evil2.txt` and `\\server\share\evil.txt`
contain no `/` at all, so they hit `len(parts) < 2` and are skipped, and
`C:/Windows/Temp/evil.txt` loses `C:` to the strip and lands harmlessly under the
base. The escaping member is `pack/C:/Windows/Temp/evil.txt` — the drive-absolute
name has to be in the **second** segment. The vulnerability is real and the patch
does catch it, because the stripped remainder reaches the guard as
`C:/Windows/…`; what I got wrong was which member escapes. And since every real
pack archive carries a `<pack-id>/` prefix, **the true shape is more natural than
the one I filed**, not less.

The cause is worth naming because it is a general one: I tested the helper at the
level the helper lives at, and never ran a member through the function that calls
it. Unit-testing a guard in isolation cannot see a transformation applied to its
input one frame up. My tests would not have caught a later reordering of the
strip ahead of the confinement check either — that gap is now closed by an
end-to-end case, [verified red without the production
change](https://github.com/jgravelle/jcodemunch-mcp/pull/443), where the install
reports **success** and writes outside the base.

**My tests were also Windows-only green.** All three parametrized names are
absolute on Windows and *relative* on POSIX, so on Linux `base / member` stays
under the base, the helper correctly returns a path rather than refusing one, and
`assert ... is None` fails — four of the nine CI legs. I could not have seen it
(first-time-contributor runs are held at `action_required`, so nothing had
executed), but "passed locally" meant "passed on one platform" and I reported it
as though it meant more. Now gated on `os.name == "nt"`, with the POSIX behaviour
deliberately *not* asserted, since resolving those names under the base is
correct there.

## Resolved 2026-08-20 — the fix shipped, and it is not my diff

**The vulnerability is fixed and released.** [Issue
#447](https://github.com/jgravelle/jcodemunch-mcp/issues/447) closed as
*completed*, [PR #519](https://github.com/jgravelle/jcodemunch-mcp/pull/519)
merged, and `install-pack` confinement shipped in
[v1.108.288](https://github.com/jgravelle/jcodemunch-mcp/releases/tag/v1.108.288)
the same hour. My [PR #443](https://github.com/jgravelle/jcodemunch-mcp/pull/443)
closed **unmerged**: the posted 2026-08-20 window expired with the CLA unsigned,
so the maintainer's stated default action fired.

**What shipped is not my diff, and the maintainer said so in the release notes
rather than in a footnote.** They applied their own pre-existing
`_safe_content_path` pattern to the call site that never had it — an independent
path, not a clean-room copy. The credit is explicit in the CHANGELOG, the release
notes and the issue close: *"@elfrost found this, analysed it, and wrote a correct
fix in #443 that could not be merged because the CLA went unsigned through a
posted window."* Stating provenance that precisely, when the easy version is
silence, is the part worth pointing at.

**The fix went past the reported call site, and the reason is the design call, not
the patch.** Because the escape is caught by *resolution* rather than by
*pattern*, it was visible that the same rule already had **three spellings** in
the tree — `security.validate_path` plus a private copy on each of the two index
stores — and the new call site would have been a fourth. There is one definition
now, with a test that fails on a fifth. The release notes open by naming this as
the release's theme: *"in three of them the report named one site while the tree
held several … this release is what checking first looks like."*

**And the regression test learned from my mistake rather than repeating it.** It
asserts *confinement* — not that `C:/…` is rejected — because that name is
absolute on Windows and an ordinary relative name on POSIX. Pinning the refusal
would have written the exact platform trivia into a security test that had already
turned four of my nine CI legs red.

**One process note, and it is theirs:** seven merge conflicts on the branch, every
one caused by their own changelog entries landing in the `[Unreleased]` block mine
occupied while the PR sat behind a form. They named it unprompted — *"a merge-order
problem we have a written rule about and kept breaking … it should not have cost
you the eight days."*

**The honest ledger:** the finding resolved, the fix is real, the credit is
unambiguous, and the one step that would have let my own patch land — signing a
CLA — is a legal act this pipeline cannot perform on the user's behalf. Sixteenth
resolution in the series, and the second (after
[EvoScientist](evoscientist-evoscientist.html)) where a filing concrete
enough to be *adopted* outlived my ability to land it myself.

---

*Scanned locally with [AI PatchLab](https://github.com/elfrost/ai-patchlab).
No source code left this machine, no AI provider was contacted, and no paid API
was called.*
