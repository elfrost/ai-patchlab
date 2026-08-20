---
layout: default
title: "whiteguo233/OpenBiliClaw: security scan"
date: 2026-08-20
---

# whiteguo233/OpenBiliClaw — security scan

**Repository:** [whiteguo233/OpenBiliClaw](https://github.com/whiteguo233/OpenBiliClaw)
**Commit scanned:** `d8f63745` (main at scan time; v0.3.208)
**Scan date:** 2026-08-20
**Disclosure status:** public — one real finding, filed as a focused courtesy
issue. No `SECURITY.md` in the root, `.github/`, `docs/`, or on the published
docs site, and private vulnerability reporting is disabled, so a public issue is
the only channel the project offers.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 216 |
| Medium | 156 |
| Low | 0 |
| Info | 0 |

**Total findings:** 373 (all above the medium floor) — semgrep 301, Trivy 60,
gitleaks 12. **One real**, and it is the one the two dependency scanners
disagreed about.

## The project

OpenBiliClaw is a **local-first cross-platform content-discovery agent**: it
learns what you like, then goes looking for it across Bilibili, Xiaohongshu,
Douyin, YouTube, X, Zhihu, Reddit, Linux.do, V2EX and Weibo. 2.9k★, MIT, five
months old, and among the most active targets this series has scanned — **14
distinct humans with merged PRs and 74 closed issues in 60 days**.

Architecturally it is three things that have to trust each other: a FastAPI
backend (261 Python files, a 20k-line `api/app.py`), a **browser extension**
that reuses your existing logins on those ten platforms rather than storing
passwords, and a desktop/mobile web UI. There is a Docker compose stack, an
optional TLS proxy profile, a Flutter client in a sister repo, and a signed
Safari build. The credential surface is exactly what you would fear: ten
platforms' session cookies, LLM provider API keys, and a proxy URL with
userinfo.

## The finding — two dependency scanners disagreed, and the disagreement is the finding

Trivy and pip-audit returned answers that cannot both be summarised as "the
dependency posture." **Trivy read `uv.lock` and reported 63 advisories, 36 of
them HIGH. pip-audit resolved `pyproject.toml` and reported zero, across 73
dependencies.**

Neither is wrong. They read different files, and **this project ships both as
real install paths**:

- `pyproject.toml` declares open floors — `"Pillow>=10.0"`, `"fastapi>=0.115"`,
  `"yt-dlp>=2024.1.0"`. Resolve those today and you get current, clean releases.
  That is what pip-audit measured.
- `uv.lock` pins the resolved set, and the pins are stale: **Pillow 12.1.1,
  starlette 0.52.1, yt-dlp 2026.3.17, python-multipart 0.0.22, cryptography
  46.0.5, urllib3 2.6.3, lxml 6.0.2.** That is what Trivy measured.

Which one a user gets is decided by *how they installed*, and the two shipped
paths land on opposite sides:

- **The README's recommended one-line installer** runs `scripts/install.sh` →
  `scripts/agent_bootstrap.py` → `local_install()`, which at
  `agent_bootstrap.py:2898` runs **`uv sync`** when `uv` is present. That
  installs the lockfile pins.
- **The Docker path does not read the lockfile at all.** `Dockerfile:28` runs a
  one-liner that loads `pyproject.toml`, writes `project.dependencies` out to
  `/tmp/requirements.txt`, and `pip install -r`s it — resolving the floors to
  current releases.

So the containerised deployment is clean and the recommended host install is
not, from the same commit. A scan that read only `pyproject.toml` would have
called this repository's dependency posture perfect.

**The reachable one is Pillow.** `uv.lock` pins 12.1.1, which carries eleven
HIGH advisories, and the cover-image pipeline hands it attacker-supplied bytes
on a background timer:

- `runtime/image_cache.py:280` allow-lists the fetch hosts — `hdslb.com`,
  `xhscdn.com`, `douyinpic.com`, `ytimg.com`, `sinaimg.cn`. **Every one of those
  is a user-upload CDN.** The allowlist correctly stops the fetch being a
  general SSRF primitive; it does not make the *bytes* trusted, because anyone
  can publish a video or a note and choose its cover.
- `discovery/multimodal.py:48` opens those bytes with `Image.open(BytesIO(data))`,
  then `_coerce_rgb` converts, `thumbnail(..., Image.Resampling.LANCZOS)`
  resamples, and it re-encodes to JPEG. That is a full decode-and-resample
  pipeline, not a header sniff.
- It runs from automatic discovery, so there is no click to socially engineer.

`discovery/keyframes.py:403` opens sprite sheets the same way. The other pins
matter less but are not nothing: **starlette 0.52.1 is the framework actually
serving every request**, and `python-multipart` 0.0.22 sits in FastAPI's form
path.

**The fix is a lockfile refresh** — `uv lock --upgrade`, or at minimum
`--upgrade-package pillow`. The floors in `pyproject.toml` already permit every
patched version; nothing needs to be relaxed, and the Docker path proves the
project runs fine on current releases.

I did not open a PR. Regenerating a 63-package lockfile is not a diff I can
verify without running the project's resolver against its full platform matrix,
and a lockfile I cannot test is worse than an issue that names the file.

## The negative I followed to the end, and published

The lead I liked most was wrong, and the reason it was wrong is worth more than
the finding would have been.

`auth_core.py:480`, `is_extension_origin`, matches **any** origin beginning
`chrome-extension://` or `moz-extension://`. It does not pin the project's own
extension IDs. `api/auth.py:_origin_safe_for_local` consults it first and
returns `True` immediately — skipping the `Sec-Fetch-Site` check and the
DNS-rebinding `Host` check that every other caller has to pass. A caller who
clears that check is **trusted-local**, which includes `/api/auth/admin`, the
endpoint that manages the password gate.

It looked airtight, because the project's own design doc calls it out. From
`docs/superpowers/specs/2026-07-10-pr-99-device-access-auth-design.md`, under
**Non-Goals**: *"不把浏览器提供的 `chrome-extension://` / `moz-extension://` Origin
当作身份凭证"* — do not treat the browser-provided extension Origin as an
identity credential. The same document records that when PR #99 was not merged,
its `allowed_extension_ids` and `verify_extension_id` were **deleted with no
compatibility migration**. A stated non-goal, a deleted enforcement mechanism,
and a live code path that does the thing the non-goal forbids. The
[docstring-as-oracle](jgravelle-jcodemunch-mcp.html) move, handed to me.

**It is not exploitable, and the reason is four lines further down.** The same
function ends with `if not origin: return True` — a loopback caller that sends
*no* `Origin` header is trusted-local already. A malicious extension does not
need to be mistaken for the real one; it can just issue a request without an
Origin, which the code's own comment in `pick_token` notes Chrome extensions do
anyway (*"Chrome extension fetches do not consistently send Origin on GET"*).
Forging or possessing an extension origin buys an attacker nothing they did not
have. The actual trust anchor is `trust_loopback`, which is **documented,
defaults on for a local-first desktop app, and is one config key to turn off**.

So the extension branch is not an identity check that is too weak. It is an
*exemption* from browser-intent checks whose entire job is stopping **web
pages**, and against web pages it holds. The non-goal in the design doc is about
remote authentication, where the device-key exchange does the work. Reading the
doc made the finding look certain; reading four more lines of the function
killed it.

## The default that looks like the finding and is not

`config.py` sets `ApiConfig.host = "0.0.0.0"` and `ApiAuthConfig.enabled =
False`. Bound to every interface, no password, out of the box — the shape this
series has filed against before, and semgrep duly fired
`avoid-bind-to-all-interfaces` twice.

It is documented, and documented in the place that matters. `README.md:345`
tells you `openbiliclaw init` **asks** whether to allow LAN access on first run,
gives the default, and names the exact key to change: `0.0.0.0` for LAN,
`127.0.0.1` for this machine only. `README.md:343` advises turning the password
gate on for remote deployments. The `ApiConfig` docstring states the trade-off
in the code. The LAN binding is not an oversight, it is the feature — the mobile
web UI at `/m/` exists to be reached from your phone.

[Advertised boundary](dataelement-clawith.html): a default that is disclosed,
prompted for at install, and reversible with a documented key is a posture, not
a defect. Filing it would have been the noisy move.

## Where the method found nothing — which is nearly everywhere

This is one of the better-defended local-first applications in the series, and
several of the defences are ones I have watched other projects get wrong.

**The credential-export class is fixed, and fixed at both sites.** `GET
/api/config` still accepts `?reveal_keys=true` for old clients — and at
`app.py:17054` the handler's second statement is **`del reveal_keys`**, with
`mask_keys=True` passed unconditionally. `GET /api/sources/credentials` does the
identical thing at `app.py:14597`, with a docstring that states the principle:
*"Secrets are write-only: a same-origin settings read must not become a bulk
credential export."* This is precisely the [N.E.K.O
class](project-n-e-k-o-n-e-k-o.html) — a loopback config endpoint handing back
every provider key unmasked — already found and already closed. What makes it
worth crediting is that it was closed at **both** call sites. The
[jcodemunch](jgravelle-jcodemunch-mcp.html) lesson three days ago was a rule
with three spellings in one tree and a fourth call site that missed it; here the
same rule has two spellings and neither drifted. The one row that opts out of
masking (`secret=False`) is Reddit's cookie **names**, with a comment explaining
that masking a list of names would hide the only thing the row exists to say.

