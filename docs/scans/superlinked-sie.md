---
layout: default
title: "superlinked/sie: security scan"
description: "Security scan of superlinked/sie, an open-source inference server and production cluster: 156 findings, 1 real. The OAuth bridge derives its issuer and token_endpoint from an unvalidated X-Forwarded-Host, and the project documents that behaviour as a URL-stability concern rather than a security one."
date: 2026-09-14
---

# superlinked/sie — security scan

**Repository:** [superlinked/sie](https://github.com/superlinked/sie) — 3.3k★, Apache-2.0, an open-source inference server and production cluster "for all the models your agent needs." A polyglot monorepo: a Python model server (306 non-test modules, 113k lines), a Rust gateway (180 `.rs` files), a TypeScript SDK, a Helm chart, and an MCP edge that fronts the cluster for claude.ai connectors.
**Commit scanned:** `394df63` (HEAD of `main` at scan time)
**Scan date:** 2026-09-14
**Disclosure status:** One real finding, reported in full in a public issue on the day of the scan. No `SECURITY.md` exists at the repository root, in `.github/`, in `docs/`, or on the published site, and private vulnerability reporting is **disabled** — so no private channel exists to use. Every fact below rests on the project's own committed source and documentation.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 3 |
| High | 83 |
| Medium | 67 |
| Low | 0 |
| Info | 3 (scanner meta) |

**Total findings:** 156 (153 above the `medium` floor) — **1 real after curation**, and **no tool produced it**.

Coverage note first, because it changes how to read every zero below. Semgrep reported 55 errors and **3 rule timeouts** — all three on `packages/sie_gateway/assets/redoc.standalone.js`, a vendored minified API-doc bundle, so no first-party file lost a rule. The rest are Helm templates, which are Go templates and not valid YAML; expected, not a gap. The dependency picture took two passes to read correctly: **pip-audit returned zero, and that zero means nothing** — it resolved the root `pyproject.toml`, which declares `dependencies = []` because, in the project's own words, "the repository root is a development environment, not a distribution." The real dependency trees are elsewhere, and Trivy found them: `uv.lock` (**0 advisories**), `Cargo.lock` (**0**), `packages/sie_server_rust/Cargo.lock` (**0**), `pnpm-lock.yaml` (**0**). The Python and Rust runtime surfaces are genuinely clean. My own `dependency-scan-unaudited-lockfile` meta-finding flagged the pip-audit gap before I noticed it — the third time in a month.

## Why this target

The responsiveness pre-check decided it, and the deciding number was not the biggest one. Sie has only **six open issues** — and **every one carries maintainer comments**. Zero ghosted. Thirty merged PRs from eight distinct authors in 60 days. A report is worth what the project does with it, and this series' fast resolutions have all come from projects that were already answering.

The shape of the product mattered too. An inference server is a network service with a real front door, and this one ships something most targets in the series do not: an **OAuth 2.0 bridge**, hand-written, so that claude.ai custom connectors — which are OAuth-only and cannot take a pasted bearer token — can authenticate against a per-user connector secret. Hand-rolled OAuth is where the interesting mistakes live.

It is, to be clear, unusually careful OAuth. PKCE is required and **S256-only** (`plain` is refused with a comment explaining it would carry the verifier in cleartext). The challenge comparison uses `secrets.compare_digest`. Authorization codes are single-use, TTL-bounded at 120 seconds, and bound to the requesting `client_id`. Redirect URIs are checked against an allowlist by **exact** membership, not prefix. The module docstring claims "Connector secrets, authorization codes, and access tokens are NEVER logged" — read as a [test oracle](hkuds-openopc.html) and checked, the claim holds exactly: `oauth.py` contains **zero** logging calls. And `_validate_authorize_params` is deliberately applied to both the GET and POST paths so "a direct POST cannot skip the invariants the GET handler checks."

Every security property that docstring claims is implemented. The hole is in the one property it does not claim.

## The finding: the OAuth issuer is whatever the caller says it is

The MCP edge resolves its own public origin in `packages/sie_mcp/src/sie_mcp/auth.py:36`:

```python
def base_url(config: MCPConfig, *, scheme: str, headers: Headers) -> str:
    """Resolve the externally reachable origin for OAuth metadata URLs.

    Prefers the pinned ``SIE_MCP_PUBLIC_URL``; otherwise derives it from forwarded
    proxy headers (falling back to the request's own scheme/host).
    """
    if config.public_base_url:
        return config.public_base_url
    proto = headers.get("x-forwarded-proto") or scheme
    host = headers.get("x-forwarded-host") or headers.get("host") or ""
    return f"{proto}://{host}"
```

No allowlist, no validation. Whatever origin this returns is stamped into the two discovery documents the OAuth ecosystem is built on — RFC 8414 authorization-server metadata and RFC 9728 protected-resource metadata:

```python
def authorization_server_metadata(origin: str) -> dict[str, Any]:
    return {
        "issuer": origin,
        "authorization_endpoint": f"{origin}/authorize",
        "token_endpoint": f"{origin}/token",
        "registration_endpoint": f"{origin}/register",
        ...
    }
```

— and into the `WWW-Authenticate` challenge an unauthenticated request to `/mcp` receives (`auth.py:105-111`), which is how a spec-compliant MCP client *discovers* where to authenticate in the first place.

Both `.well-known` routes sit in `_EXEMPT_PATHS`, so they answer before any credential is checked. That is correct — discovery must be reachable unauthenticated — but it means the poisoning input needs no credential either.

### Verified by execution, with a control

Built from the project's real `sie_mcp.oauth` routes and its real `ConnectorSecretAuthMiddleware`, imported verbatim, under the **shipped Helm defaults** (`mcpEdge.publicUrl: ""` → the env var is not rendered into the pod; `mcpEdge.oauthEnabled: true` → the bridge is on):

```
[config] oauth_enabled=True  public_base_url=None

CONTROL (no forwarded headers)
  issuer                 = https://mcp.victim.example
  authorization_endpoint = https://mcp.victim.example/authorize
  token_endpoint         = https://mcp.victim.example/token
  WWW-Authenticate       = Bearer resource_metadata="https://mcp.victim.example/.well-known/oauth-protected-resource"

ATTACK (X-Forwarded-Host: evil.attacker.example)
  issuer                 = https://evil.attacker.example
  authorization_endpoint = https://evil.attacker.example/authorize
  token_endpoint         = https://evil.attacker.example/token
  WWW-Authenticate       = Bearer resource_metadata="https://evil.attacker.example/.well-known/oauth-protected-resource"
```

The control is the point: with the header absent, the code is correct. This is not a misconfiguration — it is a header-driven rewrite of the document that tells OAuth clients where to send users and tokens.

### Why it matters here specifically

On this bridge, the authorize page is where a user **types their connector secret** — the long-lived per-user credential to the SIE cluster. A client that follows poisoned metadata sends its user to `https://evil.attacker.example/authorize`, an attacker-controlled page, to type that secret. The redirect-URI allowlist — correctly implemented, defaulting to claude.ai's callback — cannot help, because the victim never reaches the real server's authorize endpoint at all.

### What stops it, honestly

The shipped chart is better than the code. `mcp-edge-ingress.yaml` marks `mcpEdge.ingress.host` as **`required`**, so the ingress always carries a concrete host rule, and ingress-nginx overwrites `X-Forwarded-Host` with `$best_http_host` by default. **Through the chart's own default ingress, this attack does not land.** That is a real control and it deserves saying plainly.

The exposure is in the paths around it. `sie-mcp serve` — the documented dev entry point, `mise run mcp-serve` — binds **`0.0.0.0:8088`** and runs the app under uvicorn with no proxy at all; there, `Host` and `X-Forwarded-*` are entirely caller-controlled. An ingress-nginx controller configured with `use-forwarded-headers: "true"` (routine when the cluster sits behind an external load balancer) forwards the client's value instead of replacing it. And any cache in front of the `.well-known` routes that does not key on `X-Forwarded-Host` turns one attacker request into a poisoned response served to everyone.

Graded **Medium** for those reasons, not High.

### The part that makes it a finding rather than a footnote

The project already knows the metadata is header-derived. It says so twice in operator documentation — and both times frames the reason to pin the value as **stability**:

> Pin `SIE_MCP_PUBLIC_URL` to the externally reachable origin so the OAuth metadata URLs **are stable** (otherwise they are derived per-request from forwarded host/proto headers).
> — `packages/sie_mcp/plugin/superlinked.md:93`

> This ensures that OAuth metadata contains **stable public URLs**.
> — `packages/sie_mcp/README.md:399`

An operator who reads that, and whose URLs look fine, concludes reasonably that pinning is optional. Nothing tells them the unpinned state is attacker-writable. This is the [contract-versus-artifact](ginlix-ai-langalpha.html) shape with the contract and the artifact agreeing on the *behaviour* and disagreeing on the *risk* — and the reframing, not the discovery, is the deliverable.

### The fix, written before it was proposed

The instinct is to fail closed: require `SIE_MCP_PUBLIC_URL` whenever the OAuth bridge is enabled. **That breaks the project's own dev task.** `tools/mise_tasks/mcp-serve.bash` does not set the variable, so a hard requirement would stop `mise run mcp-serve` — the command the docs tell contributors to run. [Write the remedy before naming it.](roflcoopter-viseron.html)

So the proposal is two smaller pieces that break nothing:

1. **The chart already knows the answer.** `mcpEdge.ingress.host` is required when the ingress is enabled, so `mcp-edge-deployment.yaml` can default `SIE_MCP_PUBLIC_URL` to `https://<that host>` when `publicUrl` is empty. No new setting, and the shipped default stops being the unpinned one.
2. **Bound the fallback.** When nothing is pinned, validate the derived host against an allowlist, or ignore `x-forwarded-*` unless a trusted-proxy flag is set — plus a startup warning that names the consequence. Worth noting that uvicorn's `--forwarded-allow-ips`, the standard operator answer here, is **silently ineffective**: this code reads the raw headers off the ASGI scope itself and never consults uvicorn's proxy-headers handling.

## Patterns observed

**153 tool findings, zero real.** That is less an indictment of the tools than a description of what they can see, and the breakdown is unusually clean:

| Cluster | N | Verdict |
| --- | ---: | --- |
| Trivy CVEs in `bun.lock` | 87 | Already mitigated on the install path the project uses |
| `python-logger-credential-disclosure` | 23 | Vocabulary collision — every hit is an ML *tokenizer* token |
| `run-shell-injection` in workflows | 16 | All `workflow_call`, reachable only with write access |
| `pickles-in-pytorch` | 6 | All six already pass `weights_only=True` |
| `detect-insecure-websocket` | 6 | In-cluster worker registration; scheme-consistent in the SDK |
| `dynamic-urllib-use-detected` | 5 | Build tooling under `tools/`, not a served surface |
| Gitleaks | 4 | An `import` line, two SHA-256 integrity pins, one test fixture |
| `avoid-insecure-deserialization` | 3 | All three are `yaml.dump` — serialization |
| `non-literal-import` | 2 | The adapter registry, by design |
| Dockerfile `:latest` | 1 | Hardening note |

Three of those deserve more than a row.

**The 87 that were already fixed.** Trivy read `bun.lock` and reported 91 advisories including all three Criticals — `protobufjs` code execution, `fast-xml-parser` XSS, `vitest` path traversal. It read `pnpm-lock.yaml`, in the same directory, describing the same workspace, and reported **zero**. Two lockfiles, one repo, wildly different answers. The resolution is not to average them but to ask [which install path each describes](langroid-langroid.html): `package.json` declares `"packageManager": "pnpm@9.15.9"`, every CI job runs `pnpm install --frozen-lockfile`, and that same `package.json` carries a `pnpm.overrides` block pinning **exactly these packages** to patched versions — `protobufjs >=7.5.8`, `postcss >=8.5.10`, `rollup >=4.59.0`, `form-data >=4.0.4`, `vitest ^4.1.0`, `ws >=8.20.1`. The maintainers already fixed this CVE set. `pnpm.overrides` is a pnpm-specific field that **Bun does not honour**, and that single fact is the entire 87-finding delta. The whole scary tier is a lockfile CI never installs from.

**The 23 that were a pun.** `python-logger-credential-disclosure` looks for credentials in log statements. In an inference server, "token" is the domain's core noun. Every hit is `token_dim`, `add_tokens`, `kv_budget_tokens`, `new_tokens` — tokenizer vocabulary, not authentication. Twenty-three consecutive false positives from a lexical match on a word the product is *made of*. A useful reminder that finding count scales with [surface richness, not risk](whiteguo233-openbiliclaw.html).

**The four Gitleaks hits invert.** Two are `MODELING_T5_SHA256` and `T5_TOKENIZATION_SHA256` in `adapters/tensorrt_llm/compat.py` — SHA-256 **integrity pins** the project uses to verify upstream files before patching them. A security control, flagged as a leaked secret. That is the [active-harm pattern](roflcoopter-viseron.html) in its mildest form: acting on the finding would mean deleting a defence.

**The defences a scanner cannot credit** are most of what is good here. The clearest is `packages/sie_sdk/src/sie_sdk/_msgpack.py`, where the project **hand-wrote its own msgpack-numpy object hook** rather than install the library's process-global one, specifically to refuse `kind=O` — which "invokes `pickle.loads` in msgpack-numpy" — and `kind=V`, which "admits attacker-selected structured dtype descriptors." It then validates dtype, dimension count, per-dimension sign, and that `shape × itemsize` equals the actual byte length before calling `np.frombuffer`. That is someone who sat down and thought hard about a deserialization boundary on wire data. Alongside it: all six `torch.load` calls already carry `weights_only=True`, 19 `yaml.safe_load` calls and **not one** unsafe `yaml.load`, and the MCP `authenticate()` fails closed when no secrets are configured unless anonymous access is *explicitly* enabled.

The finding that survived is the one no rule could reach. It is not a dangerous function call; it is a *value flowing from a request header into a document other systems trust*, across two files, guarded by an environment variable whose absence is the shipped default and whose documentation describes the wrong risk. Composite, absence-shaped, and invisible to pattern matching.

## Notes on the tool

- **pip-audit's zero was actively misleading, and the meta-finding caught it.** The root `pyproject.toml` declares `dependencies = []`; the real trees are `uv.lock` plus five per-package manifests. `scan_dependency` is root-only, so on a monorepo "no manifest" renders as "clean." The existing `dependency-scan-unaudited-lockfile` meta-finding fired and named `uv.lock` explicitly — that is the guardrail working, and it is why this write-up says "clean" only after Trivy independently confirmed it. Backlog item stands: `scan_dependency` should walk to sibling manifests rather than rely on a meta-finding to apologise for the root-only read.
- **Two lockfiles for one workspace is a signal the tool should raise on its own.** `bun.lock` and `pnpm-lock.yaml` in the same directory with a 91-to-0 advisory split is exactly the condition that produced this scan's biggest curation step. A check for co-located lockfiles from different package managers — and for whether `package.json` names a `packageManager` — would have surfaced it in the report instead of in my head.
- **Semgrep's timeouts landed only on a vendored bundle**, which is the good case, but the report still counts three rule-timeouts against a file nobody in this project wrote. Distinguishing vendored/minified assets from first-party source in the coverage meta-finding would make the number readable.

## Disclosure timeline

- 2026-09-14 — scan run against `394df63`
- 2026-09-14 — differential built and executed against the project's own OAuth routes
- 2026-09-14 — public issue filed: [superlinked/sie#275](https://github.com/superlinked/sie/issues/275) (no `SECURITY.md` anywhere, private vulnerability reporting disabled — no private channel exists)
- 2026-09-14 — public post (this page)

## Reproduce

```bash
git clone https://github.com/superlinked/sie /tmp/scan-target
.venv/Scripts/python.exe scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/superlinked-sie --min-severity medium --ignore-samples
```
