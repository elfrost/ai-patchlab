---
layout: default
title: "TracecatHQ/tracecat: security scan"
date: 2026-08-15
---

# TracecatHQ/tracecat — security scan

**Repository:** [TracecatHQ/tracecat](https://github.com/TracecatHQ/tracecat)
**Commit scanned:** `504a26ab7745`
**Scan date:** 2026-08-15
**Disclosure status:** post-only — nothing filed upstream (strict-norm target, zero findings survived curation)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 4 |
| High | 109 |
| Medium | 99 |
| Low | 0 |
| Info | 0 |

**Total findings:** 212 above the `medium` floor — **zero real after curation**

Twenty-eighth clean scan in this series, and the first target that is itself a
**security automation platform**: an open-source SOAR (3.8k★, AGPL-3.0, two
years old, 66 merged PRs from 8 distinct authors in 60 days) where analysts
build low-code response workflows on a Temporal engine, with a credential
vault, workspace tenancy, SAML SSO, an MCP server, an agent runtime, and an
`nsjail` sandbox for untrusted code execution.

## The document was the method

This project's `SECURITY.md` is not a disclosure policy with a mailbox in it.
It is a **scoping document**, and two of its sentences are checkable claims:

> `nsjail` is enabled by default for Helm chart / Kubernetes deployments only
> and must be explicitly enabled in other deployment options.

> We do not accept reports related to "breakout" in the `pid` runtime using
> the `UnsafePidExecutor`.

The second one is the more unusual. A project declaring *its own weakest
configuration out of scope* is the honest inverse of the
[Agently](agentera-agently.html) shape — there, a component **named**
`PythonSandbox` and documented as running code "safely" was escapable, and the
advertised boundary was the whole defect. Here the boundary is advertised
*downward*: this mode is not a sandbox, do not report it as one.

That only holds up if the artifacts agree, so I checked the first claim against
every deployment description in the tree. **All four agree**, which is the first
unanimous result the [contract-versus-artifact](vexa-ai-vexa.html) test has
returned:

- `docker-compose.yml`, `.dev.yml`, `.local.yml` — `TRACECAT__DISABLE_NSJAIL:
  ${TRACECAT__DISABLE_NSJAIL:-true}`, and a separate opt-in overlay
  (`docker-compose.sandbox.yml`) that flips it to `false` and adds the required
  privileges.
- `deployments/fargate/modules/ecs/locals.tf` — `TRACECAT__DISABLE_NSJAIL = "true"`
  at both task definitions.
- `deployments/fargate/README.md` — states *why*, unprompted: "Fargate does not
  support the permissions model required by `nsjail` … Tracecat uses
  `unsafe_pid_executor` fallback … If you need highest isolation for untrusted
  code execution, deploy Tracecat on Kubernetes with the Helm chart."
- `docs/self-hosting/security.mdx` — a per-deployment isolation table whose
  Docker Compose row reads, in full, "No isolation."

This is the check that produced filings against
[AudioMuse-AI](neptunehub-audiomuse-ai.html) (three deployment descriptions,
two keeping the database internal and the compose files publishing it) and
[Vexa](vexa-ai-vexa.html) (a typed `required-explicit` contract its artifacts
contradicted). Running it here and getting a **no** is the result worth
publishing: the same probe, applied honestly, has to be able to come out in the
project's favour.

## What I went looking for instead

With the sandbox lane closed by its own documentation, the remaining question
was the [boring plumbing beside the impressive machine](evoscientist-evoscientist.html).
I enumerated all **511 HTTP routes** with an AST pass over `tracecat/`, checking
each handler signature for a role dependency. Auth here is per-route
(`Annotated[Role, Depends(...)]`), not mounted structurally at include time the
way [semantica](semantica-agi-semantica.html) does it — which means it is
*forgettable by omission*, and "which route forgot" is the right question.

The genuinely unauthenticated set is small, and every member of it is
unauthenticated for a reason: health and info probes, SAML login, auth-method
discovery, the OIDC endpoints, the workflow webhook receiver, and the invitation
acceptance page. I read each one.

**Every lane closed, and several closed on the exact defense a previous target
lacked:**

- **The credential-bearing git URL.** Registry sync clones a repository, which
  is the [Observal](observal-observal.html) shape — the strongest thing this
  series has filed privately, where a clone token was embedded into any
  user-supplied host with no allowlist. Tracecat's `parse_git_url` takes an
  `allowed_domains` set, and the caller defaults it to `{"github.com"}` from an
  organization setting. That is precisely the missing control, present.
- **The SSRF guard.** `tracecat/network.py` resolves the hostname and rejects
  anything not `is_global`, with a comment explaining that `is_global` catches
  ranges the explicit flags miss. For a SOAR, outbound HTTP to arbitrary hosts
  *is* the product, so the interesting question is which callers are
  caller-influenced but **not** product surface — the audit-log webhook and
  OAuth provider URLs. Both are the two call sites the guard has.
- **The channel webhook.** `POST /agent/channels/{channel_type}/{token}` drives
  an agent from a Slack event, which is the [EvoScientist](evoscientist-evoscientist.html)
  bug's exact habitat. It verifies-then-branches: the token's own HMAC first,
  then `_verify_slack_signature` — required headers, a timestamp replay window,
  HMAC-SHA256 over `v0:ts:body`, `hmac.compare_digest`. Unknown channel types
  raise rather than fall through. The `url_verification` path relaxes the
  *token-active* check but still requires a valid signature, so the branch that
  looked like the bypass isn't one.
- **The home-grown OIDC server.** One permitted `client_id`, `redirect_uri`
  compared by **exact match** after default-port normalisation (not prefix),
  `code_challenge_method=S256` mandatory, `offline_access` stripped, and resume
  transactions bound to a hashed client IP with an expiry.
- **Invitation acceptance** — the classic tenancy-escalation route, since it
  runs before any organization context exists and therefore on an RLS-bypass
  session. It re-fetches the user, compares emails case-insensitively, checks
  expiry, and flips status with an atomic conditional `UPDATE` whose comment
  names the TOCTOU race it closes.
- **Attachments** validate extension, MIME type **and magic number** against
  workspace settings, and the executor-facing internal router carries
  `ExecutorWorkspaceRole` plus `@require_scope` on all seven routes — no odd one
  out.
- **Secret masking** is applied to action results, action errors, sandbox
  stderr, and stored execution output.

### Row-level security, and the honest half-built thing

Workspace tenancy is backed by Postgres RLS, and the implementation detail that
usually breaks it is right: context is set with `set_config(..., true)` —
transaction-local, so it cannot leak to the next request across a pooled
connection. The code comment says "connection pool safe" and it is.

`TRACECAT__RLS_MODE` nonetheless **defaults to `off`**, with `shadow` and
`enforce` above it, and two call sites gate on `== ENFORCE`. That pattern —
a security control conditional on a mode that isn't the default — is the shape
I filed against [tokenspeed](lightseekorg-tokenspeed.html) (a flag documented as
a control, never read) and [EvoScientist](evoscientist-evoscientist.html)
(verification behind a caller-controlled condition). It isn't that here, for two
reasons I had to read the code to establish: the migration that adds the
policies says so out loud — "Phase 1 relies on application-controlled rollout
via `TRACECAT__RLS_MODE`" — and, more decisively, the non-enforcing branch does
not silently do nothing. It sets an **explicit** bypass context. RLS is
defense-in-depth being rolled out underneath an application-layer control that
is already there, not a control that quietly evaporates. Half-built and
labelled beats finished and assumed.

## The one thing worth watching

`POST /organization/vcs/github/webhook` takes `payload: dict[str, Any]`, has no
role dependency, no signature verification, and is reachable unauthenticated —
`org_router` carries no router-level dependencies. It is **not a vulnerability
today**, because the handler reads two fields, writes two log lines, and
returns; it changes no state. The body of it is a `TODO: Process other webhook
events`.

I am recording it rather than filing it because the interesting property is
*where the TODO is*. The handler is exactly where GitHub App webhook signature
verification (`X-Hub-Signature-256` against the app's webhook secret) belongs,
and the endpoint currently reads as finished — it returns
`"Webhook processed successfully"` to anyone. A comment already notes that
installation events aren't correlated to workspaces "reliably", so the next
person to make them reliable is the one who needs the check. That is a note for
a maintainer, not a report, and it is in this post rather than an issue because
nothing about it is exploitable at this commit.

## Patterns observed

**A security company's own product is a fair test of whether this method finds
anything, or only finds sloppiness.** The honest answer this time is the latter:
every probe that has produced a real filing in this series ran here and came
back clean, and several came back clean *specifically* at the point where an
earlier target failed. That is a more useful result than a marginal finding
would have been, because it makes the negative legible — the git-clone
allowlist, the verify-then-branch webhook, the exact-match `redirect_uri`, the
transaction-local RLS context are all the named defense from a named prior scan.

**Scoping documents are underrated as security artifacts.** The pattern this
project shares with [jcodemunch](jgravelle-jcodemunch-mcp.html) — the other
target whose `SECURITY.md` was a controls specification rather than a mailbox —
is that a document detailed enough to be *wrong* is the fastest way to audit
something. It generated the nsjail check and it killed the sandbox lead in the
same paragraph. The difference is that jcodemunch's document drifted from its
tree in two places and this one didn't.

**Severity and surface are still uncorrelated.** 212 findings on a codebase
where nothing was wrong, against [EvoScientist](evoscientist-evoscientist.html)'s
39 findings where one thing was — and there, as here, no tool ranked the item
that mattered. The count tracks how much a project *does* (Terraform, four
compose files, a frontend, migrations, an agent runtime), not how exposed it is.

## Notes on the tool

**Semgrep silently skipped two first-party source files — and this is the
sharpest version of a gap this series keeps recording.** The raw output is a
healthy 896 KB with 180 results across 3,093 scanned files, zero skipped. It
also carries **37 errors**, and two of them are `Other syntax error … 
Common.Impossible` on `tracecat/agent/stream/connector.py` (470 lines) and
`tracecat/registry/actions/service.py` (1,711 lines — a core service). I
compiled both with CPython 3.13: **they are valid Python**. `Common.Impossible`
is an internal parser crash, not bad syntax, and 72 other files in the tree use
the same `match` construct without issue. So **2,181 lines of first-party
application code had zero rules run against them**, and the report renders that
identically to "we analysed it and it was clean." Fifteenth vote for a **per-tool
coverage row**, and the first where the un-analysed code is core application
logic rather than a workflow file or a Dockerfile.

**pip-audit and Trivy disagreed about the same file, and pip-audit's answer was
`[]`.** Trivy parsed the root `uv.lock` and returned 9 vulnerabilities
(`aiohttp`, `cryptography`, `pydantic-ai-slim`). pip-audit, pointed at the same
repository, produced an empty array. One lockfile, two tools, opposite answers —
and in the report an empty pip-audit result is indistinguishable from a genuine
clean bill. This is the [loopx](huangruiteng-loopx.html) ambiguity again
(`{"dependencies": []}` was a *true* zero there) except resolved the other way,
and it is only detectable because a second tool covered the same target. Same
backlog item: **0-of-0, 0-of-N and "did not run" must not render alike.**

**The false positives were the usual roster, and cheap to dismiss:**

- **121 of 128 SQL findings** are `alembic/versions/**` migration DDL plus a
  benchmark package — the [#1 identifier FP](mnemosyne-oss-mnemosyne.html) in its
  **ninth** appearance, and the `alembic/versions/**` candidate-FP tier from
  [codex-lb](soju06-codex-lb.html) doing exactly what it was meant to. Seven land
  in first-party runtime code, one of them inside the RLS machinery itself.
- **Both `tarfile-extractall-traversal` highs pass `filter="data"`** — the safe
  extraction filter, already correct, same credit as
  [harbor](harbor-framework-harbor.html). Notable because archive extraction has
  been a *real* finding three times in this series
  ([pixeltable](pixeltable-pixeltable.html),
  [fast-agent](evalstate-fast-agent.html),
  [jcodemunch](jgravelle-jcodemunch-mcp.html)).
- **Both `run-shell-injection` highs** are in a workflow triggered only by
  `push` to protected branches, `schedule`, and `workflow_dispatch` — the
  interpolated value is `inputs.tag`, which requires repo write access, and the
  job additionally gates `workflow_dispatch` on the actor. [Trigger context
  decides this rule](maziyarpanahi-openmed.html); hardening, not a vulnerability.
- **All 4 criticals are unrestricted *egress*** (`0.0.0.0/0`, protocol `-1`) on
  Fargate security groups. For the `core` and `caddy` groups this is the product
  working — a SOAR exists to call arbitrary third-party APIs. The two worth a
  tidy-up are `core_db` and `temporal_db`, database groups that don't need to
  reach the internet. Calling any of them *Critical* is severity inflation on an
  egress rule, and it is the [whose-running-system](observal-observal.html) tier
  besides: reference Terraform an adopter forks.
- **gitleaks returned a true `[]`.** The repo ships its own `.gitleaks.toml`,
  which my runner does not honour — and the scan found nothing anyway, so for
  once the [honour-the-shipped-config](ibm-mcp-context-forge.html) backlog item
  (now seven votes) didn't change the answer.

**Dependency tail, for completeness rather than as a finding:** `cryptography`
48.0.1 and `aiohttp` 3.14.1 in `uv.lock` carry advisories, and
`pydantic-ai-slim` 1.62.0 has two cloud-metadata blocklist bypasses that are
interesting in principle for an agent that fetches URLs — but one requires an
opt-in that disables the private-IP block, and this project routes its own
caller-influenced fetches through `tracecat/network.py` rather than that path.
No Dependabot config is present in `.github/`; the maintainers run a bounty
programme and a 24-hour review SLA, so a "wire up Dependabot" issue would be
[the wrong thing to manufacture](kiln-ai-kiln.html).

## Disclosure

**Nothing was filed.** The quality gate was not met — no finding survived
curation — so there was no report to make. This is also a strict-norm target
independently: `SECURITY.md` nominates GitHub private security advisories as the
channel, private vulnerability reporting is **enabled** (so the pipeline *could*
have filed autonomously, as it has six times now), a security team reviews
within 24 hours, bounties are offered, and the policy asks reporters to come to
them before disclosing publicly. Had anything been real, it would have gone
there and this page would have withheld it.

## Disclosure timeline

- 2026-08-15 — scan run at `504a26ab7745`
- 2026-08-15 — curation: 212 findings above the medium floor, zero real
- 2026-08-15 — public post (this page); nothing filed upstream

## Reproduce

```bash
git clone https://github.com/TracecatHQ/tracecat /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/tracecathq-tracecat --min-severity medium
```

The route enumeration referenced above is an AST pass over `tracecat/`
collecting every `@router.<method>` decorator and its handler signature, then
filtering for signatures with no role dependency — 511 routes, 76 to read by
hand once the differently-named role types are accounted for.