**The middleware whitelist seam holds.** `_is_public` lets ten paths bypass the
auth gate entirely, and four of them are state-changing: `/api/init`,
`/api/init/cancel`, `/api/autostart/apply`, `/api/auth/admin`. Every one of them
self-gates on `is_trusted_local` as its first executable statement
(`app.py:5491`, `6393`, `16458`, and the admin handler). This is the shape I
[go looking for](liaohch3-claude-tap.html) — a guard delegated from the
framework to the handler, where one handler forgets — and all four remembered.
`/api/autostart/apply` is the one I expected to fail, because it is the only one
of the four whose whitelist entry carries no "self-gates" comment. It gates.

**Seventeen `postMessage` listeners across five platforms, none of them loose.**
The extension runs seven MAIN-world scripts that must bridge back to their
isolated content scripts. Every listener checks `event.source !== window`, then a
`source` tag, then validates the payload shape before doing anything. The Douyin
bridge — ten listeners, the most complex — goes further with a shared helper
that checks `event.source === target && event.origin === target.location.origin`.
The consistent one is the one nobody drifted from.

**The markdown renderer is hand-rolled and correct.**
`web/shared/dialogue-confirmation.js` feeds `innerHTML` at six sites. It escapes
**first**, then applies formatting to already-escaped text, slot-protecting code
spans and links so raw HTML can never re-enter; `safeMarkdownHref` allows only
`^https?://`, and links get `rel="noopener noreferrer"`. Escape-then-format is
the ordering hand-rolled sanitisers usually get backwards.

