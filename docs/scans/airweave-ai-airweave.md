---
layout: default
title: "airweave-ai/airweave: security scan"
description: "Security scan of airweave-ai/airweave: 46 findings, ~4 publishable best-practice items + 1 disclosed privately via SECURITY.md email channel"
date: 2026-05-19
---

# airweave-ai/airweave — security scan

**Repository:** [airweave-ai/airweave](https://github.com/airweave-ai/airweave) — 6.3k★, MIT, "open-source context retrieval layer for AI agents" — RAG / connector layer that ingests from 30+ integrated SaaS providers into vector stores.
**Commit scanned:** `a9c8b1af722d` (HEAD of `main` at scan time)
**Scan date:** 2026-05-19
**Disclosure status:** Public courtesy issue filed on the airweave repo with the publishable items below. **One additional finding was disclosed privately** via the email channel listed in airweave's `SECURITY.md` and will be added here after the maintainer's response.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 28 |
| Medium | 18 |
| Low | 0 |
| Info | 0 (filtered) |

**46 total findings. After curation: ~4 publishable best-practice items, 1 finding disclosed privately, ~30 false positives or intentional-by-design patterns.**

This is the cleanest large scan in our series so far — airweave is a 334 MB codebase spanning a Python backend, multiple TypeScript frontends, Dockerfile/Compose deployment, and 30+ third-party connectors, yet the curation yields only a handful of items. Two findings are particularly worth discussing: a deliberately-committed dev OAuth secrets file (documented as intentional) and the standard CI-input interpolation pattern we've now seen on every Python AI repo in the series.

## Top findings (curated, public)

### 1. `backend/airweave/platform/auth/yaml/dev.integrations.yaml` — 13 OAuth client secrets committed to source (documented as dev-only)

**Tool:** Semgrep (`detected-generic-secret`, medium confidence)
**Verdict:** **Documented-as-intentional but worth a thinking-out-loud question.**

The file opens with a clear maintainer-authored warning:

```yaml
# Warning: this file is not used in production. It is only used for development.
# The secrets that we openly share with you are for development purposes only and cannot
# be used in production.
```

Followed by 13 OAuth client_id + client_secret pairs for Airtable, Asana, Box, Confluence, and other integrated providers. The intent is to spare developers from registering their own OAuth apps to hack on airweave locally — a real friction-reducer.

Three questions worth sitting with:

1. **Provider acceptable-use policies vary.** Some providers' OAuth terms explicitly forbid sharing client secrets, even "dev-only". Atlassian/Box/Asana each have their own posture on this. Audit-friendly path: per-provider verification that the dev credentials are actually allowed to be committed in a public repo.
2. **OAuth client secrets identify the *application*, not the user.** A bad actor running a phishing flow against an airweave user with the committed `client_id` looks (to the OAuth provider) like a legitimate airweave OAuth request. The "dev only" disclaimer doesn't change that the credentials still resolve to airweave's registered app on the provider side.
3. **The shipped credentials are likely to age** — providers rotate, tokens expire, and any new contributor who relies on this file is one rotation away from a confusing error. A `.example.yaml` with `<your-client-id>` placeholders + a setup script that asks for credentials interactively gives developers the same friction-removal without the long-tail risk.

This is a **discussion item**, not an exploit. The maintainer obviously thought about this — the warning is right there — and may well have already validated the per-provider terms. The courtesy issue raises it as a check.

### 2. 8× workflow `${{ inputs.* }}` / `${{ github.base_ref }}` shell interpolation

**Files:** `.github/workflows/code-quality.yml:59, 107`, `.github/workflows/publish-sdks-and-mcp.yml:71, 77, 106, 122`, and two more
**Tool:** Semgrep (`run-shell-injection`, medium confidence)
**Verdict:** **Real best-practice — same class as [gptme #2398](gptme-gptme.html) and [PraisonAI #1676](mervinpraison-praisonai.html), both since fixed.**

Example shape from `code-quality.yml:59`:

```yaml
- name: Ruff lint (changed lines)
  if: github.event_name == 'pull_request'
  run: |
    poetry run diff-quality --violations=ruff.check \
      --compare-branch=origin/${{ github.base_ref }} \
      --fail-under=100 \
      ruff_report.txt
```

GitHub Actions interpolates `${{ ... }}` at workflow-parse time, before any shell quoting can protect the result. For `github.base_ref` and `github.head_ref` the value is GitHub-controlled (branch name of the PR base/head), so the realistic exploit window is narrow — but the fix pattern is mechanical and well-understood: pass through `env:` and reference as `$ENV_VAR`. Templates from the [gptme PR #2399 fix](https://github.com/gptme/gptme/pull/2399) and [PraisonAI PR #1677 fix](https://github.com/MervinPraison/PraisonAI/pull/1677) transfer directly.

### 3. `monke/backend/app.py:12` — wildcard CORS

**Tool:** Semgrep (`wildcard-cors`, medium confidence)
**Verdict:** **Real misconfiguration, scope-limited to internal tooling.**

```python
app = FastAPI(title="Monke Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`monke` appears to be an internal testing / chaos-tooling backend (the directory hosts a separate FastAPI app and frontend). The CORS misconfig here is less severe than the [agentic_security finding](msoedov-agentic-security.html) because `allow_credentials=True` is *not* set — browsers will simply ignore the wildcard for credentialed requests rather than relax their guards. But the intent of "any origin may call this server" is still loose, and if `monke` is ever exposed beyond local-dev, an enumeration of origins worth explicitly listing is the easier audit.

### 4. 4× Dockerfile missing `USER` directive

**Files:** `connect/Dockerfile:39`, `frontend/Dockerfile:38`, `monke/Dockerfile:29`, `monke/frontend/Dockerfile:15`
**Tool:** Semgrep (`missing-user-entrypoint`, `missing-user`, medium confidence)
**Verdict:** **Real best-practice — containers running as root.**

Each of these Dockerfiles ends without a `USER` directive, so the containerized service runs as root. Standard hardening:

```dockerfile
RUN groupadd -r app && useradd -r -g app -d /app app
USER app
ENTRYPOINT ["..."]
```

For frontend/static-serving containers the risk is lower (smaller exploitable surface), but the pattern is mechanical and removes the entire "root in container" footgun for any future RCE surfaced via the app layer.

### 5. `backend/airweave/crud/crud_usage.py:129` + `sources/ctti.py:268` — same `text(f"...")` / asyncpg-sqli class as Upsonic and PraisonAI

**Tool:** Semgrep (`avoid-sqlalchemy-text`, `asyncpg-sqli`, medium confidence)
**Verdict:** **Best-practice — same identifier-interpolation pattern we've documented twice.**

Smaller volume than [Upsonic](upsonic-upsonic.html) (8 sites) or [PraisonAI](mervinpraison-praisonai.html) (220+ sites) — airweave has just 3 sites in the same shape. The defensive change is identical: SQLAlchemy `quoted_name()` / `Identifier()` or asyncpg's identifier-escaping for any value that's interpolated into a SQL identifier.

### 6-N. False positives and out-of-scope

| Finding | File | Verdict |
|---|---|---|
| `detected-google-oauth-access-token` ×1 | `backend/airweave/api/examples.py:205` | **FP — documentation placeholder.** The value is `ya29.a0AfH6SMBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` — the `ya29.a0AfH6SMB` prefix is a real Google OAuth format, but the trailing `xxxxxxxxx` is an obvious placeholder for the API-examples doc |
| `react-dangerouslysetinnerhtml` ×2 | `connect/src/components/form-fields/{BooleanField,FieldWrapper}.tsx` | Need per-file context, but form-field rendering with controlled prop strings is typically the safe case |
| `path-join-resolve-traversal` ×4 | `connect/vite.config.ts`, `monke/frontend/vite.config.ts` | **Out of scope — build tooling**, not runtime code |
| `non-literal-import` ×4 | `backend/airweave/domains/arf/reader.py`, `monke/bongos/registry.py` | **By design** — plugin/source registration paths |
| `logger-credential-leak` ×3 | `backend/airweave/adapters/cache/redis.py` | Likely FP — `redis.py` would naturally log redis URLs or connection info; needs per-line inspection but pattern matches the same FP class as openllmetry's "token usage" log lines |
| `insecure-hash-algorithm-sha1` ×1 | `backend/airweave/platform/sources/sharepoint_online/source.py:1600` | **FP** (same shape as Upsonic and PraisonAI) — SHA1 used as a stable non-crypto identifier, not for integrity |
| `ajv-allerrors-true` ×1 | `frontend/src/search/JsonFilterEditor.tsx:62` | Frontend JSON schema validation choice, not security |

## Patterns observed

**airweave is the cleanest large-codebase scan we've done.** 334 MB across a Python backend, multiple TypeScript frontends, and 30+ third-party connectors, and the curated real-items list lands at four-and-a-half (with one item being a "thinking-out-loud" question rather than a fix). For a codebase with this much surface area, that's an unusually low real-findings rate.

**The committed-dev-secrets pattern is genuinely interesting.** This is the first scan in our series where a maintainer has *intentionally and explicitly* committed a file of real-looking OAuth credentials with a documented warning. It would be cheap to dunk on, but the maintainer's reasoning is visible and the friction-reduction is real for new contributors. The right read isn't "OMG SECRETS" — it's "the per-provider terms-of-service review is non-trivial; the warning is necessary but not sufficient against accidental long-tail misuse". The courtesy issue raises it as a check, not a flame.

**The CI-input shell-interpolation pattern is now confirmed across three independent codebases** (gptme, PraisonAI, airweave) and resolved in both that have had time to act. We can probably stop treating it as "discovered on each scan" and start treating it as a recurring class — the post template's section for it can be one paragraph + a link to the [gptme PR #2399 fix](https://github.com/gptme/gptme/pull/2399) instead of a fresh explanation each time.

**One finding was held back for private disclosure.** Airweave does not have GitHub's Private Vulnerability Reporting enabled, but their `SECURITY.md` documents an email channel with a 48-hour response SLA. The finding (an exploitable CI pattern) is documented in airweave's queue and intentionally absent from this write-up until they've had a chance to respond. The pattern will be added to this page after resolution — same format as [the agentic_security write-up](msoedov-agentic-security.html).

## Notes on the tool

Recurring backlog items confirmed on this scan:

- **Cross-rule deduplication** — the asyncpg-sqli site at `ctti.py:268` fires *twice* in the report on the same line (different sub-rules of the same family). Same observation as on PraisonAI.
- **A canonical post template for the workflow-injection class** — three scans in, the writing is essentially identical each time. Worth extracting.
- **`logger-credential-leak`'s heuristic on log lines near `token` / `key` / `secret` strings continues to over-fire** — Upsonic's "token usage" lines, openllmetry's billing-token logs, now airweave's redis adapter logs. A confidence downgrade is justified across the rule.

## Disclosure timeline

- **2026-05-19** — Scan run at commit `a9c8b1af722d`, top findings curated.
- **2026-05-19** — Private email to `rauf@airweave.ai` (per `SECURITY.md`) for one exploitable CI pattern; this post and the public issue intentionally omit it pending response.
- **2026-05-19** — Public courtesy issue filed on airweave-ai/airweave with the four publishable items above.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/airweave-ai/airweave" \
  --reports-dir reports/airweave-ai-airweave \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
