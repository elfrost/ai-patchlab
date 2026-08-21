---
layout: default
title: "theroyallab/tabbyAPI: security scan"
description: "Security scan of theroyallab/tabbyAPI: 18 findings (18 above the medium floor), 2 real — the official API server for ExLlamaV3 (1.3k★, AGPL-3.0"
date: 2026-08-08
---

# theroyallab/tabbyAPI — security scan

**Repository:** [theroyallab/tabbyAPI](https://github.com/theroyallab/tabbyAPI)
**Commit scanned:** `c50f0d2b`
**Scan date:** 2026-08-08
**Disclosure status:** disclosed — [issue #448](https://github.com/theroyallab/tabbyAPI/issues/448)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 2 |
| Medium | 16 |
| Low | — |
| Info | — |

**Total findings:** 18 raw / 18 at `--min-severity medium` (2 real after
curation; **one** of the 18 pointed at a real problem, and it understated it)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

## The project

TabbyAPI (1.3k★, AGPL-3.0) is **the official API server for ExLlamaV3** — a
FastAPI application that loads a quantized model onto your GPU and serves it
over an OpenAI-compatible API, with a KoboldAI-compatible surface as an option.
It is the thing a very large number of people run locally when they want their
own inference endpoint behind SillyTavern, Open WebUI, or a script.

It is small and legible: 92 Python files, 13,782 lines. The README is unusually
honest about its own scope — *"TabbyAPI is a hobby project made for a small
amount of users. It is not meant to run on production servers."* That sentence
does real work in this write-up, and I'll come back to it.

Maintenance is active and plural: six distinct authors had pull requests merged
in the last 60 days and seven issues were closed. There is no `SECURITY.md` at
the root, in `.github/`, or in `docs/`; private vulnerability reporting is
disabled; the only funding signal is a Ko-Fi badge. That combination is
[not strict-norm](repowise-dev-repowise.html) by this series' test, so a public
courtesy issue is the right channel.

## The finding: two correct decisions that break each other

The scanner flagged one line in `endpoints/server.py:35` as
`fastapi.security.wildcard-cors` — a rule that fires on thousands of repos and
is dismissed on most of them, because a wildcard CORS policy on a service with
no cookie authentication is usually a shrug. It was right here, and for a reason
the rule cannot see.

The server ships this:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Somewhere else entirely, two other decisions treat a loopback bind as a security
boundary in its own right:

- `config_sample.yml:20` — `disable_auth`, documented as *"Turn on this option
  if you are ONLY connecting from localhost."*
- `common/auth.py:1-4`, the module docstring — *"This method of authorization is
  pretty insecure, but since TabbyAPI is a local application, it should be
  fine."*

Each of the three is defensible alone. A permissive CORS policy makes life easy
for the many browser front-ends people point at TabbyAPI. An auth-disable escape
hatch is a kindness for a single-user local box. The docstring is candid rather
than negligent — it *tells* you the model is thin and why the author thinks
that's acceptable.

The problem is the composition, and it is the same shape as the
[N.E.K.O finding](project-n-e-k-o-n-e-k-o.html): **a web page running in your
browser is also "connecting from localhost."** The premise the auth exemption
rests on is not a property the bind enforces. CORS is precisely the mechanism
that decides whether a page from `evil.example` gets to talk to
`127.0.0.1:5000`, and this configuration decides *yes, to everything*.

For a user who followed the config's own advice and set `disable_auth: true`,
`get_key_permission()` returns `"admin"` to every caller. Any site that user has
open in another tab can then drive the admin API: load models, `/v1/download`
arbitrary HuggingFace repos onto the disk, switch prompt templates, replace
sampler overrides, and read `/v1/model/list` — which returns
`model_path.resolve()`, the absolute local model directory listing.

With auth left on (the default), the exposure narrows but does not vanish.
`/health` and `/.well-known/serviceinfo` carry no auth dependency at all, and
`/health` returns up to 100 stored `UnhealthyEvent` descriptions — raw backend
exception strings from `backends/exllamav3/model.py:1402`, which routinely carry
local filesystem paths. Any page you visit can read those cross-origin, and can
use them to fingerprint that you're running TabbyAPI and what you have loaded.

### What the differential showed

Reading Starlette's CORS middleware and asserting the outcome would have been
enough to sound right. Running it changed two claims.

Replicating the middleware config exactly, on the versions actually resolved in
the project's dependency tree (`fastapi-slim 0.129.1`, `starlette 1.5.0`):

| config | `GET /health` ACAO | page can read? | preflight `POST /v1/model/load` | page can send? |
| --- | --- | --- | --- | --- |
| shipped (`origins=["*"]`, `credentials=True`) | `https://evil.example` (**reflected**) | yes | `200` | yes |
| `credentials=False` only | `*` | yes | `200` | yes |
| `allow_origins` allowlist | absent | no | `400` | no |

The first correction: because `allow_credentials=True`, Starlette does not send
`*` — it **reflects the requesting origin**. This is the same mechanism that
[corrected my own report](msoedov-agentic-security.html) on agentic_security
back in July, where I described a permissive CORS config as "credentials
silently disappear" and the maintainer's fix revealed it was a live
reflect-any-origin hole. Same framework, same illegal-looking combination,
second time it behaved more permissively than the spec reading suggested. The
lesson has now paid for itself twice: **for a permissive-config finding, what
matters is what the framework does with the combination, not that the
combination is illegal.**

The second correction is the one that makes the issue actionable rather than
merely correct. The obvious "fix" — flip `allow_credentials` to `False` — **does
not close it.** With `*` still in `allow_origins`, a cross-origin page can still
read every response and preflight still returns `200`. Only the origin allowlist
does the work. Had I filed without running that row, the likely outcome is a
one-character patch that leaves the hole exactly where it was and closes the
issue as fixed.

### The second item: an SSRF that no rule fired on

`common/image_util.py:31-43`: for any `image_url` that isn't a `data:` URI,
`get_image()` performs a bare `session.get(url)` — no scheme filter, no host
filter, no destination policy. It is reachable from `/v1/chat/completions`
through `chat_completion.py:308` → `multimodal.py:17` →
`vision.py:39`, and `disable_fetch_requests` defaults to `False`.

That gives an api-key holder a server-side GET to anything the host can reach,
which is a genuine step up from what an api key is otherwise for — and it lands
hardest in exactly the scenario the `disable_auth` comment contemplates, an
instance shared with other people.

The preconditions are real and I stated them as such in the issue: it needs a
vision-capable model loaded (`use_vision`) and a valid api key. This is not a
drive-by.

I ran the primitive rather than describing it, and it killed part of my own
draft:

- `file://` and `gopher://` are **rejected** by aiohttp (`NonHttpUrlClientError`)
  — no local file read, no gopher pivot. Both were in my notes before I tested.
- redirects **are** followed, so validating only the submitted URL would not be
  sufficient.
- the timeout is not absent, as I had assumed from the missing `timeout=`
  kwarg — aiohttp's default `ClientTimeout(total=300, sock_connect=30)` applies.
- the two error paths differ enough to serve as an oracle: non-200 yields
  `"Failed to fetch image from {url}"`, while 200-but-not-an-image yields a PIL
  error. That distinction is enough to probe for live internal services.

Publishing the negative results is the point. "No `timeout=`" reads like an
unbounded hang until you check the library default, and `file://` SSRF is a
claim that would have been refuted by the first maintainer to try it.

## What the other 16 findings were

| Cluster | Count | Verdict |
| --- | ---: | --- |
| `github-actions-mutable-action-tag` | 12 | Hardening noise — **sixth consecutive scan** where one GHA rule is the single largest cluster |
| Dockerfile `USER` is root (Trivy) | 2 | Real hardening, not exploitability-shaped; a GPU inference container |
| `non-literal-import` (`optional_dependencies.py:65`) | 1 | False positive — the name comes from a fixed pydantic field set, never a request |
| `explicit-unescape-with-markup` (`templating.py:49`) | 1 | False positive — `Markup()` wraps a JSON filter feeding a **prompt string**, never HTML; the environment is `ImmutableSandboxedEnvironment` |
| `dynamic-urllib-use-detected` (`tools/replay_chat_request.py:134`) | 1 | False positive — a developer CLI replay tool, not shipped server surface |

## Patterns observed

**The auth wiring is the best-built part of the codebase, which is why the
finding lives outside it.** Every route across all three routers —
`endpoints/core`, `endpoints/OAI`, `endpoints/Kobold` — carries either
`check_api_key` or `check_admin_key`, and the admin/api split lands on the right
axis: every state-changing route (load, unload, download, template switch,
sampler override) requires admin, every read requires at least an api key.
`load_inline_model()` re-checks permission rather than trusting its route guard,
which is the defensive habit that catches refactors. The auth-file watcher keeps
the previous key set when a reload fails, so a partial write can't fail open.

That matters because it is the inverse of the [loopx](huangruiteng-loopx.html)
finding from yesterday, where a guard was wired to a subset of one surface's
handlers and the unguarded subset was the one that returned the private
material. Here the subset boundary is drawn correctly and consistently. The
problem is a level below: the transport layer decides *who is allowed to speak
to the guard at all*, and that decision was made once, globally, in a different
file, for a different reason.

**A candid disclaimer is not the same as a defended boundary — but it isn't
nothing, either.** The README's "not meant to run on production servers" is the
kind of sentence that could excuse almost any finding, and it genuinely does
retire a whole class of them: nobody should file "no rate limiting" or "no
audit log" here. But it doesn't retire *this* one, because the claim under
attack isn't a production claim. It's the local claim — the one the project
makes affirmatively, in its own config comments, as advice to follow. The
[advertised-boundary test](agentera-agently.html) from Agently applies in a
softer form: TabbyAPI doesn't name a boundary it fails to enforce, it names a
*condition* ("only connecting from localhost") that it treats as sufficient and
that its own transport config makes insufficient.

**Dependency posture is genuinely clean and worth saying out loud.** 61 resolved
dependencies, zero known advisories — no stale lockfile cluster, no
version-match table to triage for reachability. Gitleaks returned a true empty
`[]`, and `api_tokens_sample.yml` ships with empty placeholder values rather
than plausible-looking fakes. On a series where dependency drift is the single
most common filing, a project this small keeping 61 deps current is the
unglamorous thing that prevents most incidents.

## Notes on the tool

**The one rule that mattered fired, and its severity was three levels too low.**
`wildcard-cors` came through as `medium`, sorted below twelve GitHub Actions
tag-pinning findings and two Dockerfile `USER` warnings. Severity is a property
of a line for a scanner and a property of a *system* in reality, and nothing in
the report could connect `endpoints/server.py:35` to a comment in
`config_sample.yml` two directories away. This is the
[composite class](arcreel-arcreel.html) again: no single-file rule can see it,
because neither file is wrong.

**Sixth consecutive GHA mutable-action-tag flood.** 12 of 18 findings — 67% of
this entire report — were one rule. On loopx it was 17 of 39. The backlog item
is now unavoidable: this rule needs to be collapsed into a single aggregated
finding with a count, not emitted per-occurrence, or it will keep being the
largest cluster in every report this series produces regardless of the project.

**The coverage row, again — this time it would have read correctly.** Following
[yesterday's loopx lesson](huangruiteng-loopx.html), I checked every raw output
against the project's own declarations before trusting a zero: semgrep 43 KB
(healthy), gitleaks 3 bytes (`[]` — a true zero, confirmed against
`api_tokens_sample.yml` holding only empty placeholders), trivy 5.3 KB (two
Dockerfile targets, 0 vulnerabilities), pip-audit 61 dependencies resolved with
0 advisories. Every one of those zeros is real. But I still had to hand-verify
four files to establish that, on the second consecutive scan — which is the
whole argument for emitting a per-tool coverage row (`0 of 61 deps`,
`0 of 92 files`) instead of a bare zero.

**Both real findings needed a runnable differential, and both differentials
changed the text.** The CORS item gained a corrected mechanism (reflection, not
`*`) and a corrected remedy (the allowlist, not the credentials flag). The SSRF
item lost two claims (`file://` read, absent timeout). Neither correction was
available from reading. A scanner cannot do this, but the curation layer around
it can, and increasingly should: for any finding whose severity depends on
framework behavior, the framework is installed and the question is one script
away.

## Disclosure timeline

- 2026-08-08 — scan run
- 2026-08-08 — CORS and SSRF primitives verified against the resolved dependency versions
- 2026-08-08 — [issue #448](https://github.com/theroyallab/tabbyAPI/issues/448) filed
- 2026-08-08 — public post (this page)

## Reproduce

```bash
git clone https://github.com/theroyallab/tabbyAPI /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/theroyallab-tabbyapi --min-severity medium
```