**The image proxy handles the redirect class.** `follow_redirects=False` with
manual revalidation at each of up to three hops, host allowlist re-checked per
hop, `image/*` enforced, 10MB ceiling checked against `Content-Length` *and*
during the read. And `_upstream_headers_for_host` rebuilds the header map **per
hop** specifically so the Weibo `Referer` is never forwarded to a different
allow-listed CDN — the [Observal](observal-observal.html) cross-origin redirect
header-leak class, anticipated.

Also: static assets are served by Starlette's `StaticFiles` from fixed
directories with no custom path joining; the login rate-limiter locks per
resolved client IP with a proxy-aware `X-Forwarded-For` resolver; failed
fingerprint reconciliation **fails closed** for token auth; and
`logout?all=true` is deliberately excluded from the public whitelist while plain
logout is not.

## Notes on the tool

**Fourteen semgrep timeouts, and this time the timeout landed on the rule that
mattered.** `paths.skipped` was **0** — for the third consecutive scan the
`errors` array was the only place the coverage gap was visible. Both
`subprocess-injection` rules (the Django and Flask variants) **timed out on
`src/openbiliclaw/api/app.py`** — the 20k-line file that is the entire API
surface. A timeout renders identically to clean, so "no command injection in the
API" was a claim the report had not actually earned.

I checked by hand. `app.py` has six `subprocess.run` calls, all in
`_interface_ipv4_candidates` / `_interface_ipv6_candidates`, all constant argv
lists (`["ipconfig"]`, `["ip", "-4", "addr", "show", "scope", "global"]`), no
interpolation, `shell=False`, 2-second timeouts. The one `shell=True` in the
repo is `cli.py:2015` running Ollama's own published `curl … | sh` installer,
where the pipe is the point. **The timeout hid nothing — but I only know that
because I looked, and nothing in the report would have told me to.**
`storage/database.py`, `cli.py`, `config.py` and `runtime/refresh.py` also timed
out on individual rules, as did the two largest JS bundles — including
`tainted-html-response` on the 593KB desktop `app.js`, which is why I audited
its 42 `innerHTML` sites by hand. **Seventeenth vote for a per-tool coverage
row**, and the first where I can name the exact rule/file pair that would have
been misread.

