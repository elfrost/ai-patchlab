---
layout: default
title: "rocketride-org/rocketride-server: security scan"
description: "Security scan of rocketride-org/rocketride-server: 268 findings, 1 real — withheld — an AI pipeline engine (5.5k★, MIT"
date: 2026-07-31
---

# rocketride-org/rocketride-server — security scan

**Repository:** [rocketride-org/rocketride-server](https://github.com/rocketride-org/rocketride-server)
**Commit scanned:** `db6c882e7eb6`
**Scan date:** 2026-07-31
**Disclosure status:** withheld — one real finding held for private disclosure
through the project's `SECURITY.md` channel

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 78 |
| Medium | 189 |
| Low | 0 |
| Info | 0 |

**Total findings:** 268 (1 real after curation — withheld)

RocketRide (5.5k★, MIT, by Aparavi Software AG) calls itself an **AIDE — an AI
Development Environment**. Underneath the branding it is a data-pipeline builder
and runtime for AI workloads: pipelines are portable JSON, composed visually in
VS Code, and executed by a multithreaded **C++ engine**. The node library is the
headline number — **122 nodes** spanning 13 LLM providers, 8 vector databases,
graph stores, OCR, NER, speech, and a `tool_*` family that reaches the
filesystem, git, GitHub, Slack, MCP servers and arbitrary HTTP. It ships a
VS Code extension, Python and TypeScript SDKs, an MCP server, a Docker Compose
stack and a Helm chart.

It is also actively maintained: **40 pull requests merged in the last 60 days
from 13 distinct human authors**, with commits landing the same day the scan ran.

### A note on what this write-up does not contain

The project ships one of the most thorough `SECURITY.md` files this series has
encountered — SLAs by severity, a coordinated-disclosure window, **two-person
delegated alert dismissal** at the organisation level, documented branch
protection, and quarterly access reviews. It opens with:

> 1. **Do NOT** open a public GitHub issue for security vulnerabilities

So this post does what the policy asks. **No public issue was filed, and the one
real finding is described only by class — not by component, mechanism, file, or
reproduction.** Those details are held for the private channel.

There is one wrinkle worth reporting, because it is a *process* observation
rather than a vulnerability. The policy's **preferred** channel is:

> 2. **Preferred**: Use [GitHub Security Advisories](https://github.com/rocketride-org/rocketride-server/security/advisories/new) to report privately through GitHub

That link does not currently work for an outside reporter.
`GET /repos/rocketride-org/rocketride-server/private-vulnerability-reporting`
returns `{"enabled": false}` — private vulnerability reporting is switched off,
so the repository has no "Report a vulnerability" button and the advisory form
is unreachable. The documented fallback (`security@rocketride.ai`) still works,
but the channel the policy tells reporters to prefer is closed. **Enabling
private vulnerability reporting is a single toggle in repository settings**, and
for a project this deliberate about its disclosure process it is almost
certainly an oversight rather than a decision.

Everything else below — the defended surfaces, the false-positive analysis, and
the dependency-coverage gap — is published in full, because that is the part
that is useful to everyone and dangerous to no one.

## Top findings

### 1. Withheld — an authentication boundary that does not fail closed

- **Tool:** none. **No scanner flagged this**, at any severity.
- **Confidence:** high — the control flow was traced end to end, from the HTTP
  entry point through the middleware to the credential comparison, and every
  link confirmed by reading the code rather than inferring it.
- **Why it matters:** the failure is silent. The auth layer is present and
  installed, and an unauthenticated probe still gets a `401` — so the deployment
  *presents* as protected. The gap only appears under a specific and entirely
  ordinary condition, and it is reachable through deployment paths the project
  itself ships.
- **Status:** withheld pending private disclosure.

The shape is one this series has now met three times, and it is worth naming
even without the mechanism: **a security check whose enforcement is conditional
on something the operator, not the attacker, is expected to have configured** —
where the "unconfigured" branch resolves to *allow* rather than *deny*.

That is the [dograh](dograh-hq-dograh.html) fail-open pattern and the
[EvoScientist](evoscientist-evoscientist.html) conditional-verification bypass
seen from a third angle. In EvoScientist the condition was attacker-controlled,
which made it acute. Here the condition is operator-controlled, which makes it
*quieter* — and arguably more dangerous, because nothing in the running system
signals which branch it is on. A deployment in the unsafe state is
indistinguishable, from the outside and from the logs, from one in the safe
state.

The strongest evidence that this is a defect rather than a design choice is
internal: **the function's own docstring documents the opposite behaviour**. It
states that the unconfigured case returns an authentication failure. The code
returns success. Whatever the intent was, the implementation and the contract
disagree, and the contract is the one that is right.

The fix is small — a single condition, changed to match what the docstring
already promises — plus making the shipped deployment paths configure the value
explicitly rather than leaving it absent.

### 2. Python dependencies were analysed by nothing at all

This one is safe to publish in full, because it is a limitation of **my
scanner**, not a vulnerability in RocketRide.

Trivy reported 22 dependency findings, including the scan's only Critical
(`tar` 7.5.16, a gzip-bomb DoS). Their distribution:

| Lockfile | Findings |
| --- | ---: |
| `pnpm-lock.yaml` (npm) | 22 |
| Every Python manifest in the repository | **0** |

That second row is not a clean bill of health. This repository contains:

- **105 per-node `requirements.txt` files** — one for nearly every pipeline
  node, collectively pulling in langchain, CrewAI, LlamaIndex, deepagents, and
  the SDKs for 13 LLM providers and 8 vector databases
- a **1,686-line `constraints.lock`** pinning the resolved set
- further manifests under `packages/ai/` and `tools/`

pip-audit ran, found nothing, and reported `[]`. It was not wrong about what it
looked at — it was looking in one place. AI PatchLab's runner resolves its
target **only at the repository root**, and RocketRide's root `pyproject.toml`
is a **ruff configuration file** with no `[project]` dependencies at all. So the
runner found a `pyproject.toml`, handed it to pip-audit, and pip-audit correctly
reported zero vulnerabilities in zero declared dependencies.

Trivy missed the same tree for a different reason: `constraints.lock` is not a
filename it recognises as a Python lockfile, so it parsed the npm lock and
nothing else.

Two tools, two independent blind spots, one result: **the entire Python
dependency surface of a 122-node AI pipeline runtime went unanalysed, and the
report said so nowhere.** "Zero findings" and "not scanned" rendered
identically — again.

This is the second consecutive scan to hit this exact failure, after
[PipesHub](pipeshub-ai-pipeshub-ai.html), and the missed surface here is far
larger. It moves the fix from "should do" to "must do" on my side.

RocketRide's own dependency hygiene, for the record, is fine: **Renovate is
wired** (`renovate.json`, weekday schedule, grouped non-majors, patch automerge,
majors held for review), and the 22 npm findings are DoS-class issues in the
build toolchain — `tar`, `adm-zip`, `brace-expansion`, `js-yaml`, `postcss`,
`shell-quote`, SheetJS — not in anything the engine serves at runtime.

## What is well built

A 268-finding report containing one real item is usually a sign that the
scanners are finding surface rather than risk. That is the case here, and the
places where a mistake would have been expensive are conspicuously careful.

**The file-download endpoint is a model of the class.** `/task/fetch` serves
files from the local store using short-lived JWTs. It pins the algorithm
explicitly (`algorithms=['HS256']` — no `alg` confusion), it
**requires the `exp` claim** via `options={'require': ['exp']}` so a signed
token without an expiry is rejected rather than treated as eternal, it
distinguishes expired from invalid, and it runs the resolved path through a
traversal guard before serving. Most importantly it **fails closed**: with no
signing key configured it returns a `500` rather than serving anything, and the
issuing side raises rather than minting an unsigned URL. There is even a comment
explaining *why* the path is not re-resolved at fetch time — because
re-resolution under an internal identity would break name-based scopes — which
is the kind of note that tells you the seam was considered rather than missed.

That is worth stating plainly next to finding #1: **this project clearly knows
how to fail closed.** It does it correctly, with reasoning, a few directories
away.

**CORS defaults are restrictive, not permissive.** The class docstring says
"CORS middleware is added to allow unrestricted API access," which reads like a
finding and is not one. The actual default is
`allow_origin_regex=r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$'` — localhost
on any port, to accommodate the dynamic engine port, and nothing else. Setting
`RR_CORS_ORIGINS` narrows it to an explicit allowlist. There is even a
fail-loud branch that warns when the variable is set but parses to zero valid
origins. No wildcard, and no `allow_origins=["*"]` paired with credentials —
the pairing that showed up in [ReMe](agentscope-ai-reme.html),
[Yuxi](xerrors-yuxi.html) and PipesHub. Only the stale docstring needs fixing.

**The CI pipeline has been through real hardening, and it shows.** Actions are
pinned to full commit SHAs, not tags. Workflows declare
`permissions: contents: read` at the top level and raise to `write` only in the
jobs that publish. And the one finding that would normally demand an
outside-the-tree investigation — Semgrep's
`workflow-run-target-code-checkout` on the `Prerelease` workflow — is defended
*in* the tree, twice over: a `branches: [develop]` filter on the trigger **and**
an explicit `github.event.workflow_run.head_branch == 'develop'` guard in the
job's `if:`. The comments name the Scorecard `DangerousWorkflow` rule, explain
that `workflow_run` can be fired by CI on any branch, and spell out why feature
branches are excluded. Several other comments cite the specific CodeQL alert
numbers they close — including a stack-trace-exposure fix in the auth error path
that now sends a generic message to the client and the detail to the debug log.

**The code-execution node is an honest sandbox.** `tool_python` runs
model-supplied code through **RestrictedPython** — `compile_restricted`,
`safe_builtins`, dangerous builtins removed, and imports gated by an allowlist
of pure-computation stdlib modules. Its README states the boundary accurately,
including the part most projects leave out: *"whitelisting extra modules widens
the sandbox accordingly… Only the default allowlist guarantees no filesystem,
network, or subprocess access."* Compare [Agently](agentera-agently.html), where
a component named `PythonSandbox` promised safety a hand-rolled denylist could
not deliver. This is the opposite: a real sandbox library, and documentation
that tells you exactly where its guarantee stops.

**The container is built the way containers should be.** The base image is
pinned by **digest**, a dedicated non-root user is created and used, and the
healthcheck targets the deliberately public `/version` rather than weakening an
authenticated route to make the probe pass — with the reasoning, and the issue
number, in a comment.

**The public-values discipline is explicit and correct.** `.config` is committed
and carries a header stating that only public values belong in it. Gitleaks
flags the Stripe key inside it; the key is a `pk_test_` **publishable** key,
which is a public client-side identifier by design, and the file says so before
the scanner ever gets there.

## The false positives

**267 of 268 findings are noise.** The breakdown is unusually clean.

**135 path-traversal mediums — the single largest cluster — are all in build and
documentation tooling.** Forty in `scripts/lib/`, thirty-six in
`packages/docs/`, plus `nodes/scripts/`, `deps-tasks.js` and `licenses.js`.
These are Node scripts that join paths at build time from values the build
itself supplies. The remainder sit in the VS Code extension host, where the
"attacker" is the developer who opened the folder.

**All 17 gitleaks secrets are false, in four distinct flavours:**

- Three `curl-auth-header` hits in `task_data.py` are inside a **docstring**,
  in `curl` usage examples whose value is literally
  `-H "Authorization: Bearer your-api-key"`.
- Two hits in `engine-core/test/crypto/` are **C++ unit-test key vectors** —
  fixed inputs for testing a crypto primitive.
- The `remote.json` hits are `%remote-apikey%`-style **template placeholders**.
- Nine `pipe-file-api-key` hits across `packages/server/test/pipelines/*.json`
  are an identical copy-pasted **test-fixture token** for a local `filesys`
  source, at the same line number in every file.

The interesting detail: `pipe-file-api-key` is **RocketRide's own custom
gitleaks rule**, written to catch hardcoded keys in `.pipe` pipeline files. The
repository ships a `.gitleaks.toml` that defines it, along with allowlist
regexes for `$VAR` / `${VAR}` placeholders and a global allowlist for lockfiles
and build output. Gitleaks picked the config up from the scanned tree, so the
project's own rule fired on the project's own test fixtures. That is a **sixth
vote** for the suppression tier this series keeps re-deriving — after IBM's
`.secrets.baseline`, AG2's `# pragma: allowlist secret`, Kiln, N.E.K.O's i18n
catalogues and PipesHub's generated API specs. A repository that ships a
gitleaks config has already told you what it considers a secret; a scanner that
ignores the accompanying allowlists is arguing with its own input.

**11 SQLAlchemy raw-query highs are the [#1 identifier
FP](mnemosyne-oss-mnemosyne.html)**, in `store_postgres/postgres.py`. The
pattern is `SQL_QUERIES['...'].format(collection=self.collection)` — the
**collection name** is interpolated as an identifier while every data value is
bound (`%s` parameters, passed as a list; the keyword search builds
`[f'%{query}%'] + params` and passes it separately). Search text, filter values
and `LIMIT` are all parameters. The identifier comes from node configuration,
not from request data. Worth noting that there is no explicit identifier
validator or quoting helper — `psycopg.sql.Identifier` would express the intent
better than `str.format` — but no value crosses into the query text.

**15 insecure-websocket highs are documentation and a log message.** Most are
`ws://` occurrences in `.md` files. The two in real Python are a
**format string used for logging the connected client's address**
(`f'ws://{websocket.client.host}:{websocket.client.port}'` — a label, not a
connection) and the client's URI-normalisation helper, which parses whatever
scheme the caller supplied rather than downgrading anything.

**Cleared for context rather than content:** 10 `secrets-inherit` highs are
`secrets: inherit` on calls to **reusable workflows in the same repository**;
3 `run-shell-injection` highs interpolate a **matrix value** the workflow itself
defines, and pass every `workflow_call` input through `env:` and quoted shell
variables — the correct pattern; 2 `eval-detected` are in `tools/contract_checks`,
a developer-only contract linter; the 1 `exec-detected` **is the RestrictedPython
sandbox** executing its own compiled-restricted bytecode; 12 `non-literal-import`
mediums are the plugin loader that loads the 122 nodes by name — which is how a
plugin system works; and 6 `wildcard-postmessage` mediums are VS Code webview
messaging, where both ends are extension-controlled.

## Notes on the tool

- **pip-audit's root-only target discovery is now the highest-value fix on the
  backlog.** Two consecutive scans, two complete misses, and this one missed
  105 manifests and a 1,686-line lockfile. It must walk for
  `requirements*.txt` / `pyproject.toml` below the root, bounded and skipping
  vendored trees, rather than checking the root and stopping.
- **A root `pyproject.toml` can be a decoy.** RocketRide's is pure ruff
  configuration with no `[project]` table. The runner treated "a `pyproject.toml`
  exists" as "the Python project was found." Presence of the file is not
  presence of dependencies — the runner should check for a dependency table and
  keep looking if there isn't one.
- **Unrecognised lockfile names need a coverage warning.** `constraints.lock`
  is a perfectly ordinary pip constraints file and neither tool claimed it.
  Same family as the [0-byte Semgrep report](dataelement-clawith.html) check:
  the report must be able to say *"this tree was not analysed."*
- **Honour a repository's own `.gitleaks.toml` allowlists** (sixth vote). The
  irony here is sharp — the finding count was inflated by the project's own
  detection rule firing on the fixtures its own allowlist logic exists to
  manage.
- **Check the disclosure channel before assuming it works.** This scan's plan
  was to use the project's stated *preferred* private channel, which turned out
  to be disabled. Verifying `private-vulnerability-reporting` (and that a
  `SECURITY.md` email is reachable) belongs in the pre-check, next to the
  strict-norm probe — otherwise "post-only, report privately" quietly becomes
  "post-only."
- **Grade a docstring against its code.** Finding #1 was confirmed, not merely
  suspected, because the function's documented contract contradicted its
  implementation. When a security function's docstring enumerates its failure
  modes, that list is a free test oracle — and a mismatch is a much stronger
  signal than a pattern match.

## Disclosure timeline

- 2026-07-31 — scan run
- 2026-07-31 — public post (this page), with the real finding withheld
- pending — private report to `security@rocketride.ai` per the project's
  `SECURITY.md`; full detail to be published here once fixed, or after the
  90-day window the policy describes

## Reproduce

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/rocketride-org/rocketride-server /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/rocketride-org-rocketride-server --min-severity medium
```
