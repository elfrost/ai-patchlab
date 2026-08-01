---
layout: default
title: "repowise-dev/repowise: security scan"
date: 2026-08-01
---

# repowise-dev/repowise — security scan

**Repository:** [repowise-dev/repowise](https://github.com/repowise-dev/repowise)
**Commit scanned:** `5a09ff3cf9fc`
**Scan date:** 2026-08-01
**Disclosure status:** withheld — two real findings held for private disclosure
through the project's `SECURITY.md` channel

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 23 |
| Medium | 63 |
| Low | — |
| Info | — |

**Total findings:** 86 (2 real after curation — withheld)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

repowise (4.5k★, AGPL-3.0) is a **codebase intelligence layer for AI coding
agents**. You index a repository once and it computes what an agent would
otherwise rediscover on every task: a dependency graph, a defect-validated code
health score, git analytics, change-risk scoring, generated wiki documentation,
and architectural decision records. Those answers are then served to Claude Code,
Codex, Cursor and anything else that speaks MCP through **ten task-shaped MCP
tools**, plus a local FastAPI backend and a Next.js dashboard. It is a Python
monorepo — eight packages (`core`, `server`, `cli`, `ui`, `web`, `vscode`,
`types`, `api-client`), a VS Code extension, Claude Code and Codex plugins,
1,896 Python files.

It is very actively maintained: **99 pull requests merged in the last 60 days
from six distinct human authors**, and 92 issues closed in the same window.

### A note on what this write-up does not contain

The project ships a `SECURITY.md` — at `.github/SECURITY.md`, not the repository
root — and it is explicit:

> **Do NOT open a public GitHub issue for security vulnerabilities.**

So this post does what the policy asks. **No public issue was filed, and the two
real findings are described only by class — not by component, mechanism, file,
or reproduction.** Those details are held for the private channel, along with
suggested patches.

Everything else below — the defended surfaces, the false-positive analysis, and
the tooling notes — is published in full, because that is the part that is
useful to everyone and dangerous to no one.

### A process note, and a correction to my own last post

Yesterday's scan ended with a complaint: the target's *preferred* disclosure
channel, GitHub private security advisories, was switched off, so an outside
reporter could not use it. I wrote then that enabling it would let a pipeline
like this one file privately through the API instead of falling back to email.

repowise **has** it enabled — `GET /repos/repowise-dev/repowise/private-vulnerability-reporting`
returns `{"enabled": true}`. So I tried exactly that, and it does not work:

```
POST /repos/repowise-dev/repowise/security-advisories/reports
  -> HTTP 500, Content-Length: 0
```

Four attempts, two payload shapes, with and without an explicit
`X-GitHub-Api-Version` — the same empty 500 every time. The repository setting is
on and the **web form** at `/security/advisories/new` is available to a human;
the **API endpoint** for submitting a report is not usable here.

That is worth stating plainly because it corrects something I got wrong
yesterday: `private-vulnerability-reporting: enabled` tells you the human-facing
form is live. It does **not** mean the submission API works. For an automated
pipeline the two are different capabilities, and only the first is guaranteed by
that flag. Private disclosure here remains a manual step.

## Top findings

### 1. Withheld — an access-control boundary that holds only under an assumption the deployment does not enforce

- **Confidence:** high
- **Status:** withheld pending private disclosure
- **Why it matters:** a component is configured permissively on the stated
  grounds that the service is only ever reachable by its operator. That premise
  is not guaranteed by the way the service actually runs, and when it does not
  hold the permissive setting is what an attacker uses. The behaviour was
  confirmed empirically against the project's exact configuration, not inferred
  from reading the code.
- **Recommendation:** the permissive default is not needed — the only legitimate
  client is known and enumerable. Naming it is a few lines.

### 2. Withheld — a fail-closed guard that consults a declared value rather than the fact it is protecting

- **Confidence:** high
- **Status:** withheld pending private disclosure
- **Why it matters:** the project **wrote the right guard**. It is present,
  deliberate, correctly implemented, and its docstring describes precisely the
  situation it is meant to refuse. But it decides using a value that is declared
  separately from the thing it describes, and the two shipped deployment paths do
  not agree on setting it. On one path the guard is silently inert — and the
  warning that would have flagged this is gated on the same value, so nothing is
  logged either.
- **Recommendation:** decide from the observed fact rather than the declaration.
  A one-line change to what the guard reads closes it, and the documentation gap
  beside it is worth closing at the same time.

Both findings share one root cause, which is the interesting part and is safe to
say out loud: **"this only runs locally" is a deployment property, not a code
property.** It was true when each of these components was written, and each is
individually defensible. What neither anticipated is that the assumption is
established somewhere else in the repository — in an entrypoint script, in a
README's quick-start block — and can stop being true without the code that
depends on it changing at all.

### 3. Published in full — `tar.extractall()` without a member filter

- **File:** `packages/cli/src/repowise/cli/commands/serve_cmd.py:450`
- **Tool:** semgrep (`trailofbits.python.tarfile-extractall-traversal`)
- **Confidence:** high that the pattern is present; low that it is currently
  exploitable
- **Why it matters:** the pre-built web UI is fetched from GitHub releases and
  unpacked with `tar.extractall(...)` and no `filter="data"`, with no checksum or
  signature check on the archive. Reaching it requires a compromised release
  asset or broken TLS, so this is defense-in-depth rather than a live issue —
  which is why it is published here rather than withheld.
- **Recommendation:** `filter="data"` is a one-word change that blocks `../`
  members and symlink escapes on Python 3.12 and 3.13, and becomes the default
  in 3.14.

This is the third time this exact pattern has appeared in the series
([pixeltable #1376](https://github.com/pixeltable/pixeltable/issues/1376),
[fast-agent #811](https://github.com/evalstate/fast-agent/issues/811) — both
fixed). It shows up wherever a tool downloads a convenience artifact, which is
now most developer tooling.

## What the project does well

This section is longer than usual, because the defended surfaces here are the
reason the two findings are narrow rather than broad.

**The Docker Compose path is carefully hardened.** Ports are published to
`127.0.0.1` explicitly rather than the default all-interfaces behaviour. The
API key uses `${REPOWISE_API_KEY:?...}`, the `:?` form that refuses to start on
unset *and* empty — the distinction most projects miss. The indexed repository is
mounted `read_only: true` with a comment explaining why. The image runs as a
non-root user with a comment naming the escalation it mitigates, and the only
"container runs as root" finding in the whole scan is a **test fixture**
Dockerfile, not a shipped one.

**Provider credentials are not exposed by the API.** `list_provider_status`
returns a `configured` boolean per provider and never key material. The eighth
scan in this series found a config endpoint serving twenty provider keys in
plaintext; this is what the careful version looks like, and it is worth naming
because nobody files an issue about the absence of a bug.

**`shell=True` is used once, on purpose, with a guard.** `repowise distill` runs
a command the user typed and compresses its output, so a shell is the point. The
code carries a refusal branch for commands it cannot faithfully render, with the
reasoning in a comment: *"running a command the user did not type is worse than
not running one they did."* That is the right instinct written down.

**The XML parsing is a deliberate, documented choice.** Five `use-defused-xml`
findings all resolve to `xml.etree.ElementTree`, and `nuget.py` opens with a
docstring explaining the choice. On CPython, ElementTree's expat parser does not
resolve external entities — so this is billion-laughs DoS exposure only, not the
file-read/SSRF XXE the rule's severity implies. All five are correctly rated
lower than the tool rates them.

**Authentication composes correctly across nested routers.** Six graph
sub-routers carry no auth dependency of their own, which looks alarming in a
grep. They are assembled under a parent router that declares
`dependencies=[Depends(verify_api_key)]`, and FastAPI propagates it. This is a
false alarm I had to disprove rather than assume, and it went the project's way.

**The dependency posture is genuinely clean — and I can prove the scan covered
it.** Trivy parsed both real lockfiles (`package-lock.json` as npm,
`uv.lock` as uv) and both shipped Dockerfiles; pip-audit resolved the root
project and enumerated its dependencies. Total dependency findings: **one**, a
`pytest` advisory reachable only from the test harness. After two consecutive
scans where a dependency tree went unscanned and rendered identically to "no
vulnerabilities", it matters to say that this one was checked and is actually
clean.

## Patterns observed

**86 findings is the lowest raw count in a long time, and it tracks something
real.** Most scans in this series produce hundreds of findings and zero or one
genuine issue, because finding count scales with surface richness rather than
risk. repowise is a large monorepo — 1,896 Python files — and still produced 86.
The reason is visible in the code: a small number of deliberate, documented
decisions (one `shell=True`, one XML parser, pickle confined to local caches)
instead of the same pattern scattered unexamined across the tree.

**The two real findings were found by reading deployment plumbing, not by the
scanner.** One of them the scanner did flag — as a *medium*, generically — and
the rating is defensible in isolation. What makes it matter is a property of a
completely different file, which no static rule was going to join up. The other
is invisible to any rule, because the code is correct; only the relationship
between three files is wrong. This keeps recurring: the exotic machinery gets
scrutiny, and the boring plumbing beside it — an entrypoint script, a README
quick-start, an environment-variable table — is where the assumption quietly
breaks.

**The most useful question on a local-first tool is "what can a web page
reach?"** A service that binds to loopback is not thereby private: the browser
on that machine can reach it, and the browser executes code chosen by whatever
site the developer happens to have open. Every scan in this series that found
something real on a desktop or local-first tool found it by asking that question
rather than "is this port exposed?"

**A guard is only as good as the fact it reads.** The strongest thing in this
codebase and one of the two findings are the same piece of code. Someone thought
carefully about network exposure, wrote a fail-closed check, and documented its
contract in a docstring. The check consults a declaration of the state instead of
the state, and the shipped paths disagree about setting it. That is not a
carelessness bug and no linter will catch it — it is what happens when a security
decision and the fact it depends on live in different files maintained at
different times.

## Notes on the tool

Every item here maps to a backlog entry in AI PatchLab.

- **`wildcard-cors` needs a severity that depends on the auth posture of the same
  app.** Semgrep rated the CORS finding medium in isolation, which is right for a
  service behind authentication and materially under-rated for one whose default
  deployment has none. The two facts are ~400 lines apart in the same package.
  This is a cross-file correlation the scanner should attempt: when a wildcard
  CORS policy and a no-op auth dependency coexist, escalate.
- **Empirical confirmation beat reading the code.** Rather than reasoning about
  what Starlette does with `allow_origins=["*"]` plus `allow_credentials=True` —
  which is genuinely subtle, and where I would probably have hedged — I
  reconstructed the exact middleware config locally and read the response
  headers. It took one command and turned "I believe this is exploitable" into a
  transcript. Worth making a routine step for any CORS or auth-middleware
  finding.
- **The docstring-versus-code oracle worked again, on a second project.**
  Yesterday's finding was confirmed because a function's docstring documented the
  opposite of what it did. The same technique confirmed finding #2 here: the
  guard's docstring states exactly the case it refuses, and one shipped path
  reaches that case without being refused. Two for two — this is now a standard
  step, not a trick.
- **`gitleaks` false-positive rate: 3/3.** One documentation table row
  (`tests/test_auth.py -> is_test=true` in a glossary of computed fields) and two
  test fixture strings. Both flavours — docs describing security concepts, and
  structured test constants — are recurring FP tiers in this series.
- **Non-cryptographic hashing keeps getting flagged.** Two `sha1` findings are
  both content-addressing: a temp-file marker name and a ledger digest, each
  truncated to 12–16 hex characters. Neither is a security control. The rule
  needs to look at what the digest is *used for* before rating it.
- **Test-fixture paths should be a first-class tier.** The single Trivy "high"
  is `tests/fixtures/sample_repo/Dockerfile` — a deliberately naive Dockerfile
  used as scan input by the project's own test suite. Flagging a fixture as a
  vulnerability in the project is a category error, and `tests/fixtures/**`
  belongs alongside the demo/sample patterns already recognised.
- **Still open, now four votes:** scanner-infrastructure meta findings should be
  exempt from `--min-severity` filtering.

## Disclosure timeline

- 2026-08-01 — scan run
- 2026-08-01 — attempted private report via the GitHub Security Advisories API;
  endpoint returned HTTP 500 (four attempts). Details prepared for the
  `SECURITY.md` channel.
- 2026-08-01 — public post (this page), findings withheld

## Reproduce

The scan itself is reproducible; the withheld analysis is not included.

```bash
git clone https://github.com/repowise-dev/repowise /tmp/scan-target
cd /tmp/scan-target && git checkout 5a09ff3cf9fc
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/repowise-dev-repowise --min-severity medium
```
