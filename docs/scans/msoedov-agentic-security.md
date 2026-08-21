---
layout: default
title: "msoedov/agentic_security: security scan"
description: "Security scan of msoedov/agentic_security: 9 findings, 2 real best-practice items + 1 disclosed privately"
date: 2026-05-15
---

# msoedov/agentic_security — security scan

**Repository:** [msoedov/agentic_security](https://github.com/msoedov/agentic_security) — 1.9k★, Apache-2.0, an Agentic LLM vulnerability scanner / AI red-teaming kit (i.e. a dynamic-behavior security tool, complementary to AI PatchLab's static-code focus).
**Commit scanned:** `2aabcef` (HEAD of `main` at scan time)
**Scan date:** 2026-05-15
**Disclosure status:** Two findings filed as a public courtesy issue on the agentic_security repo — **both resolved** in commit [`dd59704`](https://github.com/msoedov/agentic_security/commit/dd59704f) with regression tests; [issue #298](https://github.com/msoedov/agentic_security/issues/298) closed 2026-07-31. **One additional finding was reported privately** via GitHub's Private Vulnerability Reporting (active on this repo); it remains in triage and will be added to this write-up after the maintainer's response.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 6 |
| Medium | 3 |
| Low | 0 |
| Info | 0 (filtered) |

**9 total findings. After curation: 2 best-practice issues worth flagging publicly, 1 finding disclosed privately, and 6 false positives or out-of-scope items.**

This is the first scan in our series with multiple findings substantive enough to warrant action — and the first one where a finding hit the bar for private disclosure ahead of public publication. Scanning a security tool tends to be illuminating in both directions.

## Top findings (curated, public)

### 1. `agentic_security/middleware/cors.py:10` — wildcard CORS with credentials

**Tool:** Semgrep (`wildcard-cors`, medium confidence)
**Verdict:** **Real misconfiguration.**

```python
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

The combination of `allow_origins=["*"]` with `allow_credentials=True` is explicitly forbidden by the [CORS specification](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS/Errors/CORSNotSupportingCredentials). Most browsers will refuse to honor it (they'll silently strip credentials from cross-origin requests), but the server's intent is to accept *any* origin with credentials — which would, if the spec didn't intervene, let any malicious page running anywhere read authenticated responses from the agentic_security server.

The fix is to enumerate explicit allowed origins (or accept that credentials should be off for an `*` origin policy):

```python
origins = ["http://localhost:3000", "https://your-frontend.example"]
# or, if credentials genuinely aren't needed cross-origin:
# allow_credentials=False
```

### 2. `agentic_security/routes/static.py:104` — path-traversal risk in the icons proxy

**Tool:** Semgrep (`ssrf-requests`, medium confidence)
**Verdict:** **Plausibly exploitable — defense-in-depth recommended.**

```python
@router.get("/icons/{icon_name}")
async def serve_icon(icon_name: str) -> FileResponse:
    icon_path = ICONS_DIR / icon_name
    if not icon_path.exists():
        url = f"https://registry.npmmirror.com/@lobehub/icons-static-png/latest/files/dark/{icon_name}"
        response = requests.get(url)
        if response.status_code == 200:
            icon_path.write_bytes(response.content)
        ...
    return get_static_file(icon_path, content_type="image/png")
```

Two related concerns:

1. **`icon_name` is interpolated into a filesystem path** (`ICONS_DIR / icon_name`) without validation. FastAPI's `{icon_name}` path parameter is single-segment by default, but URL-encoded path separators (`%2F`) can still slip through in some Starlette versions, and the parameter is also used to write a file via `icon_path.write_bytes`. A malicious or malformed value could lead to writing outside `ICONS_DIR`.

2. **Same value is interpolated into the upstream URL** to `registry.npmmirror.com`. The host is fixed, so this isn't a classic SSRF (no choosing the target). But an attacker can make the server cache an arbitrary file from `registry.npmmirror.com` under a name they control.

Tactical fix: validate `icon_name` against a strict allowlist before either filesystem access or the upstream request:

```python
ICON_NAME_RE = re.compile(r"^[a-z0-9_-]+\.png$")
# in the handler:
if not ICON_NAME_RE.match(icon_name):
    raise HTTPException(status_code=400, detail="Invalid icon name")
```

Defense in depth: also resolve and verify the constructed path stays inside `ICONS_DIR` with `icon_path.resolve().is_relative_to(ICONS_DIR.resolve())`.

### 3-9. False positives and out-of-scope items (still worth noting for tooling feedback)

| Finding | File | Verdict |
|---|---|---|
| `direct-use-of-jinja2` | `agentic_security/routes/static.py:18` | **FP — `autoescape=True` is explicitly set** in the same `Environment(...)` call. Semgrep's rule didn't read the kwargs. |
| `Potential secret detected: stripe-access-token` | `tests/unit/refusal_classifier/test_pii_detector.py:14` | **By design — test data for a PII detector.** The string `sk_test_1234567890abcdef` is *literally the fixture that exercises the detector's API-token rule*. |
| `Potential secret detected: generic-api-key` | `tests/unit/test_security.py:128` | **By design — test data for a log-sanitization function.** The fixture is `'api_key="sk-1234567890"'` and the test asserts that the sanitizer removes it. |
| `prototype-pollution-loop` | `agentic_security/static/vue.js:518` | **Out of scope — vendored Vue.js**, not the project's code. |
| `python37-compatibility-importlib2` | `agentic_security/refusal_classifier/model.py:1` | **Not security** — a Python 3.7 compatibility hint, irrelevant given the project requires `>= 3.12`. |

## Patterns observed

**Scanning a security tool sharpens the contrast between syntactic patterns and intent.** Three of the seven non-private findings here (Stripe token in `test_pii_detector`, API key in `test_security`, and the `jinja2.Environment` with `autoescape=True`) are textbook examples of static scanners firing on the **shape** of a pattern without understanding the **role** of the surrounding code. A PII detector that doesn't test against fake-but-realistic credentials would be a useless PII detector. A jinja2 `Environment` that explicitly sets `autoescape=True` is the opposite of the vulnerability that the rule is designed to catch. The signal in static-scanner output lives in the rule names; the noise lives in the next half-step of context.

**Two findings clear that bar:** the wildcard-CORS misconfiguration is unambiguous, and the icons-proxy route has both filesystem-write and upstream-fetch paths that warrant defense-in-depth even if today's FastAPI behavior makes the worst-case exploit narrow. These are textbook web-app hygiene items that any maintainer would want surfaced.

**One finding warranted private disclosure** instead of immediate publication. Agentic Security has Private Vulnerability Reporting enabled on the repo, which is exactly the channel a third-party scanner should use when a finding's exploitability depends on context the reporter can't determine from the outside. This page will be updated with the resolution after the maintainer responds — a delayed-disclosure section, not a swept-under-the-rug omission.

**The meta-angle**: this is the first scan in our series where AI PatchLab found more than just curation-fodder false positives. The fact that the target is itself a security tool isn't ironic — it's confirming that **static code analysis and dynamic agentic red-teaming are non-overlapping specialties**, and that the maintainers of one specialty are exposed to the blind spots of the other.

## Notes on the tool

Recurring items from prior scans (still in the backlog):

- **No path-level suppression / `.aipatchlabignore`** — `static/vue.js` (vendored library) should be excludable; `tests/**/*_pii_detector*` likewise (a PII detector's tests will always look like a "secrets file" to a string-based scanner).
- **No deduplication across files** — the AUTH_TOKEN finding (privately disclosed) fired identical findings in two different files at the same line offset; a single grouped entry would be clearer.

New items from this scan:

- **The `Repository:` header still shows the temp clone path** even on the `agentic_security` scan output — already in the backlog from the gptme write-up.
- **The Semgrep `direct-use-of-jinja2` rule fires regardless of `autoescape` kwarg value.** Worth either suppressing this in our `enrich_findings` layer (by parsing the `autoescape=True` kwarg from the matched code), or downgrading its confidence to `low` when an explicit `autoescape=True` is in the same expression.

## Disclosure timeline

- **2026-05-15** — Scan run, top findings curated.
- **2026-05-15** — One finding disclosed privately via GitHub Private Vulnerability Reporting on agentic_security; awaiting maintainer response.
- **2026-05-15** — Public courtesy issue filed on agentic_security with the two publishable items (CORS + path-traversal); this post published.
- **2026-06-22** — Both public items fixed in commit [`dd59704`](https://github.com/msoedov/agentic_security/commit/dd59704f) by contributor Devam Shah, with regression tests for each (`tests/unit/test_cors_middleware.py`, `tests/integration/routes/test_static_icon_validation.py` — traversal, encoded slash, null byte, trailing newline, wrong extension).
- **2026-07-31** — [Issue #298](https://github.com/msoedov/agentic_security/issues/298) closed as completed.
- **TBD** — This page updated with the resolution of the privately-disclosed finding (still in triage as of 2026-08-02).

### What the fix corrected in *our* analysis

Worth recording, because the maintainer-side fix was **more accurate than the report that prompted it**. The write-up above describes the wildcard-CORS item as a spec violation whose practical effect is that *"any origin may make unauthenticated requests, and credentials silently disappear cross-origin"* — i.e. annoying, not dangerous. The commit message rejects that framing:

> CORS: drop `allow_credentials=True`. With `allow_origins=['*']` Starlette **reflects the request Origin** and emits `Access-Control-Allow-Credentials: true` on any credentialed request — a reflect-any-origin hole.

That is correct, and it matters. Starlette's `CORSMiddleware` only sends the literal `Access-Control-Allow-Origin: *` when `allow_all_origins and not allow_credentials`; with credentials enabled it falls through to the explicit-origin path and echoes back whatever `Origin` the caller sent. The browser therefore never sees the illegal `*` + credentials pairing that would have triggered its own protection — it sees a well-formed, fully-credentialed grant to the attacker's origin. **The spec violation the scanner rule is named after never actually occurs; what occurs is the vulnerability the spec exists to prevent.**

The general lesson for curation: for a permissive-config finding, the severity depends on *what the framework does with the illegal combination*, not on the combination being illegal. Reading the middleware source (or reproducing the response headers, which is one command) converts a hygiene note into an exploitability claim — the technique that has since become routine in this series.

The path-traversal item landed as filed: strict allowlist (`re.fullmatch(r"[A-Za-z0-9._-]+\.png")`) **plus** a `resolve()` / `is_relative_to(ICONS_DIR)` containment check, guarding both the local write and the outbound npmmirror fetch (CWE-22 and CWE-73), with the rationale written into the endpoint's docstring.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/msoedov/agentic_security" \
  --reports-dir reports/msoedov-agentic-security \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
