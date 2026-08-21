---
layout: default
title: "roflcoopter/viseron: security scan"
description: "Security scan of roflcoopter/viseron: 399 findings (399 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-18
---

# roflcoopter/viseron — security scan

**Repository:** [roflcoopter/viseron](https://github.com/roflcoopter/viseron)
**Commit scanned:** `59b25659` (master at scan time; latest release v3.6.0)
**Scan date:** 2026-08-18
**Disclosure status:** **withheld** — one real finding, reported privately
through GitHub private vulnerability reporting as `GHSA-5r5m-c4m6-jfmf`.
**Accepted by the maintainers on 2026-08-21**: the submitted report was
converted into a draft advisory (`submission.accepted: true`, state
`triage` → `draft`), the **medium** severity was kept exactly as filed, CWE-863
(incorrect authorization) was assigned, the affected range was recorded as
`<= 3.6.0`, and the reporter was credited. No patched version is published yet,
so the finding stays withheld — described here at class level only.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 72 |
| Medium | 327 |
| Low | — |
| Info | — |

**Total findings:** 399 above the medium floor (1 real after curation —
**withheld**; **zero** of the 399 scanner findings represented it).

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

## The project

Viseron (3.4k★, MIT) is a **self-hosted, local-only NVR with computer vision**.
It ingests RTSP camera streams, runs object detection, motion detection, face
recognition and licence plate recognition against them, records to a tiered
storage hierarchy, and serves a React dashboard over a Tornado web server. It
has been going since 2020, which for this series is unusually old — most targets
are eighteen months old at most.

It is also, structurally, a project that handles unusually sensitive data. An
NVR knows who walked past which door and when. Viseron takes that seriously
enough to ship a per-user access model: an administrator can give an account a
role (`admin` / `write` / `read`) *and* a list of assigned cameras. The admin UI
labels that field, in the product's own words, `"Cameras - Empty gives access to
all cameras"`.

The maintainer is active and the project is not a solo ghost: 17 merges from the
maintainer plus four distinct human contributors in the last 60 days, 15 issues
closed in the same window. That cleared the responsiveness pre-check
comfortably.

There is **no `SECURITY.md`** — not at the root, not in `.github/`, not in
`docs/`, and not on the published documentation site. But private vulnerability
reporting is **enabled** on the repository. Per the rule this series has settled
on, a deliberate opt-in outranks a missing policy file: enabling that toggle is
the maintainer saying *send it here*. So the real finding went there and not
into a public issue.

## What this write-up does not contain

The one real finding is under private report and is not described below. No
component, no mechanism, no file path, no reproduction. What can be said is the
class:

> An authorization gap. A per-user access boundary that the project defines,
> documents in its own admin UI, and enforces consistently across most of its
> surface is not applied on one code path. An authenticated account holding the
> **lowest** available role, and explicitly granted access to only a subset of
> resources, can observe data belonging to the resources it was not granted.
> Confidentiality only — no write or privilege-escalation path. Not reachable by
> an unauthenticated visitor.

If it is fixed, or if the maintainer would rather it were published, this page
gets the detail and a dated timeline entry. If the report goes stale, the same
90-day convention this series has used throughout applies.

## The channel, and a correction worth publishing

This scan produced a **methodology finding about GitHub's own API** that
invalidates a belief two earlier entries in this series recorded, so it goes
near the top rather than buried in the tooling notes.

Viseron reports `private-vulnerability-reporting: {"enabled": true}`. The first
submission to `POST /repos/{owner}/{repo}/security-advisories/reports` returned
**HTTP 500**. So did the second and third. Two previous scans in this series
(repowise, Vexa) hit exactly that wall and were filed under a category I had
been calling "PVR enabled but the API is broken" — a dead channel with a live
toggle.

That category appears to have been wrong, and here is the control that shows it.
An empty payload returns a clean, correct **422**:

```
Invalid request.
Invalid input: object is missing required keys: summary, description.
```

So the endpoint is reachable, the token scopes are right, and the request is
being parsed. The 422 names exactly two required keys: `summary` and
`description`. A payload with both — and nothing else — returns **500**. Adding
the `vulnerabilities` array, which the API documents as *optional* and which the
422 does not mention, returns **201 Created**.

```
summary + description                      -> 500
summary + description + cwe_ids            -> 500
summary + description + vulnerabilities    -> 201
```

The channel was never broken. The payload was incomplete in a way the API's own
validation error actively misdirects you about: it tells you which fields are
missing, that list is wrong, and the failure mode for the field it omits is a
server error rather than a validation message. Anyone reporting a vulnerability
through this API for the first time will read the 500 as "they have disabled
it" and walk away — which is what I did, twice, and it may have cost two
maintainers a report they had explicitly opted in to receive.

The rule that replaces the old one: **a 500 from a private-reporting endpoint is
a claim about your payload until a 422 control proves otherwise.** Send the
empty payload first. It costs nothing, it files nothing, and it tells you
whether the door is locked or you are holding the key wrong.

*(A second, smaller lesson from the same minute: the confirming request I ran to
check what had been created re-POSTed the payload instead of only listing it,
which filed the report twice. The duplicate, `GHSA-3ffc-5g6c-9g3j`, could not be
withdrawn — the API only lets the repository owner change a report's state — so
it was retitled in place to point at the real one. A verification step that
mutates is not a verification step.)*

## Patterns observed

**This is the best-defended authentication layer this series has scanned.** That
is worth saying plainly, because the finding count above says the opposite and
the finding count is noise.

Two of the scariest-looking results are both defences that a scanner cannot
recognise as defences:

`auth.py:752` trips `unverified-jwt-decode`, a rule that is right often enough
to be worth having. Here it is the standard two-pass pattern — decode without
verification *only* to read the `iss` claim, so you know which key to fetch,
then always run a real verified `jwt.decode` with that key, the issuer and a
leeway. The code then goes a step further than the pattern requires: when the
issuer is not found it verifies against a **decoy key** generated at startup,
purely so a bad issuer and a bad signature take the same amount of time. A rule
that fires on `verify_signature: False` cannot see the second decode; it
certainly cannot see the decoy.

`auth.py:362` trips a hardcoded-bcrypt-hash secret rule. It is a dummy hash used
to make failed logins cost the same as successful ones. This series has learned
to check whether a declared timing defence is actually *invoked* — the "inert
security flag" pattern, where the guard exists and nothing calls it. It is
invoked, at line 376, on the exact path where no user matched. The defence is
real, and the scanner reported it as a leaked credential.

The same care shows up structurally. The REST dispatcher defaults `requires_auth`
to **True** and makes routes opt *out*, which is the correct direction for that
default. Role checks fall back to a per-method table when a route does not
declare one. XSRF is enforced precisely when the credential is a cookie and the
method is state-changing, and skipped for token clients where CSRF is not a
threat — a conditional that is easy to get backwards and is not backwards here.
Personal access tokens are explicitly refused the browser cookie-binding path.

Which is exactly why the one real finding is interesting, and why no rule found
it. It is not a missing check in code that has no checks. It is a boundary
enforced almost everywhere and absent from one path. The signal that it is a
defect rather than a decision is entirely **intra-repo**: the same data, reached
a second way, is guarded. You cannot get there from a pattern database. You get
there by listing the ways in and comparing them to each other.

**The 399 findings, honestly accounted for.** 238 of them are `RUN cd ...` in a
Dockerfile. 34 are "image user should not be root" — on an NVR container that
needs device access to talk to GPUs, VAAPI and Coral TPUs, repeated once per
build variant. 43 are mutable GitHub Actions tags. That is 315 of 399, or 79%,
from three hygiene rules firing repeatedly across a build matrix. Finding count
scales with how many build targets you support, not with risk.

Of the 56 dependency CVEs, **31 are in `docs/package-lock.json`** — the
Docusaurus toolchain that builds the documentation website. They ship to nobody.
Another 24 are in the frontend lockfile, and 20 of those are one package,
`dompurify`, which nearly became a wrong finding: `package.json` declares
`^3.2.7` and Trivy reported 3.1.7, which reads like a stale lockfile that
`npm ci` would install below its own declared floor. Reading the lockfile
directly kills it — `node_modules/dompurify` **is** 3.2.7, and the 3.1.7 is a
second, nested copy vendored inside `monaco-editor`. The app's own sanitiser,
the one actually imported by `HoverLine.tsx` and `ProgressLine.tsx`, is current.
That left exactly **one** dependency CVE in the Python runtime: scikit-learn
1.2.2, `CVE-2024-5206`.

The remaining Python hits are the familiar roster. `subprocess-shell-true` in
`data_stream` is `["ulimit", "-u"]` — a constant list, no user input anywhere
near it, and `ulimit` is a shell builtin so the shell is the point. The
SQLAlchemy `text()` in `storage/models.py` interpolates an offset string built
from `int()` arithmetic and `f"{hours:02d}:{minutes:02d}"`; only digits and a
sign can reach it, making it the tenth appearance of the parameterised-SQL
identifier family this series has now catalogued. The eight `non-literal-import`
hits are Viseron's component and domain loader, which is the entire plugin
architecture.

The one that took real work to dismiss is the **GitHub Actions template
injection**: `.github/templates/run_in_venv/action.yaml` interpolates
`${{ inputs.command }}` straight into a `run:` block. In a composite action that
is a genuine hazard, and the rule is right to flag it. But a composite action
cannot be judged from its own file — the question is what callers pass. All
seven call sites in `ci.yaml` pass hardcoded literals, and the workflow triggers
on `pull_request`, not `pull_request_target`, so a fork PR runs on the fork's
ref without secrets. Latent, not reachable. Trigger context decides, and it
decided in the maintainer's favour.

## Notes on the tool

- **The `422`-control move is now a required step**, not a nicety, and it
  belongs in the pipeline rather than in my head. Any private-reporting POST
  that returns a 5xx must automatically re-send an empty payload and compare.
  Two earlier scans were misfiled for want of a request that files nothing.
- **A verification step must not mutate.** The command that confirmed the
  advisory had been created re-sent it. Read-back and write have to be different
  code paths, and the read-back has to be the one that runs by default.
- **`pip-audit` hung again** — no output after 15 minutes on this repo, killed
  manually, and it produced `[]` on disk. That empty array is indistinguishable
  in the report from a genuine clean result. It is the fourth time this has
  happened. The runner needs a `subprocess` timeout and a distinct
  `pip-audit-timeout` finding, because "did not run" currently renders as
  "clean". Trivy covered the Python dependency surface here, so nothing was lost
  this time, which is precisely the kind of luck that hides the bug.
- **Coverage was genuinely good this run**, and worth recording as a contrast to
  the tracecat scan: 822 files scanned, `paths.skipped` 0, and 8
  `PartialParsing` errors — all on four non-Python files (`ci.yaml`, a composite
  action, a `Dockerfile`, a shell script). No first-party Python was lost. The
  coverage row reads the `errors` array, not `paths.skipped`, and this time both
  agree.
- **Nothing in the scanner's 399 results pointed at the real finding**, and
  nothing could have. Reporting the ratio honestly matters more than the ratio.

## Disclosure timeline

- 2026-08-18 — scan run against `59b25659`
- 2026-08-18 — finding reported privately via GitHub private vulnerability
  reporting: `GHSA-5r5m-c4m6-jfmf` (state: triage)
- 2026-08-18 — public post (this page), finding withheld
- 2026-08-21 — **accepted**: advisory moved `triage` → `draft` with
  `submission.accepted: true`, severity kept at medium as filed, CWE-863
  assigned, affected range set to `<= 3.6.0`, reporter credited. Acceptance is
  not resolution — no patched version yet, so this stays withheld and the row
  on the index stays *private*.

## Reproduce

```bash
git clone https://github.com/roflcoopter/viseron /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/roflcoopter-viseron --min-severity medium
```
