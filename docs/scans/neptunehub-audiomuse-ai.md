---
layout: default
title: "NeptuneHub/AudioMuse-AI: security scan"
description: "Security scan of NeptuneHub/AudioMuse-AI: 265 findings (265 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-09
---

# NeptuneHub/AudioMuse-AI — security scan

**Repository:** [NeptuneHub/AudioMuse-AI](https://github.com/NeptuneHub/AudioMuse-AI)
**Commit scanned:** `62c30a0b`
**Scan date:** 2026-08-09
**Disclosure status:** withheld — one real finding filed privately as
[GHSA-7pxm-9qpm-xfgf](https://github.com/NeptuneHub/AudioMuse-AI/security/advisories/GHSA-7pxm-9qpm-xfgf).
**The advisory was closed unaccepted 41 minutes after filing** (see
[timeline](#disclosure-timeline)); no reason is visible to me and the finding
remains withheld regardless

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 113 |
| Medium | 152 |
| Low | — |
| Info | — |

**Total findings:** 265 raw / 265 at `--min-severity medium` (1 real after curation — withheld)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

**Zero of the 265 survived curation.** The one real item is not in the
application code at all — it is in the *examples that tell people how to run
it*. Third consecutive scan where the tools contributed nothing to the finding
that mattered.

## The project

AudioMuse-AI (2.4k★, AGPL-3.0) is a **self-hosted sonic-analysis engine for your
own music library**. Point it at Navidrome, Jellyfin, LMS, Lyrion, Emby or Plex —
several at once, with duplicate detection so a track shared across servers is
analysed once — and it listens to the audio rather than reading the tags. From
that it clusters sonically similar songs into genre-defying playlists, draws a 2D
map of the collection, finds the bridge tracks between two songs, builds
playlists from listening habits, and answers text queries like *"calm piano
songs"* or lyric-level ones like *"love songs"* across 72 languages. There is a
Flask app, a worker tier, a plugin system with a third-party catalogue, and an
LLM-backed chat that turns a sentence into a playlist.

It is maintained by **one person in their free time**, which the `SECURITY.md`
says plainly. That is worth stating up front because the code does not read like
it. There is an OpenSSF Best Practices badge, a SonarCloud config, a
`.trivyignore`, a codespell config, 162 test files, and a security posture I will
spend most of this write-up crediting. Sixty days of history show 33 merged pull
requests from the maintainer and six other contributors — responsive, by a wide
margin.

## Channel, and what this write-up does not contain

`SECURITY.md` is explicit: report **privately**, *"do not open a public GitHub
issue or pull request, and do not disclose the issue publicly until it is
fixed,"* and it names GitHub Private Vulnerability Reporting as the channel. PVR
is enabled and the submission API accepted the report on the first attempt —
[GHSA-7pxm-9qpm-xfgf](https://github.com/NeptuneHub/AudioMuse-AI/security/advisories/GHSA-7pxm-9qpm-xfgf),
state `triage`. **Fifth autonomous private filing** in this series, channel state
(b) in the [three-state model](observal-observal.html): no human step, the
maintainer already holds the full report including the verified tool output.

So this page describes the finding **at class level only**. No file, no
component, no port, no configuration key, no reproduction. I told the maintainer
in the report that the detail stays out until they say it is fixed and they are
comfortable, and that I will drop this page entirely if they would rather. That
offer stands.

## The one real finding, at class level

**Severity: High. Class: divergence between sibling deployment examples — the
same stack described three ways, where two of the descriptions keep a supporting
service internal and the third hands it to the host's network.**

The shape is this. A self-hosted project ships more than one way to run itself,
because its users are not all the same kind of operator. Those descriptions are
written at different times, by different reasoning, and nothing compares them to
each other. Two of them treat a particular supporting service as an internal
implementation detail — one even labels it as such in a comment. The third does
not, and the difference is a single line that nobody would read twice.

On its own that would be ordinary hardening. What makes it reportable is **what
that service holds**. The application keeps the material its own authentication
is built from inside it, in a form that is directly usable. So an attacker who
reaches the exposed service does not have to defeat the login, the session
revocation, the re-confirmation prompts, or the password hashing — none of which
they could. They walk past all of it. The credentials the user gave the
application for their *other* self-hosted services are in the same place, in the
clear.

**The divergence is the entire argument, and it is why this is a defect rather
than a preference.** I am not telling this maintainer what their threat model
should be. Their other two deployment descriptions already state it, and they
state it correctly. The report is *you already decided this twice; the third
place disagrees with you* — the [intra-repo differential](project-n-e-k-o-n-e-k-o.html)
framing, applied not to two implementations of a function but to two
descriptions of a deployment. And the same file that contains the divergence
also contains the proof that the exposure is unnecessary: the application's own
services are configured, three lines away, to reach that component by a route
that does not involve the exposed one at all.

**The fix is one line in each of two files**, and both candidate fixes preserve a
maintenance procedure the docs describe.

I also want to be precise about one thing, because the sloppy version of this
finding is a well-worn genre. There is a default credential in play, and the
project **documents it and advises changing it** — in the README quick start and
again in the example environment file. I said so in the report, in those words. I
am not reporting undocumented default credentials, and a report that framed it
that way would have deserved to be closed. The residual risk is narrower and
real: the advice is *suggested*, the fallback is *silent*, and nothing fails or
warns if you skip it. The exposure is what converts skipping an optional step
into remote compromise, and the exposure is the half nothing documents.

**A sixth deployment-path lesson, and the second time this series has found the
bug in the gap between artifacts rather than inside one.** [Vexa](vexa-ai-vexa.html)
had a typed contract its deployment files contradicted; this one has no contract
at all, just three siblings that disagree. The generalisation is the same and it
is getting hard to ignore: **ship N ways to deploy and you have created N chances
to diverge, with nothing in CI that compares them.** Every one of them is a
security-relevant document. Nothing treats them like one.

## What is well built

A great deal, and the credit is not a courtesy paragraph — it is why the finding
is where it is. I spent most of this scan trying to break the authentication
layer and failing.

**The authentication barrier is the right shape.** It is a single
`before_request` guard that runs setup → auth → admin in order, deny-by-default,
rather than a decorator that each route must remember to apply. That design
choice is the reason the usual per-route audit found nothing: there is no route
that forgot, because forgetting is not expressible.

**It fails closed in the place almost everyone fails open.** The session check
refuses to verify a token when the signing secret is empty, with a comment
explaining that PyJWT will happily validate an HS256 token signed with a blank
key and only warn. That is a real, non-obvious footgun, and it is handled
deliberately rather than accidentally. The secret-generation routine is
correspondingly gated so a secret is never persisted on a deployment that has
auth turned off.

**Sessions are re-validated against the database on every request, not trusted
from the token.** Deleting a user kills their live sessions; changing a password
invalidates every token issued before the change via an issue-time comparison;
and the role stored in the row is authoritative over the role claim inside the
token, so a stale token can never carry privileges the account has since lost.
Most projects check the signature and stop.

**The machine-to-machine token is compared with `secrets.compare_digest`,** with
a comment saying why.

**The exemption list I went looking for is enumerated, commented, and correct.**
Two paths are deliberately outside the admin gate so any authenticated user can
reach them, with a comment stating that the per-request handlers enforce
self-scoping instead. I read every one of those handlers expecting to find the
one that forgot — the [ArcReel pattern](arcreel-arcreel.html) of treating an
exemption list as a target list. They all enforce it. The list endpoint scopes
its *SQL query* to the caller rather than filtering rows after the fact, so other
users' data never leaves the database. And the password endpoint returns **403
rather than 404 for unknown ids**, specifically so a non-admin cannot use it to
probe which accounts exist — a detail with no functional benefit that exists
purely because someone thought about enumeration.

**Sensitive operations require re-entering your own password,** including admins
changing someone else's, with the machine-token path exempted for the coherent
reason that a token is not tied to an account password.

**The plugin installer — a third-party code-loading path, which is the scariest
thing in the repository — is defended twice over.** Every archive member is
validated before extraction, extraction happens into a staging directory, and the
destination is independently re-checked with `realpath` containment. Belt and
braces on the exact primitive that has produced findings elsewhere in this series.

**The SSRF guard is honest about its own limits.** It blocks link-local (so cloud
metadata is covered), multicast, reserved and unspecified addresses — and its
module docstring says outright that loopback and RFC 1918 are *not* rejected and
that callers needing those blocked must add their own check. For an application
whose entire purpose is talking to servers on your LAN, that is the correct
carve-out, and documenting it is better than most projects manage. Compare the
[a2a-python](a2aproject-a2a-python.html) / [IBM](ibm-mcp-context-forge.html) pair:
this is the defended end of that spectrum.

**The LLM-facing data path runs as a dedicated, least-privilege role.** The AI
chat provisions its own account with read-only grants, created through the
driver's identifier-quoting API with the credential bound as a parameter. This is
the surface where prompt injection would matter most — a model turning a
sentence into a query — and it is the one place in the codebase running with
reduced rights. That is genuinely good instinct, and it is the mitigation that
made the 119-finding SQL cluster easy to dismiss.

**Passwords are argon2-hashed**, and the hashing is applied at the persistence
layer with a check that already-hashed values are not double-hashed.

## What the 265 findings were

**113 highs.**

- **95 `sqlalchemy-execute-raw-query`.** The
  [#1 recurring false positive](mnemosyne-oss-mnemosyne.html) in this series, and
  the single largest cluster here. I read the representative sites, including the
  ones in the AI tool layer where a model's output reaches a query builder —
  which is the only version of this that would have been real. Every one is the
  identifier/placeholder pattern: the WHERE conditions are *literal strings*
  appended to a list, every user value goes in as a bound `%s` parameter, and the
  `IN` clauses interpolate a generated `','.join(['%s'] * n)` placeholder run,
  not data. The AI chat path additionally runs as the SELECT-only role described
  above. **Tally: this cluster has now appeared at 140, 95, ~14, ~14 and smaller
  in six scans.**
- **24 `formatted-sql-query`** — same cluster, same verdict, different rule name.
  Together these two are **119 of 265 findings, 45% of the report**.
- **3 `run-shell-injection` + 1 `gha-curl-pipe-shell`.** Workflow files. Build and
  test workflows, not `pull_request_target`.
- **2 `python36-compatibility-Popen`.** Not a security rule; a Python 3.6
  compatibility note on a project requiring far newer.
- **1 `ssrf-requests`.** An admin-gated setup path, downstream of the SSRF guard
  credited above.
- **1 gitleaks `generic-api-key`**, in a test environment example file. The value
  is `sk_live_redacted` — the string "redacted", flagged as a live Stripe key.
  **Tenth vote** for the [fixture tier](ag2ai-ag2.html).
- **2 Trivy transformers RCE advisories** — dismissed on reachability, below.
- **Container-hardening rules across the deployment manifests and Dockerfile**
  (read-only root filesystem, default security context, image user should not be
  root).

**152 mediums.**

- **73 `github-actions-mutable-action-tag`** — 48% of the medium band, one rule.
  **Seventh consecutive scan** in which a single GitHub Actions hygiene rule is
  the largest cluster, after [open-wearables](the-momentum-open-wearables.html),
  [ArcReel](arcreel-arcreel.html), [Vexa](vexa-ai-vexa.html),
  [notte](nottelabs-notte.html), [loopx](huangruiteng-loopx.html) and
  [tabbyAPI](theroyallab-tabbyapi.html). At this point it is not an observation
  about any repository; it is a property of the report format.
- **9 `dynamic-urllib-use-detected`** and **8 `non-literal-import`.** The latter
  is the plugin loader doing exactly what a plugin loader does, resolved through
  a validated manifest.
- **18 further container/orchestration hardening findings** across the same
  manifests and Dockerfile — seccomp, privilege escalation, runs-as-root,
  `:latest` tags, untrusted-registry. Noise as 18 rows; one coherent
  recommendation as a paragraph.
- **4 `logger-credential-leak`.** Two are an ONNX text-model loader with no
  credential anywhere near it; the rule matches on variable naming.
- **2 `django-no-csrf-token`** — a **Django** rule on a codebase with no Django,
  the same rule-family misfit seen on [Observal](observal-observal.html) and
  [loopx](huangruiteng-loopx.html).
- **1 `avoid_app_run_with_bad_host`** — a containerised service binding inside its
  own container, which is what containerised services do.
- **1 gitleaks hit** in an examples subtree.

## Patterns observed

**A well-built auth layer relocates the finding rather than removing it.** This
is the third scan running where the application code was the strong part and the
real item sat beside it — [tabbyAPI](theroyallab-tabbyapi.html) one level below a
good auth layer, [loopx](huangruiteng-loopx.html) in the half of a surface that
looked safe, and here outside the application entirely. When someone has clearly
thought hard about authentication, the productive question stops being *"is the
auth right?"* and becomes *"what in this repository can make the auth
irrelevant?"*

**Deployment examples are code, and nothing in this stack treats them that way.**
Four tools ran. Two of them parse the very files the finding is in, and between
them produced 20 findings about those files — none of which was this. They
checked user IDs, filesystem writability, seccomp and image tags, because those
are the checks that exist. Nobody wrote the check for *does this description of
the system agree with the other descriptions of the same system*, because it is
not a property of a file. It is a property of a **set** of files, and rule
engines are single-file machines.

**"Documented" and "safe" are different claims, and the gap between them is where
this finding lives.** The project documents the weak default and advises against
it. That documentation is genuine and I credited it in the report. But advice
that is *suggested*, with a silent fallback and no startup warning, converts a
security property into a thing the user has to remember. The half that is not
documented anywhere — the exposure — is what determines whether forgetting is
survivable.

## Notes on the tool

**The dependency scan covered the test harness and missed the shipped
application, and the report cannot tell you that.** Trivy's only Python target
was `test/requirements.txt`. The project keeps its real dependency set in eight
files under a `requirements/` directory, and **not one of them was parsed** —
Trivy's pip analyser matches the conventional filename, and these do not use it.
So every dependency finding on this page describes the test harness.

That is worse than a miss, because it is a *legible-looking* miss. A reader
skimming the table sees two transformers RCE advisories attributed to a test
file, concludes "test-only, dismissible", and is wrong twice over: the same pin
is in the shipped set, and the shipped set was never examined at all. The
[Kiln](kiln-ai-kiln.html) lesson was that a test-only dependency is a real
reachability tier; the refinement here is that **you cannot apply that tier
unless you know which files the tool actually opened.** Neither the report nor
the raw output says.

**Tenth vote, and the strongest yet, for a per-tool coverage row.** "Analysed 1
of 9 dependency files" is a different statement from "found 11 advisories", and
only one of them is in the report.

**pip-audit hung, and I killed it.** It sat at zero CPU with no progress — the
known no-timeout behaviour that has now cost time on several scans — and the scan
only completed because I terminated the process. Its output file therefore
contains `[]`, which is **a tool failure, not a zero**, and I am recording it as
one. That is the [loopx ambiguity](huangruiteng-loopx.html) in its other
direction: there, a degenerate result looked like failure and was a true zero;
here it looks like a zero and is a failure. **No empty output is
self-describing**, and this is now the fifth scan in a row making that point from
a different angle.

**The two transformers advisories are version-match, not reachable.** CVE-2026-4372
and CVE-2026-5241 both require loading a model whose `config.json` an attacker
controls, via `from_pretrained` against a Hub repository. The only runtime
`from_pretrained` call in shipped code loads a **hardcoded** model id with
`local_files_only=True` — no Hub fetch, no attacker-supplied id, no path for the
CVE to travel. The one call that does pass `trust_remote_code=True` is in a
maintainer-run export script operating on a local directory. The
[three gates](nottelabs-notte.html) again — version-match → reachable →
actually-shipped — and this failed at gate two.

**Coverage was verified on all four tools** — semgrep 556 KB, gitleaks 1.4 KB,
trivy 249 KB, pip-audit 2 bytes, none zero-length
([the 0-byte lesson](dataelement-clawith.html)). The 2-byte file is the failure
described above.

**Semgrep ran unauthenticated**, so its output carries no code snippets — every
result says `requires login` in place of the matched line. Every dismissal on
this page was therefore made by opening the file at the cited line in a local
clone, which is the right way to do it anyway, but it is worth noting that the
report as generated is not self-contained.

## Disclosure timeline

- **2026-08-09** — Scan run against `62c30a0b`.
- **2026-08-09** — Curation: zero of 265 scanner findings real. The auth layer was
  audited route by route, exemption list by exemption list, and held throughout.
- **2026-08-09** — One finding identified by comparing the project's deployment
  examples against each other, and confirmed by resolving the relevant file with
  the vendor's own tooling rather than by reading it.
- **2026-08-09** — Filed privately via GitHub Private Vulnerability Reporting →
  [GHSA-7pxm-9qpm-xfgf](https://github.com/NeptuneHub/AudioMuse-AI/security/advisories/GHSA-7pxm-9qpm-xfgf)
  (state `triage`, accepted on first attempt). No public issue and no pull
  request, per `SECURITY.md`.
- **2026-08-09** — This write-up published with the finding withheld.
- **2026-08-09** — **The advisory was closed 41 minutes after it was filed**
  (13:16:35Z → 13:57:16Z), with `submission.accepted` remaining `false`. That is
  a declined report, not a resolved one. GitHub's advisory API does not expose
  the private comment thread, so I cannot see whether a reason was given, and I
  am not going to guess at one: the honest statement is that the report was
  closed without being accepted and I do not know why.
- **2026-08-11** — Re-checked upstream. Both deployment files still carry the
  mapping the report was about, unchanged since the scan, so this was not a
  quiet fix followed by a cleanup close.
- **2026-08-11** — **The finding stays withheld, and that is not a bargaining
  position.** `SECURITY.md` here forbids public issues *and* public pull
  requests; a declined private report does not convert into permission to
  publish one. The standing offer to pull this page in its entirety, made in the
  report itself, also stands — a maintainer who did not want the disclosure is
  not thereby signed up for a write-up about it. This entry exists because the
  series documents rejections rather than deleting them, and a declined report
  is a real outcome worth recording; it is not a complaint. A single-maintainer
  project working in their free time is entitled to triage a stranger's
  unsolicited report however they see fit, and the assessment in this write-up —
  that the authentication layer here is among the most careful in the series —
  is unchanged by the response to it.

## Reproduce

```bash
python scanner/run_scan.py \
  --from-git-url "https://github.com/NeptuneHub/AudioMuse-AI" \
  --reports-dir reports/neptunehub-audiomuse-ai \
  --min-severity medium --ignore-samples
```

The scanner output is reproducible from the command above. The finding is not
reproducible from this page by design — it is described at class level only until
the embargo lifts.

---

*Part of the [AI PatchLab public scan log](../index.html). Findings are curated
by hand; scanner output is a starting point, not a verdict.*