**The single CRITICAL is a file path.** Trivy DS-0031, "secrets passed via
build-args or envs", fired on
`docker/openbiliclaw-tls-proxy.Dockerfile:21` — `ENV KEY_FILE=${CERT_DIR}/srv.key`.
That is the *location* of a key, on a container whose whole job is to hold one,
in a volume generated at first start. The rule matched the variable **name**.
The top line of the report is a string containing `/certs/srv.key`.

**188 of 373 findings — 50% — are the SQL identifier FP, on its thirteenth
appearance**, and this is the most absurd instance yet: **157 of them come from
a rule named `sqlalchemy-execute-raw-query`, and the project does not depend on
SQLAlchemy.** It is not in `pyproject.toml` and not in `uv.lock`; storage is
stdlib `sqlite3`. The rule fires on any `.execute()`. The sites are what they
always are — `PRAGMA busy_timeout = {int(...)}` (an integer, coerced, and SQLite
does not accept a bound parameter in a PRAGMA at all), and
`ALTER TABLE llm_usage ADD COLUMN {column_name} {column_type}` in a schema
migration where both names come from a dict literal in the same function.

**All four "SSRF" hits are the same hardcoded loopback URL.**
`ssrf-injection-urllib` fired in the Linux.do, Reddit, Zhihu and Douyin
producers, on four copies of a `kick_*_task_dispatcher` that POSTs an empty body
to the literal string `http://127.0.0.1:8420/api/sources/<x>/kick`. No variable
reaches the URL. (They *are* four copies of a hardcoded port, which will fail
silently for anyone who moved the API off 8420 — a robustness nit, not a
security one, and not what the rule was claiming.)

**Twelve gitleaks hits, eleven of them placeholders**, and the twelfth is the
most interesting variety of this FP yet: `gcp-api-key` on
`youtube/client.py:53`, `AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8`. That is a
real Google API key by format and by issuer — it is YouTube's **public InnerTube
web key**, shipped inside youtube.com's own HTML to every browser that loads the
site, and hardcoded in every client library that speaks that API. Not a leak; a
published constant. **Twelfth placeholder-tier vote**, and the first where the
matched string is genuinely a live API key that is genuinely meant to be public.
The rest are `sk-abcdef1234567890xyzw` and friends in `tests/`.

Also `dangerous-globals-use` fired once, on `locals().get("outcome", "error")`
inside a logging call.

## The honest verdict

**One real finding out of 373, and it required two tools to disagree before it
was visible.** Every rule that fired on first-party code was wrong; the finding
came from noticing that Trivy and pip-audit had answered different questions and
that the project ships both questions as install paths. **The other 372 were
noise, and half of them came from a rule named after a library this project does
not use.**

The deeper reading is about what "well-defended" looks like from outside. This
codebase carries reviewer annotations in its auth layer (`review r1#1`, `r7`,
`r9`), a design doc that writes down its non-goals, and comments that explain
why a bypass exists rather than just leaving it. All three helped me — and two
of them helped me toward a **wrong** conclusion before the code corrected me. A
project that documents its reasoning gives an auditor more to work with and more
to be wrong about, and the second half of that is the price of the first.

**Twenty-ninth clean scan by the tools' own accounting** — and the one thing they
found between them, they found by contradicting each other.

## Disclosure timeline

- 2026-08-20 — scan run at `d8f63745`
- 2026-08-20 — curation; one real finding confirmed by reading the install path
  and the image pipeline
- 2026-08-20 — public courtesy issue filed; this post published

## Reproduce

```bash
git clone https://github.com/whiteguo233/OpenBiliClaw /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/whiteguo233-openbiliclaw --min-severity medium
```

---

*Scanned locally with [AI PatchLab](https://github.com/elfrost/ai-patchlab).
No source code left this machine, no AI provider was contacted, and no paid API
was called.*
