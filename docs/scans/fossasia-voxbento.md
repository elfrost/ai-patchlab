---
layout: default
title: "fossasia/voxbento: security scan"
description: "Security scan of fossasia/voxbento: 168 findings at medium+, 0 first-party defects after curation; one reachable dependency advisory (Starlette). Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-09-28
---

# fossasia/voxbento — security scan

**Repository:** [fossasia/voxbento](https://github.com/fossasia/voxbento)
**Commit scanned:** `81a6bbf` (`dev`, the default branch)
**Scan date:** 2026-09-28
**Disclosure status:** post-only — nothing first-party survived curation, so nothing was filed upstream. The one actionable item is a published advisory in a transitive dependency, fixed by one lockfile command.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 83 |
| Medium | 82 |
| Low | 0 |
| Info | 3 |

**Total findings:** 168 at `--min-severity medium` (0 first-party defects after curation; 1 reachable dependency advisory; the 3 info rows are coverage meta findings)

Voxbento is FOSSASIA's real-time interpretation platform for live events: interpreters
broadcast translated audio from a browser tab, attendees listen from theirs, and a
FastAPI portal handles everything around the audio — accounts and JWT sessions, the
admin console, booth coordination over WebSocket, background transcription and
translation, and a developer platform with OAuth2 clients and API keys (1.5k★,
Apache-2.0). It is one of the most active projects this series has picked: 167 merged
pull requests from 23 human authors and 77 closed issues in the 60 days before the scan.

**Scope of this write-up.** Every finding family below was checked against the code at
its call site. This page is *not* a manual review of the surfaces no rule inspects — the
OAuth2 provider, the developer API-key platform and the booth WebSocket layer were not
swept by hand this time. Read the result as "the tools' 168 findings are accounted for",
not as a clean bill of health for those surfaces.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | A shipped lockfile was not covered by the dependency scan |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep's 40 errors are all parse errors — 38 `PartialParsing`
and 2 syntax errors on the Jinja HTML templates and the two Dockerfiles, with **zero rule
timeouts** — so no first-party Python module went unexamined. `dependency-scan`
(pip-audit) resolved the version floors in `pyproject.toml` and did not read the shipped
`uv.lock`; Trivy read `uv.lock` directly, and every dependency finding below comes from it.

## Top findings

There is no first-party finding to lead with. The one item worth acting on is a
dependency advisory that happens to sit on the login path.

### 1. Starlette 1.1.0 in `uv.lock` — form limits ignored for urlencoded bodies (CVE-2026-54283)

- **File:** `uv.lock` (starlette 1.1.0, pulled in transitively by fastapi 0.141.1)
- **Tool:** trivy
- **Confidence:** high that it applies; the call sites are unauthenticated
- **Why it matters:** Starlette's `request.form()` enforces `max_fields` and
  `max_part_size` for multipart bodies but silently ignores them for
  `application/x-www-form-urlencoded`, so a URL-encoded body of any size is parsed in
  full. Voxbento calls `request.form()` directly on its `/register` and `/login` routes
  (`portal/routers/auth.py:114`, `:207`), which answer before any authentication. It is a
  resource-exhaustion advisory, not a data-exposure one.
- **Recommendation:** `uv lock --upgrade-package starlette`. FastAPI 0.141.1 requires only
  `starlette>=0.46.0`, so 1.3.1 resolves without touching FastAPI. The repository's daily
  `uv` Dependabot had no open pull request for it at scan time — Starlette is a transitive
  dependency, and version updates target the direct ones.

### 2. The docs-site build chain — 39 advisories that never run in production

- **File:** `website/package-lock.json`
- **Tool:** trivy
- **Confidence:** high that the versions are behind; not reachable in a deployed voxbento
- **Why it matters:** 39 of the 45 Trivy findings — `js-yaml` (7), `fast-uri` (6),
  `brace-expansion` (3), `svgo` (3) and 13 more packages — belong to `website/`, the
  Docusaurus 3.10.1 documentation site. CI runs `npm ci` and `npm run build` and publishes
  `website/build` as static files to GitHub Pages; nothing under `portal/` imports it.
- **Recommendation:** refresh the docs lockfile when convenient. `.github/dependabot.yml`
  covers `uv`, `github-actions` and `docker`, but not `npm`, so this lockfile has no
  automated updates today; adding an `npm` entry for `/website` would keep it current.

### 3. Hardening, not vulnerabilities

- **17 × `github-actions-mutable-action-tag`** across six workflows — SHA-pinning
  third-party actions is supply-chain hardening.
- **2 × `missing-integrity`** (`home.html:11`, `listener-event.html:4`) — both load the
  Tailwind Play CDN script, which is unversioned and cannot carry an SRI hash. Vendoring a
  Tailwind build removes the third-party script from the listener page; the project already
  did exactly that for its error pages in
  [#263](https://github.com/fossasia/voxbento/pull/263).
- **2 × container runs as root, 2 × `apt-get` without `--no-install-recommends`** (portal
  and floor-bot images) — image hygiene.

## Why the rest were dismissed

Of the 168 findings, 165 are accounted for below; the other 3 are the coverage meta findings
above. The scanner itself dropped 12 more under the `--min-severity` floor.

| Reason | Findings |
| --- | ---: |
| `placeholder-secret` | 50 |
| `mitigated-in-app` | 46 |
| `not-reachable` | 40 |
| `by-design` | 25 |
| `below-min-severity` (scanner) | 12 |
| `sample-or-demo` | 2 |
| `domain-noun-collision` | 1 |
| `dependency-currency` (finding 1) | 1 |

The largest family, `placeholder-secret` (50), is really **one value counted 49 times**:
a CI-only encryption key, prefixed `ci-`, is set in `.github/workflows/tests.yml` and quoted
in 17 files under `docs/plans/`. The fiftieth is `.env.example`, where
`JWT_SECRET=` is empty and the match runs onto the next line. The second family,
`mitigated-in-app` (46), is Semgrep's Django CSRF rule firing 45 times on a FastAPI app's
Jinja templates (below), plus one Jinja rendering that Starlette autoescapes.

## Patterns observed

**168 findings, zero defects, and two families explain most of the gap.** Neither is
about this project. Semgrep's `django-no-csrf-token` looks for Django's
`{% raw %}{% csrf_token %}{% endraw %}` in any `<form method="post">`, so it fires on every
form in a FastAPI app whether or not the app defends against CSRF. Voxbento does: both auth
cookies (`admin_token`, `user_token`) are set `HttpOnly` and `SameSite=Lax`, which browsers
withhold on cross-site POSTs; the admin router's writes are POST (39 routes) or DELETE (1);
and the developer dashboard adds a double-submit token checked with `secrets.compare_digest`.
One limit on that verdict: `Lax` does not cover top-level GET navigations, and some GET
handlers set cookies or write rows (logout and email-link redemption among them). Those sit
outside what this rule inspects and were not traced one by one here. The other family is
Gitleaks counting a single test fixture once per document that quotes it.

**The defaults fail closed.** The shipped `docker-compose.yml` falls back to
`SECRET_KEY=change-me` — the kind of line that is usually the headline of a scan like this.
Here it cannot produce a running production portal: the only signing key the code uses is
`effective_jwt_secret` (`JWT_SECRET`, else `SECRET_KEY`), and the FastAPI lifespan calls
`validate_production_secrets()` at startup (`fastapi_app.py:45`), which refuses to boot on
a known-weak value unless `DEBUG` is on. `DEBUG` defaults to off, and the guard has its own
tests. Third-party provider keys are encrypted at rest under a separate
`API_KEY_ENCRYPTION_KEY` (a `MultiFernet` over a comma-separated key list, so keys rotate
without breaking stored values), and the embeddable player's `postMessage` listener checks
the origin allow-list, when one is configured, before it will play, pause or change volume.

**The hardening is written down.** `docs/plans/` holds numbered implementation plans,
and several are security hygiene: `005-secret-key-startup-guard`,
`008-admin-access-control-dedup`, `015-debug-default-false`, `016-listener-rate-limit`.
That is the startup guard above, arriving as a plan with tests rather than a patch after an
incident. The same folder is also why Gitleaks reports 47 of its 50 hits: plans quote the
CI configuration they change.

**The drift is where automation does not reach.** 32 Dependabot pull requests were merged
in the 60 days before the scan, so direct dependencies move daily. What lags is the transitive
layer (Starlette arrives through FastAPI) and the one ecosystem Dependabot is not configured
for (the docs site's `npm` lockfile). One thing worth adding that no scanner flags: voxbento
has no `SECURITY.md`, and GitHub private vulnerability reporting is off, so the next person
with a real finding has no stated private channel. A short `SECURITY.md` naming one, or
enabling private reporting, would close that gap before it is needed.

## Notes on the tool

- **Framework-blind CSRF rule.** `django-no-csrf-token` went 45 for 45 false on a FastAPI
  app. The discriminating facts (cookie `SameSite`, form method, a double-submit check)
  live in Python the template rule never reads. Backlog: gate the rule on a Django
  dependency being present, or downgrade it to `info` when none is.
- **One secret, 49 findings.** Gitleaks reports a location, not a secret, so a single
  fixture quoted across planning documents surfaced as 49 high-severity findings. Backlog:
  fingerprint Gitleaks hits by secret hash and report one finding with N locations.
- **The partial-coverage advice still assumes timeouts.** The Semgrep meta finding says to
  "re-run Semgrep with a higher `--timeout`" although zero rules timed out and all 40 errors
  were parse errors, which no retry fixes. It was first noted on 2026-09-13 and is still
  open; the recommendation should key on the error type.
- **The `uv.lock` gap again.** pip-audit read the `pyproject.toml` floors and not the
  shipped lockfile; Trivy's lockfile read carried the dependency result, as on the last
  several scans. The meta finding made the gap visible, which is its job.

## Disclosure timeline

- 2026-09-28 — scan run at `81a6bbf` (`dev`)
- 2026-09-28 — curated: no first-party finding, so the bar for filing upstream was not met
  and nothing was filed
- 2026-09-28 — this page published

## Reproduce

```bash
git clone https://github.com/fossasia/voxbento /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/fossasia-voxbento --min-severity medium
```

---

## More from this series

- **Previous scan:** [superdesigndev/treg](superdesigndev-treg.html) — 2026-09-24, 1 real — withheld
- [Every scan in the series]({{ '/' | relative_url }}) — 112 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 26 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
