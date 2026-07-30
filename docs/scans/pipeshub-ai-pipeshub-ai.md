---
layout: default
title: "pipeshub-ai/pipeshub-ai: security scan"
date: 2026-07-30
---

# pipeshub-ai/pipeshub-ai — security scan

**Repository:** [pipeshub-ai/pipeshub-ai](https://github.com/pipeshub-ai/pipeshub-ai)
**Commit scanned:** `8d1f267aabc7`
**Scan date:** 2026-07-30
**Disclosure status:** partially withheld — two real findings held for private
disclosure through the project's `SECURITY.md` channel

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 159 |
| Medium | 228 |
| Low | 0 |
| Info | 0 |

**Total findings:** 389 (2 real after curation — both withheld)

PipesHub (3.1k★, Apache-2.0) is an **enterprise "context layer"**: it connects
to a company's business systems — Google Drive, Gmail, SharePoint, Confluence,
Jira, Slack, GitLab, S3, Azure Blob, Dropbox, Linear, ClickUp and more — indexes
what it finds, and serves it back through explainable enterprise search and an
agent runtime. It is a Python backend (2,219 files), a TypeScript/Express
backend, a React front end, and an Electron desktop sync client, deployed as one
Docker Compose stack.

It is also the most actively maintained project this series has scanned:
**60 pull requests merged in the last 60 days from 13 distinct human authors**,
with merges landing the same day the scan ran.

### A note on what this write-up does not contain

The project ships a real `SECURITY.md` that says, unambiguously:

> **Please DO NOT create public GitHub issues for security vulnerabilities.**
> Instead, please report security vulnerabilities by emailing
> `abhishek@pipeshub.com`.

It commits to a 48-hour acknowledgement and a 30-day fix target for critical
issues. That is a real disclosure programme, and this scan found two items that
belong in it. So this post does what the policy asks: **no public issue was
filed, and the two real findings are described only by class, not by mechanism.**
The reproduction detail, the exact call path, and the payload shape are held
until the maintainers have had their window.

Everything else below — the defended surfaces, the false-positive analysis, and
the tooling lessons — is published in full, because that is the part that is
useful to everyone and dangerous to no one.

## Top findings

### 1. Withheld — unvalidated destination in an agent tool

- **Tool:** semgrep ranked the underlying line only as a **medium**
- **Confidence:** high — verified by reproducing the enabling primitive locally
- **Why it matters:** the tool is reachable in the **default agent role**, and
  the boundary it crosses is one the project otherwise enforces carefully
  everywhere else.
- **Status:** withheld pending private disclosure.

The shape is worth describing even without the mechanism, because it is a
recurring one: a project builds a careful boundary, and then a *sibling* utility
that nobody classified as a boundary-crossing tool quietly provides the same
capability without the checks. PipesHub confines the agent's file tools to a
`WorkspaceBackend` and its code execution to a network-isolated container — both
deliberate, both well built. The finding is a third path that reaches past both.

This is the [Agently](agentera-agently.html) "advertised boundary" lesson viewed
from a different angle. There, a component *named* `PythonSandbox` failed to
enforce what its name promised. Here the sandbox enforces its promise
exactly — and the gap is somewhere the sandbox was never asked to cover.

### 2. Withheld — reachable critical in a pinned core dependency

- **Tool:** trivy (found via the *wrong* lockfile — see below)
- **Confidence:** high
- **Why it matters:** it survives all three curation gates this series applies to
  dependency findings — **version-match → reachable → mitigated?** — which is
  rare. Most dependency criticals die at gate two.
- **Recommendation:** a one-line version bump. The upstream fix is published.
- **Status:** withheld pending private disclosure.

The reachability argument is the interesting part. This series has spent a year
learning to *collapse* dependency findings: LiteLLM CVEs that are Proxy-only
([Q00/ouroboros](q00-ouroboros.html)), langchain criticals whose only import
sites are `test_*.py` ([Kiln](kiln-ai-kiln.html)), a chromadb pre-auth RCE
against an embedded in-process client ([dimos](dimensionalos-dimos.html)),
`authlib` reached through a code path that is never touched
([N.E.K.O](project-n-e-k-o-n-e-k-o.html)). The reflex is to assume a dependency
critical is noise until proven otherwise.

That reflex is right often enough to be a rule, and wrong often enough to be
dangerous. This one is reachable, and the threat model in the upstream advisory
maps precisely onto a configuration surface the product exposes to its users.

### 3. Dependency scanning covers the test harness, not the product

This one is safe to publish in full, because it is a structural observation
rather than a vulnerability.

Trivy reported **89 dependency findings**. Their distribution:

| Lockfile | Findings |
| --- | ---: |
| `integration-tests/uv.lock` | 49 |
| `backend/nodejs/apps/package-lock.json` | 25 |
| `frontend/package-lock.json` | 7 |
| Dockerfiles | 8 |
| **`backend/python/` (the shipped product)** | **0** |

That last row is not a clean bill of health — it is a **blind spot**.
`backend/python/` declares its dependencies in `pyproject.toml` with **no
lockfile at all**. There is a `package-lock.json` in that directory, but it locks
*npm* packages, not Python ones. So the ~69 pinned Python dependencies that make
up the actual shipped backend were resolved by **no scanner in this run**:
Trivy had nothing to parse, and pip-audit produced no output either.

The 49 findings against `integration-tests/uv.lock` are real, but that file
locks the **test harness**. Finding #2 above was surfaced only because the
vulnerable package happens to appear in *both* — the test lockfile is where the
scanner saw it, and `backend/python/pyproject.toml` is where it actually ships.
Had the test harness not happened to pull the same package, the scan would have
reported zero criticals against a product that pins a critical.

This inverts the [Kiln](kiln-ai-kiln.html) coverage-asymmetry lesson. There, the
npm front end was on Dependabot auto-updates while three Python `uv.lock` files
drifted uncovered. Here the *test* dependencies are locked and scannable while
the *product* dependencies are not. In both cases the actionable finding is not
a CVE — it is **which part of the tree the scanner can see at all**.

**Recommendation:** commit a `uv.lock` (or equivalent) for `backend/python/`.
It costs one file and makes 69 direct dependencies plus their transitive closure
visible to Trivy, pip-audit, and GitHub's own advisory automation at once.

## What is well built

The honest headline of this scan is that a 389-finding report contains two real
items, and that the surfaces most likely to be catastrophic are the ones the team
has most obviously thought about.

**The CI secret-exposure trap is armed, and defused in a place scanners cannot
see.** `.github/workflows/integration-tests.yml` triggers on
`pull_request_target`, checks out `github.event.pull_request.head.sha` with
`allow-unsafe-pr-checkout: true`, and then runs `npm ci` and `docker compose
build` on that untrusted code — inside a job whose environment holds a Google
Workspace **service-account key with domain-wide delegation**, Jira and Linear
API tokens, SharePoint certificates and private keys, S3 and Azure credentials,
SMTP passwords, and `SECRET_KEY`. Semgrep flags this, correctly and loudly, as
the classic drive-by repository compromise.

It is not exploitable, because the job is bound to a GitHub **Environment**:

```yaml
environment:
  name: ${{ github.event_name == 'schedule' && 'integration-test-daily'
           || 'integration-test-dev' }}
```

Querying the repository's environments API shows `integration-test-dev` —
the one every `pull_request_target` run uses — carries a `required_reviewers`
rule naming three maintainers. The job, and therefore every secret in it, waits
for a human. `integration-test-daily`, which has no protection rules, is used
only by the `schedule` trigger, where the checkout is trusted `main`. The
workflow even sets `permissions: contents: read` and
`persist-credentials: false`.

**The control that makes this safe does not live in the repository.** It lives
in repository settings, and no amount of static analysis of the checked-out tree
can see it. A scanner is structurally incapable of adjudicating a
`pull_request_target` finding on its own — which makes this rule a permanent
source of loud, correct-looking, wrong conclusions unless the environment API is
consulted. That is a tooling lesson, not a project defect.

**The code sandbox is the real thing.** `SANDBOX_MODE` defaults to `local`
(host subprocess) in `app/sandbox/manager.py`, which in isolation reads like a
finding. It is not, because **all five shipped Compose files** set
`SANDBOX_MODE=${SANDBOX_MODE:-docker}` — the [deployment-default
pivot](ucbepic-docetl.html) applied in the project's favour. The container it
launches runs with `network_mode="none"` **and** `network_disabled=True`
(belt-and-braces against Docker versions where one alone is insufficient), a
memory cap and a CPU quota. Package installation happens in a *separate*
short-lived container on a dedicated bridge network that exists solely so
installs can reach a registry — explicitly **not** the Compose project network,
so the sandbox can never reach `mongodb`, `arangodb`, `redis`, `etcd` or `kafka`.
That last detail is the difference between a sandbox and a gesture.

**The deployment does not expose its own databases.** Exactly one `ports:`
mapping exists in the entire Compose file — `${APP_PORT:-3000}:3000`. MongoDB,
Redis, Qdrant, ArangoDB, Neo4j, etcd, Zookeeper and Kafka publish **nothing** to
the host. The `0.0.0.0` listeners Semgrep finds in the etcd and Kafka command
lines bind inside the container network only.

**No shipped default passwords.** Every credential in Compose is
`${VAR:-}` — empty, not a guessable default. `SECRET_KEY` is *required*:
`configuration_manager/config/config.ts` throws on startup if it is unset, rather
than falling back to a constant. That is the opposite of the
[dograh](dograh-hq-dograh.html) fail-open pattern, and it is the right call.

**The live encryption path is correct.** `libs/encryptor/encryptor.ts` — the one
actually used to protect S3 keys, Azure connection strings, SMTP passwords,
OAuth client secrets and database credentials — is AES-256-GCM with a fresh
12-byte IV per encryption and an authentication tag that is set and verified on
decrypt, serialised as `iv:ciphertext:authTag`. Config secrets are additionally
masked on read (`maskConfigSecrets.ts`, with `HIDE_SECRET_CONFIG` defaulting to
`true`) — the [N.E.K.O](project-n-e-k-o-n-e-k-o.html) lesson already learned.

**The retrieval permission model is layered — and one layer is load-bearing by
accident.** `RetrievalService.search_with_filters()` resolves the set of records
a user may see from the graph *first*, then constrains the vector query to those
IDs, then re-intersects the returned IDs against the permitted set before
fetching any record. Two independent checks, with a comment explaining that the
second prevents cross-connector leakage.

There is a seam. When a caller supplies `virtual_record_ids_from_tool`, the
vector filter uses **those** IDs instead of the permission-derived set
(`retrieval_service.py:367`), and the loop that drops non-permitted results
(line 449) has its `final_search_results.append(result)` at line 504 sitting
*outside* the `if virtual_id in virtual_to_record_map:` branch — so an
unverified chunk falls through rather than being discarded.

It still does not leak, because of a filter written for an unrelated purpose.
The response is post-filtered to require `['origin', 'recordName', 'recordId',
'mimeType', 'orgId']`, to "prevent citation validation failures" — and
`recordId` is injected **only** inside the permission-verified enrichment branch.
Indexed chunks carry `origin`, `recordName`, `mimeType` and `orgId` from
`indexing/run.py`, but never `recordId`. An unverified chunk therefore always
fails the completeness gate and is dropped.

So: not a vulnerability, and reported here as neither. But the property "no
unauthorised document content in a response" currently rests on a citation
formatting rule. Add `recordId` to the indexed payload as a perfectly reasonable
optimisation, or relax `required_fields`, and the seam opens with no test
failing. Moving the `append` inside the branch is a two-character fix that makes
the guarantee structural instead of incidental. That is a code-quality note
offered in good faith, not a finding.

## The false positives

**73 of 73 secret findings are false.** Sixty-eight sit in `tests/`,
`mock-data/`, `code-generator/zoom_specs/` (API specification fixtures) and
`README.md`. The five in real source are more interesting, and two are the
inverted kind this series keeps meeting:

- `sharepoint_online/connector.py:405` — flagged `private-key`. The matched
  string is `-----BEGIN RSA PRIVATE KEY-----`, used as a
  `TEXT_NOT_CONTAINS` **validation rule that rejects** RSA-format uploads and
  tells the user how to convert to PKCS#8. Gitleaks flagged the line that
  *protects* the key store — the same inversion as the `0o700` chmod in
  [linkedin-mcp-server](stickerdaniel-linkedin-mcp-server.html).
- `sources/external/dropbox/dropbox_.py:25` and two in `code-generator/` —
  flagged `dropbox-api-token`. All three are **import statements**
  (`from dropbox.team import GroupSelector, UserSelectorArg`). The rule matched a
  dotted module path.
- `api/routes/toolsets.py:1675` — flagged `generic-api-key` on a variable named
  `auth_config` in validation code. No secret present.

`code-generator/zoom_specs/` contributed 16 hits on its own. Alongside IBM's
`.secrets.baseline`, AG2's `# pragma: allowlist secret`, Kiln, and N.E.K.O's
i18n catalogues, that is a **fifth vote** for a structural suppression tier:
generated API-specification fixtures are not credential stores.

**66 path-traversal highs, all false.** Twenty-three are in `__tests__`, four in
an Electron `after-pack` build script. The server-side ones in
`storage/providers/local-storage.provider.ts` run every path through
`sanitizePath()`, which is `path.normalize()` **before** stripping leading `../`
sequences — the ordering that matters, since `normalize` collapses interior `..`
first, so `foo/../../../etc/passwd` becomes `etc/passwd` and stays under the
mount. (A `path.resolve` plus explicit containment check would express the intent
more directly, but the current logic holds.)

**44 mustache-unescape highs** are all `{{{ }}}` in `modules/mail/views/*.hbs` —
notification email templates.

**The one flagged crypto weakness is in dead code.** Semgrep's
`gcm-no-tag-length` fires on `libs/services/encryption.service.ts`. That file
also derives its key with `crypto.pbkdf2Sync(key, crypto.randomBytes(16), ...)`
— **a random salt that is generated per construction and never stored**, meaning
the derived key differs on every process start and nothing encrypted with it
could ever be decrypted again. That would be a serious defect if the class were
used. It is not: the only import anywhere in the repository is its own unit test.
The live encryptor is the other, correct class of the same name. Two classes
named `EncryptionService` in one codebase is a trap worth removing, and the
scanner flagged the harmless one.

**2 wildcard-CORS findings** (`connectors_main.py:592`, `query_main.py:319`) pair
`allow_origins=["*"]` with `allow_credentials=True`, which is a genuine
anti-pattern. Impact here is bounded on three counts: these Python services
publish no host port, authentication is `Authorization: Bearer` rather than
cookies (so a cross-origin page cannot attach the victim's credential), and the
gateway is what browsers actually talk to. Worth tightening; not a live hole.

Also cleared: 37 mutable GitHub-Actions tags and 3 `run-shell-injection` hits in
`workflow_dispatch`-triggered jobs; 12 `dynamic-urllib` hits of which the
`web_search` tool's are constant Brave/DuckDuckGo endpoints with the query
`quote_plus`-encoded; 4 `docker-arbitrary-container-run` findings that *are* the
sandbox; 5 `spawn-shell-true` in Electron build scripts. Notably absent: the
[parameterised-SQL identifier cluster](mnemosyne-oss-mnemosyne.html) that has
dominated almost every prior scan produced exactly **one** hit here.

## Notes on the tool

- **`pull_request_target` cannot be adjudicated from the repository alone.**
  This is the sharpest tooling lesson of the scan. The rule fired correctly on a
  genuinely dangerous-looking workflow, and the control that neutralises it lives
  in the GitHub Environments API. Any curation pass that meets
  `pull_request_target` must now query
  `/repos/{owner}/{repo}/environments` and check for `required_reviewers` on the
  environment the job actually binds to — including resolving the
  `github.event_name == 'schedule' && A || B` expression to the right one. A
  finding of this class reported without that check is a coin flip.
- **Absent lockfiles are invisible failures.** The scan reported 89 dependency
  findings and 0 for the shipped Python backend, and nothing in the output says
  "this tree was not analysed." A `pyproject.toml` with no adjacent lockfile
  should raise an explicit *coverage* warning, in the same family as the
  [0-byte Semgrep report](dataelement-clawith.html) check. "Zero findings" and
  "not scanned" must never render identically.
- **pip-audit produced nothing at all,** and because its meta findings are `info`
  severity they were filtered out by `--min-severity medium`. This is the exact
  gap flagged in the [Clawith](dataelement-clawith.html) write-up and still open:
  scanner-infrastructure findings should be exempt from severity filtering.
- **Grade the guard, then grade what the guard depends on.** The retrieval seam
  above was found by asking "what drops the unverified chunk?" and following the
  answer to a filter with an unrelated purpose. A rule that flags *security
  properties enforced by non-security predicates* would be hard to write and
  valuable to have.
- **Two classes, one name.** The dead `EncryptionService` was nearly reported as
  a live crypto defect. Resolving a flagged symbol to its import graph before
  judging severity should be a standard curation step, not an ad-hoc one.
- **Gitleaks needs a generated-fixture tier** (fifth vote), and its
  `dropbox-api-token` rule should not match `from dropbox.team import ...`.

## Disclosure timeline

- 2026-07-30 — scan run
- 2026-07-30 — public post (this page), with two findings withheld
- pending — private report to `abhishek@pipeshub.com` per the project's
  `SECURITY.md`; full detail to be published here once fixed or after the
  90-day window the policy describes

## Reproduce

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/pipeshub-ai/pipeshub-ai /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/pipeshub-ai-pipeshub-ai --min-severity medium
```
