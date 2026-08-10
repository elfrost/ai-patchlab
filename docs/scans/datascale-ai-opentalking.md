---
layout: default
title: "datascale-ai/OpenTalking: security scan"
date: 2026-08-10
---

# datascale-ai/OpenTalking — security scan

**Repository:** [datascale-ai/opentalking](https://github.com/datascale-ai/opentalking)
**Commit scanned:** `1aa2516e`
**Scan date:** 2026-08-10
**Disclosure status:** disclosed — [issue #167](https://github.com/datascale-ai/opentalking/issues/167), fix in [PR #168](https://github.com/datascale-ai/opentalking/pull/168)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 52 |
| Medium | 41 |
| Low | — |
| Info | — |

**Total findings:** 93 at `--min-severity medium` (1 real after curation —
and **none of the 93 is it**)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

## The project

OpenTalking (2.7k★, Apache-2.0) is a **real-time digital-human pipeline**: you
point a browser at it and talk to an animated presenter that listens (STT),
thinks (an OpenAI-compatible LLM), speaks (TTS), and lip-syncs (QuickTalk,
Wav2Lip, FlashTalk, MuseTalk, FasterLivePortrait) over WebRTC. The README's
demo reel is healthcare guidance, live commerce, and a tourism guide — this is
aimed at people deploying a talking avatar in front of the public, not at a
hobby audience.

It is a substantial codebase and an actively plural one: 25 merged PRs in the
recent window across nine or more distinct contributors, pushed to on the day of
the scan. There is a FastAPI backend (`apps/api`), a single-process variant
(`apps/unified`), a React WebUI (`apps/web`), a worker, a marketing homepage,
and `docker-compose.yml` at the root so `docker compose up` gets you the whole
stack.

No `SECURITY.md` at the root, in `.github/`, or in `docs/`. Private
vulnerability reporting is disabled — I probed it, and `POST
/security-advisories/reports` returns `403 Repository does not have private
vulnerability reporting enabled`. There is a company org and a product website,
which is a commercial signal, but with no private channel offered at all the
project has effectively nominated GitHub issues as the channel. One finding, so
one focused issue — which satisfies the one-vuln-per-issue rule either way.

## What the project already says about its own boundary

Before the finding, the concession that shapes it. `docs/en/cases/private-deployment.md`
says this, plainly, under a heading called *Gateway and Security Boundary*:

> OpenTalking does not provide a complete built-in user-auth system. For public
> or multi-tenant enterprise deployments, handle these at the gateway:
> TLS termination. User authentication and access control. CORS allowlist.

So "the API has no authentication" is **not** a finding here. It is a stated,
honest boundary, and by the
[advertised-boundary test](agentera-agently.html) this series has been applying
since Agently, an honest "no boundary, put a gateway in front" is a design
choice, not a defect. They even name the CORS allowlist as a gateway
responsibility, which pre-empts the lazy version of this write-up.

I still filed. The reason is the interesting part.

## The finding: the documented mitigation makes it worse

`opentalking/core/config.py:354` ships:

```python
cors_origins: str | list[str] = "*"
```

and both application entry points mount it identically —
`apps/api/main.py:31` and `apps/unified/main.py:217`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,   # ["*"] by default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This is the same *family* as [tabbyAPI two days ago](theroyallab-tabbyapi.html),
and I nearly wrote it up the same way. The differential said otherwise, twice,
and the mechanism here turns out to be a different one.

### The wildcard is the whole lock, and the obvious fix doesn't turn it

The routes take pydantic bodies, so a cross-origin POST is preflighted. Measured
against Starlette 0.48.0 / FastAPI 0.119.0 with the exact middleware config
above and `Origin: https://evil.tld`:

| `allow_origins` | `allow_credentials` | preflight for JSON POST | attacker's POST executes? |
| --- | --- | --- | --- |
| `["*"]` (shipped) | `True` | `200`, `ACAO: https://evil.tld` | **yes** |
| `["*"]` | `False` | `200`, `ACAO: *` | **yes** |
| `["http://localhost:5173"]` | `True` | `400`, no `ACAO` | no |

Two results worth having in writing. **Turning `allow_credentials` off does not
close it** — the preflight is still approved and the request still runs. This is
now the second consecutive scan where the one-character version of the fix would
have fixed nothing, and it is the reason I run the table before filing rather
than after.

And there is **no non-preflight path**: every CORS-simple content type against a
pydantic-body route returns `422` — `text/plain`, `application/x-www-form-urlencoded`,
`multipart/form-data` alike. So this is not classic CSRF needing a token;
blocking the preflight is a *complete* fix. That is a pleasant thing to be able
to tell a maintainer.

### The part that inverts the documentation

Here is the Starlette detail that makes the gateway advice backfire:

```
simple GET, Origin: evil.tld, no cookie   -> Access-Control-Allow-Origin: *
simple GET, Origin: evil.tld, WITH cookie -> Access-Control-Allow-Origin: https://evil.tld
                                             Access-Control-Allow-Credentials: true
```

With `allow_origins=["*"]` and `allow_credentials=True`, Starlette emits a
literal `*` for an anonymous request — but **reflects the requesting origin the
moment the request carries a cookie**. So the two deployments diverge:

- **No gateway** (what `docker compose up` gives you): the attacker's page gets
  *blind writes*. The preflight is approved, the request executes, the response
  body is not readable. Sufficient on its own — see below.
- **With a gateway doing session auth, exactly as the docs advise:** the
  victim's browser attaches the session cookie, Starlette flips to reflecting
  the origin, and the attacker's page gets **authenticated cross-origin reads
  *and* writes** across the whole API. The gateway authenticates the request;
  the app then tells the browser that any origin may read the answer.

The mitigation the project documents is the thing that supplies the cookie that
unlocks the read. A reverse proxy cannot cleanly retract it either — the app's
own `Access-Control-Allow-Origin` is already on the response.

This also reconciles a note this series has been carrying since
[agentic_security](msoedov-agentic-security.html), where the fix's own analysis
corrected mine: Starlette *reflects* rather than sending `*`. It does — **when a
cookie is present**. Both readings were partial. The rule to carry forward is
that for a permissive-config finding, the framework's behaviour is a function of
the *request*, not just the config, so probe it with the request the attack
would actually send.

### Why it matters: `/runtime-config/apply`

`apps/api/routes/runtime_config.py:753` has no dependencies of any kind. A body
of `{"llm_base_url": "https://attacker.tld/v1"}` is the whole payload:

- `_build_updates` (`:588`) maps it to `OPENTALKING_LLM_BASE_URL`;
- `_write_env_updates` (`:760`) **persists it to the server's `.env`**, so it
  survives a restart;
- `_refresh_live_runners` (`:724`) rebuilds live session LLM clients with the
  new base URL **while keeping the existing `settings.llm_api_key`**.

And `opentalking/providers/llm/openai_compatible/adapter.py:27-31` sends that
retained key to whatever host was just injected:

```python
if self.api_key:
    headers["Authorization"] = f"Bearer {self.api_key}"
url = f"{self.base_url}/chat/completions"
```

One blind cross-origin POST therefore redirects the deployment's LLM traffic —
the provider API key in the `Authorization` header, plus the full content of
every subsequent conversation turn — to an attacker-chosen endpoint,
persistently. The same route writes the STT, TTS and mem0 key and base-URL
variables too.

The blind-write case alone carries it. No response read is required, which is
why this bites the default `docker compose up` deployment and not only the
gatewayed one.

**Fix:** default `cors_origins` to the shipped WebUI origins
(`http://localhost:5173,http://127.0.0.1:5173`) and let deployments widen it via
`OPENTALKING_CORS_ORIGINS`. That is [PR #168](https://github.com/datascale-ai/opentalking/pull/168);
compose still works, unified mode is same-origin and unaffected, and the
existing CORS parsing test passes untouched because it constructs `Settings`
explicitly.

## Two findings I killed by running them

Both looked good in the draft. Neither survived.

**The avatar path handlers.** Five handlers in `apps/api/routes/avatars.py`
resolve `avatar_id` and check containment with `relative_to(root)`;
`get_preview` (`:1225`) and `get_avatar` (`:1214`) do not. That is the
[seam shape](the-momentum-open-wearables.html) exactly — the sixth
implementation of something done right five times — and I expected a traversal.
Running it: `%2e%2e` does decode to `..` after routing and *does* escape one
directory (I confirmed a read of a file placed above the avatars root). But a
path parameter matches `[^/]+`, so `%2f` breaks routing and it stops at exactly
one level, on a file that must be named `preview.png`. Reading
`./examples/preview.png` is not a vulnerability. It is a consistency nit, and
filing it as traversal would have been wrong.

**The persona package importer.** `opentalking/persona/package.py:51` calls
`zf.extractall(target)`, which is normally where a zip-slip write-up starts.
`_ensure_safe_zip` (`:29`) rejects absolute members and any `..` component and
caps the total at 200 MB *before* extraction, and `_read_prompt_text` re-checks
the resolved prompt path with `relative_to`. It is correct. Credit where it is
due.

## Notes on the codebase

This team is careful, and the care is not decorative. `get_client_asset`
(`:1051`) inspects `request.scope["raw_path"]` for `%2f`, `%5c` and `%00` before
touching the path, then runs `safe_relative_path`, then checks containment,
*then* requires the asset to appear in a `referenced_assets` allowlist. Four
independent gates on one file-serving route. Someone there has thought hard
about how uvicorn decodes paths — which makes the two unguarded siblings above
read as drift rather than ignorance, and is why the fix belongs in a linter or a
shared helper rather than a bug report.

The `runtime_config` GET is also right where it counts: every provider payload
returns `api_key_set: bool` rather than the key. Config-reading endpoints
handing back live credentials is a genre this series has filed before
([N.E.K.O](project-n-e-k-o-n-e-k-o.html)); OpenTalking does not do it. The
finding is about who may *write* that config, not about what reading it leaks.

## What the other 93 findings were

Zero real. The breakdown:

- **18 `detect-insecure-websocket`** — a JavaScript rule fired at YAML, Markdown
  and Python, on `ws://` URLs pointing at `127.0.0.1:9000` (the local OmniRT
  inference container) in compose files, docs and config examples. Loopback
  inference transport.
- **13 `pickles-in-pytorch` / `avoid-pickle`** — `torch.load` of model weights
  in the MuseTalk, Wav2Lip and QuickTalk loaders. For a project whose *purpose*
  is running ML models, this is product surface, per the
  [code-executor inversion](ag2ai-ag2.html). The weights come from the
  operator's own downloads. `weights_only=True` is worth adopting where the
  loader allows it, but it is hardening, not a finding.
- **18 `github-actions-mutable-action-tag`** — the **eighth consecutive scan**
  in which one GitHub Actions hygiene rule is the largest single cluster. At
  this point it is a property of the report format, not of any repository.
- **2 `run-shell-injection`** in `.github/workflows/pypi-release.yml` — the
  trigger is `workflow_dispatch` with a required `tag` input, and the flagged
  step *is the validator* (`case "${{ inputs.tag }}" in v[0-9]*...`).
  Maintainer-triggered, and it is the check itself. FP.
- **1 `sqlalchemy-execute-raw-query`** at `opentalking/agent/knowledge_store.py:846`
  — the [#1 recurring FP](mnemosyne-oss-mnemosyne.html), seventh appearance.
  `placeholders = ", ".join("?" for _ in selected)` with the values bound as
  parameters. Only the placeholder count is interpolated. FP.
- **4 Dockerfile "user should not be root"**, npm advisories (nanoid, postcss,
  vite) confined to `apps/homepage`'s build toolchain, and one nginx h2c note —
  standard hygiene.
- **Python dependency CVEs**: `rembg` ×2, `transformers` ×3, `onnx` ×10. The
  `rembg` advisories (PYSEC-2026-2274 and GHSA-55v6-g8pm-pw4c) are path
  traversal **in rembg's HTTP server** — `rembg s`. OpenTalking imports
  `from rembg import remove` as a library
  (`opentalking/avatar/matting/rembg_provider.py:58`) and never starts that
  server. Version-match, not reachable —
  [gate two of three](nottelabs-notte.html). The `transformers` and `onnx`
  entries are malicious-model-file classes, gated by the same operator trust
  boundary as the pickle findings.
- **Gitleaks: clean.** A true zero, not an empty file — 3 bytes containing `[]`,
  and there is a real secret surface here (a `.env.example` with 60-plus
  provider key names) for it to have found something in.

## Notes on the tool

**A per-tool coverage row, an eleventh time.** Trivy's targets were both npm
lockfiles and four Dockerfiles. It never opened `pyproject.toml` — there is no
Python lockfile in the repo, and an unlocked `pyproject` is skipped. If pip-audit
had also produced nothing, "Python dependencies: 0 findings" would have rendered
identically to "Python dependencies: never scanned," which is the
[pipeshub blindness](pipeshub-ai-pipeshub-ai.html) exactly. Here pip-audit did
run and did return 15 advisories, so the gap closed by luck of tool overlap
rather than by design. The report still cannot tell you which manifests were
read.

**I mis-keyed my own report and it looked like a tool failure.** I read
`security_report.json` expecting a `findings` key, got `0`, and briefly had a
139 KB report that claimed to contain nothing — the
[0-byte lesson](dataelement-clawith.html) reflex firing correctly on a
false alarm, since the actual key is `findings_by_severity`. Worth recording
because the reflex is right and the check is cheap: a report whose size and
whose finding count disagree is always worth one more look, whichever way the
disagreement resolves.

**The rule that mattered never fired.** No CORS rule appeared in the 93. tabbyAPI
at least surfaced `fastapi.security.wildcard-cors` at `medium`; here the same
class of misconfiguration produced *nothing at all*, because the wildcard is not
at the middleware call site — it is a pydantic-settings default 300 lines away in
another module, reached through a property. Two-hop config defaults are invisible
to a pattern matcher. Both of this scan's real pieces of work — that default, and
the unauthenticated `.env`-writing route it exposes — were hand-swept.

## Disclosure timeline

- 2026-08-10 — scan run against `1aa2516e`
- 2026-08-10 — private channel probed: no `SECURITY.md` in root, `.github/` or
  `docs/`; private vulnerability reporting disabled (`403`)
- 2026-08-10 — [issue #167](https://github.com/datascale-ai/opentalking/issues/167) filed
- 2026-08-10 — [PR #168](https://github.com/datascale-ai/opentalking/pull/168) opened with the fix
- 2026-08-10 — public post (this page)

## Reproduce

```bash
git clone https://github.com/datascale-ai/opentalking /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/datascale-ai-opentalking --min-severity medium
```

The CORS differential is standalone — it needs only `fastapi` and `starlette`,
not the project:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.get("/runtime-config")
def rc():
    return {"llm": {"base_url": "https://internal.example/v1", "api_key_set": True}}

c = TestClient(app)
print(c.get("/runtime-config", headers={"Origin": "https://evil.tld"}
     ).headers.get("access-control-allow-origin"))                      # -> *
print(c.get("/runtime-config", headers={"Origin": "https://evil.tld",
     "Cookie": "session=x"}).headers.get("access-control-allow-origin"))  # -> https://evil.tld
```
