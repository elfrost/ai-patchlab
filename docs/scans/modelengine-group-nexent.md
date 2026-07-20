---
layout: default
title: "ModelEngine-Group/nexent: security scan"
date: 2026-07-20
---

# ModelEngine-Group/nexent - security scan

**Repository:** [ModelEngine-Group/nexent](https://github.com/ModelEngine-Group/nexent)
**Commit scanned:** `ea3fd0711fb21310374b89737c7061f6777a1c58`
**Scan date:** 2026-07-20
**Disclosure status:** post-only — strict-norm (private security policy); no real finding to disclose

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 33 |
| Medium | 82 |
| Low | 0 |
| Info | 0 |

**Total findings:** 115 (0 real, exploitability-shaped after curation) — **19th clean scan**

## What it is

Nexent is a zero-code platform (5.7k★, ModelEngine-Group) for auto-generating
production-grade AI agents: a FastAPI backend that speaks its own JWT/CAS/Supabase
auth, brokers MCP tool calls (`fastmcp`), runs a Ray/Celery data-processing tier,
and ships a full Docker/Kong/Helm deploy stack. That is a *lot* of surface — a
custom auth layer, a tool broker, a monitoring SQL tier, and a dozen CI/CD
workflows — which is exactly why the 33 "highs" look alarming until you trace
each one to where it's actually called. On an agent platform the finding that
matters is *the auth boundary*, and this one holds.

## Top findings

There are no real, exploitability-shaped findings after curation. The interesting
part is *why* each high-severity hit is a non-issue — grouped by the question it
raised.

### The auth boundary (the finding that would matter) — holds

Nexent implements its own JWT verification in `backend/utils/auth_utils.py`, and
two Semgrep highs land here:

- **`unverified-jwt-decode` (`auth_utils.py:453`)** — `jwt.decode(token,
  options={"verify_signature": False})`. Read the function: it's
  `extract_session_id_from_authorization`, which pulls only the `sid` claim *for
  idempotent logout*, then hands it to `ensure_cas_session_active_from_authorization`
  which checks the CAS session against server-side state. It's a **peek-then-check**,
  not an auth decision — the same shape [IBM ContextForge](ibm-mcp-context-forge.html)'s
  peek-`iss` pattern took. Every *authenticating* decode (`_decode_jwt_token`,
  `_decode_jwt_token_allow_expired`) verifies the signature with
  `algorithms=["HS256"]` pinned and the env-loaded `SUPABASE_JWT_SECRET`, and
  **fails closed** if that secret is unset.
- **`jwt-hardcode` (`auth_utils.py:564`)** — a literal `MOCK_JWT_SECRET_KEY =
  "nexent-mock-jwt-secret"`. It signs `generate_test_jwt`, whose only two callers
  in the whole repo are its own definition and `test/backend/utils/test_auth_utils.py`.
  Tokens minted with the mock secret can't validate against the production verifier
  (which requires `SUPABASE_JWT_SECRET`), so it's a test helper that happens to live
  in a prod module — a hygiene nit, not an auth bypass. Same mandated-vs-mock
  distinction as the [linkedin-mcp](stickerdaniel-linkedin-mcp-server.html) active-harm
  lesson, inverted: here the "secret" is inert by construction.

### The monitoring SQL — parameterized-identifier FP

**`avoid-sqlalchemy-text` (`backend/apps/monitoring_app.py:92`)** builds a
`text(query_sql)` with two f-string slots, which reads as injection on a
per-tenant metrics query. But `time_filter` comes from `_compute_time_range_filter`,
where `hours = {"24h": 24, "7d": 168, "30d": 720}.get(time_range, 24)` — the raw
`time_range` string is *never* interpolated, only the resolved **integer constant**
(always one of three, default 24). The `tenant_filter` uses a bound `:tenant_id`
param. Every data value is bound; only whitelisted constants are formatted. This
is the [#1 recurring cluster](mnemosyne-oss-mnemosyne.html) in the series — the
parameterized-SQL identifier false positive — in its smallest, cleanest form.

### The CI/CD workflows — privileged-trigger hardening, not injection

**11 `run-shell-injection`** highs span `build-offline-package.yml`,
`docker-deploy.yml`, `docker-build-push-*.yml`, and `sdk_publish.yml`. Every one
of those workflows is triggered by **`workflow_dispatch`** — a maintainer manually
clicking "Run workflow" with repo write access. An attacker can't reach the
interpolated `inputs.version` / `inputs.deployment_mode` steps without already
being a maintainer. That's the privileged-trigger side of the
[openmed](maziyarpanahi-openmed.html) lesson: `workflow_dispatch` = hardening,
`pull_request_target` = vulnerability. Quoting the inputs is good practice; none
of it is exploitable.

### Infra & container hygiene — deployer's call

The remaining highs are the deploy stack: ~7 `detect-insecure-websocket` (`ws://`
in Kong / docker-compose / Helm — internal service-mesh config), and ~8
Dockerfile `last-user-is-root` / `missing-user` + Trivy `DS-0002`/`DS-0025`
(containers running as root). Standard container-hardening notes for a
self-hosted stack, not app-level vulnerabilities. The lone Gitleaks hit
(`deploy/docker/deploy.sh:622`) is `elastic:${ELASTIC_PASSWORD:-nexent@2025}` — a
**default-password fallback** in the bootstrap script, overridable by env. Weak
default worth documenting; not a leaked live credential.

The 82 mediums are almost entirely `github-actions-mutable-action-tag` (pin
third-party actions to a commit SHA rather than a tag) — the same CI-lint bulk
that inflates every well-tooled repo's count.

## Patterns observed

**Count scales with surface, not risk — again.** 115 findings, 0 real. Nexent has
one of the widest surfaces in this series (custom auth + MCP broker + SQL
monitoring + Ray tier + full Docker/Kong/Helm deploy), and the raw number tracks
the *number of moving parts*, not the number of ways in. Almost every high is an
infrastructure-config or CI-lint hit that a scanner can't contextualize: it sees
`ws://` and a root Dockerfile user and a shell step interpolating an input, but
not that the WebSocket is internal, the container is a deploy artifact, and the
workflow only a maintainer can trigger.

**The auth layer is where a custom platform earns or loses trust, and nexent
built it correctly.** Rolling your own JWT verification is where most agent
platforms slip — unpinned `algorithms`, `verify_signature=False` on the wrong
path, a fallback secret that the verifier also accepts. Nexent avoids all three:
signature always enforced, HS256 pinned, secret env-loaded and fails-closed, and
the one unverified decode is scoped to logout-idempotency with a server-side CAS
session check behind it. The hardcoded secret is genuinely test-only. This is the
mark of a team that understood the threat model of its own auth code.

**Dependencies pinned by floor, audited by nobody's default tooling.** The backend
`pyproject.toml` pins with `>=` floors (`fastapi>=0.115.12`, `authlib>=1.3.0`,
`PyJWT>=2.8.0`, `cryptography>=42`) plus `defusedxml` for XXE defense — so a fresh
resolve pulls current patched versions. One nuance worth a deployer's eye:
`fastmcp>=2.14.2,<3.0` caps below the 3.x line, so any fix that only landed in
fastmcp 3.x wouldn't be reachable without lifting the ceiling. See the tool note
below on why this run didn't audit those deps directly.

## Notes on the tool

- **Nested-manifest dependency-audit gap (recurring).** Nexent's Python manifests
  live at `backend/pyproject.toml` and `sdk/pyproject.toml` — there is *no* root
  manifest — so AI PatchLab's root-anchored pip-audit runner found nothing to scan
  and Python dependency CVEs went **unaudited** this run (Trivy covered only the
  Dockerfiles). This is the same monorepo lockfile-coverage asymmetry seen on
  [Kiln](kiln-ai-kiln.html): the dep audit should discover and iterate over nested
  manifests, or at minimum emit a *medium* (not info) meta-finding naming the
  uncovered manifests so a `--min-severity medium` run doesn't silently look
  dep-clean. **Backlog: nested-manifest discovery for the dependency scanner.**
- **`run-shell-injection` still lacks trigger context.** As flagged on
  [openmed](maziyarpanahi-openmed.html) and [optillm](algorithmicsuperintelligence-optillm.html),
  the finding should carry the workflow `on:` trigger — `workflow_dispatch` /
  `push` (privileged → hardening) vs `pull_request_target` / `issue_comment`
  (attacker-reachable → real). All 11 here were the privileged kind; the tool made
  a human read every YAML to learn that.
- **Parameterized-identifier SQL FP, one more for the tally.** The
  `avoid-sqlalchemy-text` heuristic should check whether f-string slots resolve to
  bound params / whitelisted constants before flagging `high`. Same class as
  mnemosyne (140), codex-lb, potpie, AG2, Agently.
- **Test-secret in a prod module.** `jwt-hardcode` on a `MOCK_*` constant whose
  only callers are the test module is a candidate-FP the confidence layer could
  downgrade (grep the symbol's callers for a `test/` confinement).

## Disclosure timeline

- 2026-07-20 — scan run
- 2026-07-20 — public post (this page); **post-only** — the repo ships a real
  private-reporting `SECURITY.md` (security-team email, coordinated-disclosure
  timeline, Hall of Fame) → strict-norm, and curation found no real finding to
  report privately regardless

## Reproduce

```bash
git clone https://github.com/ModelEngine-Group/nexent /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/modelengine-group-nexent --min-severity medium
```

---

*Generated by [AI PatchLab](https://github.com/elfrost/ai-patchlab). Findings are
curated: noise filtered, top items highlighted, threat paths traced by hand.
This is a point-in-time signal, not an audit.*
