---
layout: default
title: "Datus-ai/Datus-agent: security scan"
date: 2026-09-10
---

# Datus-ai/Datus-agent — security scan

**Repository:** [Datus-ai/Datus-agent](https://github.com/Datus-ai/Datus-agent)
**Commit scanned:** `c954fa47660812aedd5536369218b99bcb9dc585`
**Scan date:** 2026-09-10
**Disclosure status:** public — one focused issue filed upstream

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 3 |
| High | 118 |
| Medium | 167 |
| Low | 0 |
| Info | 3 |

**Total findings:** 291 (1 real after curation — and the tools did not find it)

Datus-agent is a natural-language-to-SQL data-analysis agent (1.7k★, Apache-2.0,
commercial backing — "Copyright 2025-present DatusAI, Inc." on every source
file). It ships a FastAPI server (`datus-api`, `python -m datus.api.main`) that
binds `0.0.0.0:8000` by default, and the agent it drives executes SQL against
configured datasources and runs a bwrap/Seatbelt-sandboxed bash tool. It is, on
the whole, a **carefully engineered codebase** — which is exactly why the one
real finding is the part that was left behind.

## The one real finding: the documented auth is protected by a key the repo publishes

The project has **two auth systems in one app**, and the finding lives in the
older of the two.

The **new** system (`datus/api/auth/`, wired through `datus/api/deps.py`) is a
clean, pluggable `AuthProvider` protocol. Its default `HeaderContextProvider`
reads a caller-supplied `X-Datus-User-Id` and forwards an `X-Datus-Policy-Context`
JSON blob to the policy engine, and its own docstrings say so plainly:
*"Authentication and authorization happen before this boundary."* That is a
**downward boundary** — the design expects a deployment to front the service
with its own auth provider or gateway — so the header-trusting default is
by-design, not a defect.

The **legacy** system is different, because it actively *claims* to authenticate.
`datus/api/service.py` registers three decorator routes on top of the plugin
routers:

- `POST /auth/token` (`service.py:536`) — OAuth2 client-credentials → JWT
- `POST /workflows/run` (`service.py:552`) — `Depends(get_current_client)`
- `POST /workflows/feedback` (`service.py:588`) — `Depends(get_current_client)`

`get_current_client` calls `AuthService.validate_token`, which does a real
`jwt.decode` against a signing secret (`legacy_auth.py:103`). This surface is
the one the API docs (`docs/workflow/api.md`) present as *the* way to
authenticate. The problem is where the secret and the client list come from
when the operator has not created a config file:

```python
# datus/api/legacy_auth.py
DEFAULT_CLIENTS = {"datus_client": "datus_secret_key"}                     # :20
DEFAULT_JWT_CONFIG = {"secret_key": "your-secret-key-change-in-production", # :23
                      "algorithm": "HS256", "expiration_hours": 2}

def load_auth_config(config_path=None):
    ...
    if yaml_path.exists():
        ... return config
    # Return default configuration if no config file found                 # :61-62
    return {"clients": DEFAULT_CLIENTS, "jwt": DEFAULT_JWT_CONFIG}

self.jwt_secret = os.getenv("JWT_SECRET_KEY", jwt_config.get("secret_key")) # :75
```

The live config lives at `~/.datus/conf/auth_clients.yml`
(`path_manager.auth_config_path`). Only `conf/auth_clients.yml.example` is
committed — the real file must be hand-created. **Its absence is the default
state of a fresh install, and absence silently selects the hardcoded values.**
There is no startup warning, no refusal to boot, no log line — `load_auth_config`
just returns the defaults.

That gives an attacker who can reach the port **two** ways in, and the second
needs no credential at all:

1. Authenticate at `/auth/token` with the published `datus_client` /
   `datus_secret_key`.
2. Skip the endpoint entirely and **forge** a JWT signed with the constant
   `"your-secret-key-change-in-production"` (published in the public source).
   The project's own `validate_token` accepts it.

Either token then satisfies `get_current_client` on `/workflows/run`, which runs
`service.run_workflow` → `Agent` → a SQL task against the configured datasource.

### Verified with a differential, negative control included

The repro imports the project's **own** `legacy_auth` module verbatim (its
constants, its `jwt.decode` path), points the config loader at a nonexistent
path to reproduce a fresh install, and checks a wrong-key token is rejected so
the test proves the check actually runs:

```
Config file the loader looks for : .../__nonexistent__/auth_clients.yml
Exists?                          : False
clients on a fresh install       : {'datus_client': 'datus_secret_key'}
JWT secret on a fresh install    : 'your-secret-key-change-in-production'
------------------------------------------------------------------------
(A) /auth/token datus_client/datus_secret_key -> ACCEPTED
(B) forged token via published secret accepted -> {'client_id': 'attacker', ...}
Control: wrong-key token REJECTED -> HTTPException
```

