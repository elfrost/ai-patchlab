---
layout: default
title: "experientiallabs/experiential: security scan"
date: 2026-09-15
---

# experientiallabs/experiential — security scan

**Repository:** [experientiallabs/experiential](https://github.com/experientiallabs/experiential)
**Commit scanned:** `4611bc7`
**Scan date:** 2026-09-15
**Disclosure status:** reported privately — detail withheld pending maintainer response

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 28 |
| Medium | 46 |
| Low | 0 |
| Info | 3 |

**77 findings. One real, reported privately.**

## Why this target

An **open-source gateway and router for agent workflows** — 4.9k★, Apache-2.0,
created in June 2026 and moving fast. It fronts hosted, BYOK and local models
behind one OpenAI-compatible API, controls which identities may use which models
and how much they may spend, and holds the operator's own provider keys to do it.

Picked on responsiveness: 48 issues closed in 60 days and three distinct humans
merging PRs. It is also the most interesting *shape* the shortlist offered. Most
targets in this series are one language; this one is a Python control plane
wrapped around a **34,011-line Rust data plane** (`axum`, PyO3), and the split is
not cosmetic — the Rust owns sockets and streaming, the Python owns authorization.
A scan that only reads Python reads half the program, and the half it skips is
the half holding the listener.

## The finding: a scope that widens when the credential is removed

Withheld until the maintainers have responded. Reported privately through GitHub
private vulnerability reporting ([GHSA-x853-p24r-pw58](https://github.com/experientiallabs/experiential/security/advisories/GHSA-x853-p24r-pw58),
in triage), because the project has PVR enabled and an [enabled private channel is
signalled consent](mims-harvard-tooluniverse.html) even where no `SECURITY.md`
exists — and there is none here, at the root, in `.github/`, in `docs/`, or on the
published docs site.

What can be said about the class without handing over a recipe:

**A read surface on the loopback control plane answers an unauthenticated caller
with a broader scope than it gives a caller who presents a valid key.** The
branch is taken on a condition the caller fully controls — whether to send the
credential header at all — and the branch carrying *less* proof of identity is
the branch carrying *more* authority. That is the
[conditional-verification shape](sentelabsai-openexecutive.html) with its sign
flipped: not an auth check that can be skipped, but an auth check whose *absence*
is a documented mode.

The behaviour is not a bug in the sense of code disagreeing with intent. The
project documents it, accurately, in its own architecture reference. **What the
report disputes is not the behaviour but the stated consequence** — the
[hardest variant of contract-versus-artifact](superlinked-sie.html), where docs
and code agree on what happens and disagree on what it costs. The design rests on
a confinement argument — the gateway "binds only `127.0.0.1`" — and loopback is
doing more work in that argument than it can bear. It does not authenticate the
local *user*, and without `Host` validation it does not keep out a *browser*
either.

**The differential that makes it worth a maintainer's time is intra-repo.** The
same process ships a credential store whose module docstring calls it an
"Atomic, **user-only** `auth.json` store", and which earns that adjective:
`0o600` on the file, `0o700` on the directory, a symlink check, `os.fchmod` on
the descriptor *before* any bytes are written, atomic `os.replace`. That is a
careful, deliberate statement that **other local users are not trusted**. The
report's whole argument is that one process should not answer that question two
different ways. This is the [sibling-differential form](zilliztech-memsearch.html)
that has been the most adoptable evidence in this series: it does not import an
external rule, it shows a project its own standard.

Reported at **Low/Medium**, argued down on purpose. Nothing exposed is a
credential or a prompt — the project's "content-free" claim is accurate, and I
checked the schema rather than taking it on faith. The disclosure is operational
metadata. The report says so in its own summary, and names the browser path's
real costs (DNS rebinding is not free, and Private Network Access is gradually
raising its price) rather than selling the scarier half.

### The fix was left as a question

Three options were offered, in increasing order of disruption: validate `Host`
on every route; invert the branch so that more proof of identity never yields
less data; or, if neither is wanted, document the trust assumption so operators
on shared hosts know which switch to flip. A PR was offered for the first and
**not opened unprompted**, because which of the three is right depends on who the
maintainers think the gateway's local callers are — and that is
[a product decision, not a patch](theroyallab-tabbyapi.html).

## The control that made the finding checkable

The verification ran against the **shipped PyPI wheel**, not the source tree: a
stub control plane handed to the real `exp_gateway_native` binary, echoing back
the scope the Rust chose per request. Three blocks, and the two that decide it
are the controls rather than the finding:

- **A negative control** — the same request with a foreign `Host` header. It
  *could* have returned 400 or 421. It did not. A probe that cannot come back
  "no" proves nothing, and this series has [published the ones that came back
  clean](langroid-langroid.html).
- **A positive control** — an authenticated `/v1` route with the credential
  removed, which returns a correct **401**. This is the block that matters most
  for triage, because it proves the auth machinery is *not broken*. Every
  request-serving route on the API surface fails closed. The finding is about a
  deliberate, scoped exception, and saying so plainly is what separates a report
  a maintainer can act on from one they have to defend against.

A first attempt at verification failed for an unrelated reason worth passing on:
`pip install experiential` then `exp` **crashes on Windows**, because
`exp/cli/providers/experiential_cloud.py:19` does an unconditional top-level
`import termios` — a Unix-only stdlib module. Not a security issue; included in
the report as a courtesy.

## What the other 76 findings were

**Zero findings in 34,011 lines of Rust.** Semgrep opened all 72 `.rs` files and
returned nothing on any of them — and the one real finding of this scan lives in
`server.rs`. This is the most concrete statement of the coverage gap the series
has produced: not a tool failing to open a file, but a tool opening the file and
having no rule that could express the question. No ruleset in the stack knows how
to ask "does this route's scope widen when a header is absent?"

**Two active-harm false positives on the best-written file in the repository.**
Semgrep flagged `exp/common/auth/store.py` twice — once for a credential leak
into a log, once for insecure file permissions. Both are wrong, and both are
wrong in the [direction that does damage](realiti4-claude-swap.html):

- The "credential leak" is a `logger.warning` that prints a **path** and an
  `OSError` when a `chmod` fails. The word *credential* is in the message; the
  credential is not. The [domain-noun collision](superlinked-sie.html) again —
  same pun that made 23 ML tokenizer tokens look like leaked secrets last scan.
- The "insecure file permissions" hit is the line `os.chmod(directory,
  _DIRECTORY_MODE)` where `_DIRECTORY_MODE = 0o700` and `_FILE_MODE = 0o600`.
  The scanner flagged the project's own hardening as the vulnerability. Acting on
  that recommendation would **loosen** it.

That is the third scan in a month where `0o600`/`0o700` drew a fire-and-loosen
recommendation. It has earned a standing rule rather than a per-scan note.

**25 SQL findings, all of them the identifier FP.** Twelfth appearance of the
series' most persistent cluster. Two reads settle it: the flagged f-strings
interpolate a `predicate` built entirely from **hardcoded literals** — the widest
of them is `" AND i.identity_id = ?"` — and every value travels separately as a
bound `?` parameter. Data bound, identifiers static, nothing reachable.

**16 secret hits, 13 in `*_test.py`.** Of the rest, the notable one is
`POSTHOG_PROJECT_API_KEY` in `telemetry.py`, a PostHog *project* key — the
write-only ingest kind designed to ship inside client JavaScript. Public by
construction, not a leak.

**18 GitHub Actions mutable-tag rows, correctly inert.** Both workflows trigger
on `pull_request`, not `pull_request_target`, with `permissions: contents: read`
— so a fork PR runs with no secrets and nothing to steal. The
[trigger is what sets the severity](mai-with-u-maibot.html). Credit where due:
the one action that actually builds and publishes wheels, `PyO3/maturin-action`,
is already **SHA-pinned with a version comment**. They know the practice and
applied it where it counts.

**The two dependency Highs split on reachability, in opposite directions.**
Neither `httpx2` nor `transformers` is a declared dependency; both arrive
transitively, and `uv.lock` covers every extra including `dev` and `sft`.

- `transformers==5.5.4` carries a `save_pretrained` path-traversal CVE. In this
  repository `save_pretrained` is **never called** and `transformers` is **never
  imported**. Unreachable — [the vulnerable function is the gate](plastic-labs-honcho.html),
  not the version string.
- `httpx2==2.10.0` carries three advisories and *does* ship, because `openai` —
  a declared base dependency — pulls it. But the exposure belongs to the locked
  path: a `pip install experiential` resolves floors and lands on a current
  release, while `uv sync` gets the pin. [Which install path did the tool
  describe?](langroid-langroid.html) — the answer decides whether this is a user
  problem or a contributor problem. It is the latter, and it is in the report as
  a note.

## Notes on the tool

- **The unaudited-lockfile meta finding overstated the gap for the third run
  running.** `dependency-scan` reported that `uv.lock` went unaudited because
  pip-audit does not read it — and Trivy had read it in the same run, which is
  precisely where the `httpx2` and `transformers` rows came from. This was
  already a backlog item after [langroid](langroid-langroid.html) and
  [bub](bubbuild-bub.html); three consecutive scans makes it the top one. The
  scanner holds both tools' target lists and still will not cross-check them.
  It should stay silent when a sibling tool covered the file, or better, report
  where the two paths' *versions* disagree — which is the genuinely useful signal
  and the one it keeps burying.
- **A polyglot repository needs a language-coverage line in the report.** The
  scan opened 800 Python files and 72 Rust files and reported findings from
  exactly one of those languages. Nothing in the output says so. A report that
  ends "77 findings" when 34k lines produced structurally zero is not lying, but
  it is letting the reader infer coverage that does not exist. A per-language
  scanned/finding breakdown would have made this scan's central fact visible
  without any new rule.
- **Semgrep's five rule timeouts were all on `*_test.py` files**, so first-party
  coverage is real. Reported via the `errors` array, as always —
  [`paths.skipped` was 0](tracecathq-tracecat.html) here too, and would have said
  "clean" if believed.
- **23 of 77 findings are in test files**, which no severity column reflects.
  The [ownership split](klavis-ai-klavis.html) asked for in earlier scans would
  have moved nearly a third of this report into its own bucket before a human
  read a line.

## Disclosure timeline

- 2026-09-15 — scan run at `4611bc7`
- 2026-09-15 — curation complete: 1 real finding, quality gate met
- 2026-09-15 — reproduced against the shipped PyPI wheel with a positive and a
  negative control
- 2026-09-15 — reported privately via GitHub private vulnerability reporting
  ([GHSA-x853-p24r-pw58](https://github.com/experientiallabs/experiential/security/advisories/GHSA-x853-p24r-pw58)),
  accepted into triage; report offers to withdraw this page entirely if the
  maintainers prefer
- *pending* — maintainer response
- *pending* — public detail, once fixed or after a reasonable window

## Reproduce

```bash
git clone https://github.com/experientiallabs/experiential /tmp/scan-target
.venv/Scripts/python.exe scanner/run_scan.py \
  --repo /tmp/scan-target \
  --reports-dir ./reports/experientiallabs-experiential \
  --min-severity medium
```

---

## More from this series

- **Previous scan:** [superlinked/sie](superlinked-sie.html) — 2026-09-14, 1 real
- [Every scan in the series]({{ '/' | relative_url }}) — 105 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 24 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — 40 of them, published as they were
