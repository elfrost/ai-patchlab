---
layout: default
title: "Zleap-AI/SAG: security scan"
date: 2026-08-27
---

# Zleap-AI/SAG — security scan

**Repository:** [Zleap-AI/SAG](https://github.com/Zleap-AI/SAG)
**Commit scanned:** `f1b4879c41974e82bb958335a2d29c767530ac26`
**Scan date:** 2026-08-27
**Disclosure status:** public courtesy issue filed (no private channel advertised — no `SECURITY.md` at root, `.github/`, or `docs/`; private vulnerability reporting disabled)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 44 |
| Medium | 13 |
| Low | 0 |
| Info | 3 |

**Total findings:** 60 (1 real after curation, plus one dependency-freshness note)

SAG is an original-architecture RAG knowledge base — a FastAPI backend
(`apps/api`), a Next.js web client (`apps/web`), and an Electron desktop wrapper
(`apps/desktop`) — shipped as a single-user personal app with a default
`docker compose` bind of `127.0.0.1`.

The scanner's 44 "high" findings collapsed to one real item under curation. The
one that matters is not in the scanner's list in any recognizable form: it is a
missing authentication check, and a rule that greps for dangerous *calls* cannot
see a *check that never happens*.

## Top findings

### 1. Login never verifies the password — any name logs in as the owner

- **File:** `apps/api/sag_api/services/auth_service.py:46` (`authenticate_or_register`), reached from `apps/api/sag_api/api/v1/auth.py:23` (`POST /api/v1/auth/login`)
- **Tool:** none — found by reading the auth seam, not by a scanner rule
- **Confidence:** high (reproduced against the real code)
- **Class:** conditional-verification bypass (CWE-287 / CWE-306) — the password
  check is guarded by a condition the caller controls, and identity falls back to
  "the first account that exists."
- **Why it matters:** the login handler passes the request straight into
  `authenticate_or_register(...)`. Inside, the password is only checked
  `if password_supplied` — and `password_supplied = bool(password)`, where
  `password` comes from `LoginRequest.password: str | None = None`. Omit the
  field and no verification runs at all. Worse, when no `email` is sent, the
  function resolves the user by falling back to
  `select(User).order_by(User.created_at.asc()).limit(1)` — the owner. So a
  single unauthenticated `POST /api/v1/auth/login` with body `{"name":"anything"}`
  returns the owner's account, silently renames it to the attacker-supplied name,
  and the handler issues a valid JWT for the owner's user id. That token unlocks
  every authenticated route, including `GET /api/v1/system/model-config`, which
  returns the configured LLM / embedding / MinerU provider settings.
- **Reachability:** the default compose binds `127.0.0.1`, so out of the box the
  attacker is a local process or a page that can reach the port (the desktop
  build runs a local server). It becomes network-wide the moment `BIND_ADDRESS`
  is set to `0.0.0.0` or the API is put behind a reverse proxy — both of which
  the compose file explicitly parameterizes. **Medium** as shipped; **High** for
  any non-localhost deployment.
- **The honest tension:** the web login page collects *only* a name
  (`api.login({ name })`), so name-only login is the intended UX for a personal
  app. But registration *requires* an 8+ character password
  (`RegisterRequest.password: Field(min_length=8)`), the app refuses to boot in
  `prod` with a default `SAG_SECRET_KEY`, and `SAG_ALLOW_REGISTRATION=false`
  exists to stop unwanted account creation. Those three controls only make sense
  if authentication is a boundary — and this login does not enforce it. If the
  design intent really is "no credential, ever," then the registration password
  and the registration lock are decorative, and that is worth saying out loud.
- **Recommendation:** decide whether login is a credential check. If yes, verify
  the password whenever the resolved account has one (and add a password field to
  the login form), and drop the "first user by `created_at`" fallback so identity
  is never assigned by ordinal. If no, document that the API must never be exposed
  beyond loopback and drop the registration password so the control isn't
  misleading. Filed for the maintainers to choose — the fix is a product decision,
  not a one-liner, precisely because the naive "always verify" break the shipped
  name-only login page.

### 2. Web dependency freshness (secondary — hardening, not a live bug)

- **File:** `apps/web/package-lock.json` (`next@15.5.20`, `sharp`, `postcss`, `nanoid`, `js-yaml`)
- **Tool:** trivy
- **Confidence:** medium — version-match only; reachability of each specific CVE
  (Next.js SSRF / DoS / info-disclosure, sharp libvips, postcss) was not confirmed
  against the app's actual usage.
- **Why it matters:** a routine dependency refresh clears the advisory noise and
  is cheap. None of these rise to the level of the auth finding.
- **Recommendation:** bump the web dependencies to current patch releases.

## Patterns observed

This is well-built code, and the scanner's raw output actively hides that. Every
one of the six SQLAlchemy `text()` / raw-query "high" findings is an
identifier-only interpolation — a table name drawn from a hard-coded map or from
`sqlite_master`, with the actual *values* bound through `bindparam(...)` or `?`
placeholders right beside the flagged line. The three `child_process` /
`spawn(shell=True)` findings are all dev, build, and release scripts spawning
fixed argv (`npm run build`), not runtime attack surface. The fourteen
"generic-api-key" secrets are SHA-256 tree digests in `.public-sync-state.json`
and fixtures in `test_*.py`. Curation turned 44 highs into zero.

What the app does well is the more interesting half. The upload path
(`attachments.py`) generates its own UUID filenames, validates retrieval with a
strict `^[0-9a-f]{32}\.(png|jpe?g|webp|gif)$` regex, caps size, and requires auth
on both ends. The MinerU result fetcher resolves the host and rejects any address
that `is_global` fails — a real SSRF guard. The Dify compatibility endpoint —
the one route that is deliberately unauthenticated — gates on a constant-time
`compare_digest` API key and fails closed when the key is unset. The `prod`
secret-key guard is enforced at startup. The two archive-handling paths read
entries in memory (`archive.read(...)`) and never extract to disk, so there is no
zip-slip.

So the single real finding sits inside a codebase that clearly understands
security — which is exactly the shape these scans keep surfacing. The bug is not
a missing seatbelt on obviously dangerous code; it is one control (the login) not
enforcing a boundary that three *other* controls (registration password, prod
key guard, registration lock) all assume exists. No static rule sees a boundary
that isn't there. You find it by tabulating every route against its guard, noticing
the one login path that resolves identity without a credential, and then running
it.

## Notes on the tool

- **The dependency scan silently covered nothing.** `scan_dependency` only
  probes the repo root, found no manifest there, and emitted
  `dependency-scan-no-supported-manifest`. The real Python surface lives in
  `apps/api/pyproject.toml` + `apps/api/uv.lock`. Run by hand, pip-audit resolved
  128 dependencies with **zero** known vulnerabilities — a true clean, but the
  scanner would have reported "no manifest" and moved on. Backlog: teach the
  dependency scanner to walk into sub-projects (`apps/*/pyproject.toml`), the same
  way the fingerprint indexer already recurses.
- **No rule for missing-auth.** Every finding here is a dangerous *call*; the real
  bug is a *check that never runs*. This is the recurring gap — the scanner is
  blind to absence-shaped findings. Curation, not the scanner, is the product.
- The identifier-only SQL false positives are the single most common noise class
  across the whole series (now nine appearances). Worth a post-filter that reads
  one line of context and collapses "interpolated identifier, bound values" to
  info.

## Disclosure timeline

- 2026-08-27 — scan run; auth bypass reproduced against the real code
- 2026-08-27 — public courtesy issue filed (no private channel advertised)
- 2026-08-30 — **fixed.** [PR #156](https://github.com/Zleap-AI/SAG/pull/156)
  merged ("Closes #153") and the issue closed as completed, three days after
  filing. The maintainers took the question the report actually asked — *is this
  login a credential check?* — and answered it with an explicit deployment mode
  rather than a patch. `SAG_AUTH_MODE` is now `local | password`. In `password`
  mode, `POST /auth/login` routes to `authenticate(email, password)`, which calls
  `verify_password` unconditionally; the name lookup and the
  `order_by(created_at.asc()).limit(1)` first-user fallback are both gone from
  that path, and JWTs issued under the old local identity are rejected after the
  mode switch. The default stays `local`, preserving the shipped single-user
  name-only experience — which is the honest outcome: the personal-app UX was
  never the bug. The bug was that a deployment had no way to say
  "authentication is a boundary here," so the registration password and
  `SAG_ALLOW_REGISTRATION` were guarding a door that login left open. Now the
  three controls agree with each other. The PR also lands regression tests
  naming this issue: name bypass, missing password, wrong password, first
  credential bootstrap, old-token invalidation, and local-mode compatibility
  (616 backend tests passing).

## Reproduce

```bash
git clone https://github.com/Zleap-AI/SAG /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/zleap-ai-sag --min-severity medium
# dependency surface the root-only scan missed:
cd /tmp/scan-target/apps/api && pip-audit .
```