A hardcoded signing key is CWE-321 (Use of Hard-coded Cryptographic Key): the
key's secrecy *is* the security property, and here it is committed to a public
repo, so the "change in production" advice in the docs and the `.example` file
does not help against anyone who reads the source. The fix is not "document it
harder" — it is to **fail closed**: refuse to serve the legacy JWT routes (or
generate a random per-process secret and log a loud warning) whenever the
resolved secret is still the shipped default and neither `JWT_SECRET_KEY` nor
`auth_clients.yml` overrides it. That mirrors the project's own bash-sandbox
philosophy, which already refuses to run when its protection is unavailable.

## Patterns observed

**The tools produced 291 findings and none of them was this one.** The reason is
the shape: a hardcoded credential that *looks* like a placeholder. Gitleaks does
not flag `"your-secret-key-change-in-production"` because it reads as a comment
to a human and as low-entropy noise to a secret scanner; the actual defect is
that a *fallback constant is trusted when a file is missing*, which no SAST rule
models. This is the recurring lesson of the series — the real finding is an
**absence**, and you find it by reading the auth seam, not by ranking the
scanner's output.

**What the maintainers do well is most of the security surface.** The new
`AuthProvider`/`AppContext` layer is a genuine redesign with a documented trust
boundary and a deliberate anti-footgun (`deps.get_scoped_sub_agent` rejects an
unknown sub-agent name with 400 rather than building an unscoped service — its
docstring explains that a name that resolves to nothing "has no scope filter at
all"). CORS is handled correctly: `allow_credentials=cors_origins != ["*"]`
disables credentials exactly when the origin is the wildcard, which is the gate
this series has had to *ask five other projects to add*. The bash tool fails
closed — with the sandbox on and no bwrap/Seatbelt mechanism available, "the
command was NOT executed." DuckDB runs with `SET enable_external_access=false`.
The legacy path is the outlier, not the norm.

**The scary tiers are all noise once you apply the standard gates.** The three
`Critical` LiteLLM CVEs (OIDC cache-key collision, `/prompts/test` SSTI, Host-
header auth bypass) are all **LiteLLM *Proxy*-only**; Datus uses litellm as a
client library (`datus/models/litellm_adapter.py`) and never runs the proxy, so
none is reachable — a version-match → reachable → mitigated call, and it fails at
"reachable." The 79 raw/formatted-SQL hits (High + Medium) are the **engine
layer** of a NL→SQL tool — the DuckDB and SQLite connectors whose *job* is
executing SQL — interpolating identifiers and config values, not end-user
values, with the real guard being the statement-level policy/auto-review layer
the README advertises; that is the parameterized-SQL identifier false positive,
now on its **eleventh** appearance. The 53 mutable-action-ref and 4 shell-
injection hits are CI hardening. Every Gitleaks hit is a `curl -H "Authorization:
Bearer your_jwt_token"` line in the docs, a value in `sample_data/`, or a test
fixture.

## Notes on the tool

- **The finding is invisible to every scanner in the stack**, and that is the
  point worth carrying: a hardcoded *default* that activates on a missing file
  is neither a high-entropy secret (Gitleaks) nor a taint path (Semgrep) nor a
  CVE (Trivy/pip-audit). A future check that reads "config loader returns a
  hardcoded fallback that is then used as a signing key / credential" would have
  caught it, but that is a semantic rule, not a pattern match.
- The 3 LiteLLM criticals re-confirm the **SCA reachability gap**: Trivy reports
  the lockfile CVEs with no notion that they are Proxy-server-only against a
  client-library import. The "affected surface + reachable here?" columns remain
  a backlog item.
- The SQL identifier cluster (79 here) is the single most repeated false-positive
  family in the series. A curation aid that collapses "f-string interpolates an
  identifier/validated column, binds every value" would remove a large, recurring
  chunk of manual review.

## Disclosure

Datus-agent has **no `SECURITY.md`** (root, `.github/`, or the docs site — all
404), **private vulnerability reporting is disabled**, and the org publishes no
security email. There is no signalled private channel. Because the vulnerable
value is *already committed to the public repository*, a public issue discloses
nothing that is not already public; it adds only the reachability analysis and a
fix. One focused, single-issue report was filed upstream (no grouped "review"
issue, per this series' handling of commercial-backed targets), leading with the
code path and the concrete fail-closed fix, and offering a PR.

## Disclosure timeline

- 2026-09-10 — scan run, finding verified with a differential repro
- 2026-09-10 — focused public issue filed: [Datus-ai/Datus-agent#1415](https://github.com/Datus-ai/Datus-agent/issues/1415)

## Reproduce

```bash
git clone https://github.com/Datus-ai/Datus-agent /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/datus-ai-datus-agent --min-severity medium
```
