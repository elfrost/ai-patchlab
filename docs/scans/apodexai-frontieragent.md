---
layout: default
title: "ApodexAI/FrontierAgent: security scan"
description: "Security scan of ApodexAI/FrontierAgent: 58 findings above the medium floor, every one a false positive or by design, and one real gap none of them pointed at — in the optional public demo, an artifact the project's own docs say is never served to a browser is served to the browser. Disclosed privately, detail withheld."
date: 2026-09-06
---

# ApodexAI/FrontierAgent — security scan

**Repository:** [ApodexAI/FrontierAgent](https://github.com/ApodexAI/FrontierAgent) — 1.8k★ two weeks after going public, Apache-2.0, backed by Apodex AI. An agent runtime, terminal product and evaluation suite for long-horizon research and file work: a ReAct workflow and a coordinator-plus-sub-agents "Agent Team" workflow, a task-scoped sandbox (`/inputs` read-only, `/workspace`, `/outputs`), a plugin tool tree of fifty-odd modules, and an optional Gradio demo for a Hugging Face Space.
**Commit scanned:** `1233828` (HEAD of `main` at scan time)
**Scan date:** 2026-09-06
**Disclosure status:** **Private — detail withheld.** The repository's `SECURITY.md` names a security mailbox, forbids public issues for vulnerabilities and commits to a 48-hour acknowledgment. One Low-severity finding has been filed through the repository's private vulnerability reporting channel; only the finding *class* appears below. This page will be expanded once the maintainers resolve, or after a 90-day window.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 0 |
| High | 13 |
| Medium | 42 |
| Low | 0 |
| Info | 3 (scanner meta) |

**Total findings:** 58 above the `medium` floor — **1 real after curation, withheld; zero of the 58 pointed at it.**

Coverage note: Semgrep reported six partial-parse errors, all on Dockerfiles and shell
scripts, zero rule timeouts, so Python coverage is complete. pip-audit resolved the
`pyproject.toml` floors (58 packages, no advisories) and Trivy read `uv.lock` (no advisories),
so for once the two install paths agree and both are clean.

## The one real finding — class only

**Class:** a download allow-list scoped to a parent directory (CWE-552), in a component whose
own documentation says the sibling directory under that parent is never served.

The shape, without the specifics. The optional demo deployment gives every visitor an
isolated per-session directory tree with an unguessable id, and it is genuinely well
contained: the agent's writable root is one subtree, its readable roots are enumerated, a
tool-boundary observer refuses any path outside them, three separate layers scrub the
operator's secrets out of the stream, out of tool arguments and out of downloadable files,
and the tool set is a fail-closed allow-list with a hard deny on top. The README then
records, in its own words, the one place a secret can still land on disk — a raw run
artifact written before any scrubber runs — and explains why that is acceptable: the
artifact sits outside the agent's reach, is deleted with the session, and *is never served
to a browser*.

That last clause is the one that does not hold. A single launch argument grants the web
framework permission to serve a directory that contains that artifact, and the framework
does exactly what its documentation says it will. The visitor who owns the session can fetch
their own raw artifact, unscrubbed. Nobody else's — the ids hold — so the scope is one
visitor reading a fuller record of their own run than the UI shows them, and that record
includes the full system prompt and, in the documented worst case, whatever a hostile or
misbehaving model endpoint managed to place in a tool call.

I filed it as **Low**. It is same-session only, and it becomes a secret leak only when a
secret first lands in the artifact, which the project itself documents as possible but not
routine. The fix is one line, and I verified it against the same primitive: the deliverables
stay downloadable, the artifact returns 403.

## What verification added

Two executions, both against a local listener with the demo's exact launch arguments and a
session tree laid out the way the demo builds it. The first showed the artifact, a dotfile
beside it, and the read-only inputs directory all served with 200, while two controls
outside the allowed root were refused. The second removed the one argument and showed the
deliverable still served through the framework's own cache while every raw session path
returned 403. No deployed instance was touched.

Reading alone would have made the claim; the framework's documentation is explicit about
what a directory in that allow-list means. But the README says the opposite was *verified*,
and when a maintainer's document says they tested it, the burden is to run it, not to argue
from the manual. What the README actually lists as tested is another session's artifact,
which fails on the unguessable id. The visitor's own artifact was never on the list.

## What the 58 findings actually were

Every one collapsed on inspection:

- **Twelve `non-literal-import`** hits are the workflow and plugin loaders. The module name
  is derived from a runtime dataclass's `__module__` attribute or from a registry, never from
  model output. Framework plumbing.
- **Twelve mutable-action-tag** hits in three workflow files, `actions/checkout@v4` and the
  like. Supply-chain hygiene worth pinning to SHAs; not a vulnerability.
- **Seven `logger-credential-leak`** hits in the scheduler. The "token" being logged is an
  execution epoch used to detect stale runs. Seven-for-seven false positive, the same as this
  rule's record across the series.
- **Six Gitleaks** hits, all `sk-test-…` placeholders inside `tests/test_hf_space_leaks.py`
  and `tests/test_hf_space_config.py` — the project's own test suite *for its secret-leak
  guards*. The scanner flagged the test that proves the guard works.
- **Six `dynamic-urllib-use`** hits. Every destination is an operator-configured endpoint
  read from the environment (a vision model, an OCR pool, an SGLang health check). The
  model-controlled fetches go through a separate guarded client that pins the resolved
  address and walks redirects hop by hop, and none of these six are on that path.
- **Four Docker root-user** hits across the runtime images. The sandbox shell drops to an
  unprivileged uid per exec and runs under a per-exec cgroup, so root in the image is the
  usual hardening item, not an exposure.
- **Two `exec-detected`** hits are the reader and writer bundles compiling *their own source
  fragments* into a single-file script for the sandbox. Two `dangerous-globals-use` hits
  index a fixed dispatch dict by file extension. One `subprocess-shell-true` hit is the
  sandbox shell tool itself — on a code-executing framework, that is the product surface,
  and it runs with a minimal env, an unprivileged uid and a memory cap.
- **One `tarfile-extractall`** hit in a benchmark staging script that resolves every member
  against the base directory *and* passes `filter="data"`. Credit the defense.
- One Jinja2 hit on a prompt template, one Python 3.7 importlib compatibility note. Noise.

## Patterns observed

This is the **composite-finding** class, and one of the cleanest examples the series has
met: two decisions, each defensible in isolation, in two different files, composing into a
contradiction of the project's own written containment. Decision one, "accept the raw
artifact because it is unreachable," lives in a README paragraph and a test docstring.
Decision two, "allow-list the sessions root so the file component can serve deliverables in
place," lives in a launch call. No rule fires on either. The bug is the edge between them.

It is also the **docstring-as-oracle** pattern doing exactly what it is for. The README
paragraph that records the caveat is what made the finding precise: it named the artifact,
named the property it depends on, and named the property as verified. Diff that sentence
against the launch call and the gap is a single argument. Projects that write down their own
caveats are easier to review and easier to fix, and this one is a strong argument for the
habit — the reasoning was correct everywhere except one line, which is why the fix is one
line.

Everything else this review touched held, and it touched a lot: the path guard resolves
symlinks before the prefix check and only lets a symlink *widen* access from an
operator-curated tree; the fetch guard refuses split-horizon DNS by pinning every resolved
address; the tool policy is an allow-list and a hard deny at once, installed before anything
runs, precisely so a future profile edit cannot re-admit the shell. For a two-week-old
public repository this is an unusually finished threat model, and the scanner had nothing
to say about any of it.

## Notes on the tool

- **58 findings, one real, and the real one is in none of them.** The recurring limit: a
  download allow-list that is one directory too wide is not a pattern any SAST rule
  represents, and the evidence that it matters lives in a README paragraph.
- **The `logger-credential-leak` rule is now seven-for-seven false on this repo and, as far
  as the series has recorded, has never once been right.** Its trigger is the substring
  "token" in a log call. Backlog: re-rank it below the fold unless the logged value
  traces to a secret source.
- **Gitleaks flagged the leak-guard test suite.** A `.gitleaks.toml` or baseline would
  clear it, and the finding count on a well-tested repo continues to scale with test
  richness rather than risk.
- **The two dependency install paths agreed today.** The `dependency-scan-unaudited-lockfile`
  meta finding still fired, correctly, because pip-audit did not read `uv.lock`; Trivy did,
  and both were empty. Worth recording as the case where the meta finding is the honest
  "checked both" rather than a coverage gap.

## Disclosure timeline

- 2026-09-06 — scan run against `1233828`; finding verified by execution, remedy verified by execution
- 2026-09-06 — reported privately via GitHub private vulnerability reporting, with both repro scripts
- 2026-09-06 — public post (this page), finding class only

## Reproduce

```bash
git clone https://github.com/ApodexAI/FrontierAgent /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/apodexai-frontieragent --min-severity medium
```

*The scan is reproducible; the finding detail is withheld until the maintainers resolve or a 90-day window elapses, per the project's security policy.*
