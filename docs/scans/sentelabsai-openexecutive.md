---
layout: default
title: "SenteLabsAI/OpenExecutive: security scan"
description: "Security scan of SenteLabsAI/OpenExecutive: 124 findings at medium+ collapse to one real gap — a webhook whose verification is skipped when its optional secret is unset, disclosed privately (detail withheld). Plus a security policy pointing at a channel that is switched off."
date: 2026-08-30
---

# SenteLabsAI/OpenExecutive — security scan

**Repository:** [SenteLabsAI/OpenExecutive](https://github.com/SenteLabsAI/OpenExecutive) — 2.9k★, an "AI-powered virtual executive team": a single coherent executive persona backed by eight specialist Claude agents. A FastAPI backend and a Next.js UI (`packages/core`, `packages/ui`), deployed to Fly, with Telegram, Google Chat, Discord and MCP integrations.
**Commit scanned:** `755d8ec13083` (HEAD of `main` at scan time)
**Scan date:** 2026-08-30
**Disclosure status:** **Private — detail withheld.** The project's `SECURITY.md` asks that vulnerabilities not be reported "through public GitHub issues, discussions, or pull requests." One Medium-severity finding is being routed privately; only the finding *class* appears below. This page will be expanded once the maintainers resolve, or after a 90-day window.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 3 |
| High | 59 |
| Medium | 59 |
| Low | 0 |
| Info | 3 (filtered) |

**124 findings at `--min-severity medium`. After curation: one real defect — and it is not in the list the scanners produced.** All three "criticals" retired. So did all 60 SQL findings, all 7 secret hits, and most of the dependency table. The one real item is an authentication check that is skipped under a configuration the project's own `.env.example` ships as the default.

This is a well-built codebase with an unusually honest security posture — including a written threat model that lists what it *does not* protect against. That made the scan more interesting, not less: when the obvious controls are all present and correct, the remaining defect is a seam between two of them.

## The finding (class only, detail withheld)

**Class:** conditional verification bypass on an externally-reachable webhook — CWE-306
(missing authentication for a critical function), by way of CWE-1188 (insecure default).

The shape, without the specifics. The API sits on a public URL and gates every route behind
a shared-secret header, compared in constant time, with a fail-closed startup guard in
production. A small set of webhook paths are deliberately exempt from that gate, because
they are called by external services that — in the project's own words — "carry their own
verification." The security documentation lists each exempt path next to the credential it
checks for itself.

For one of those exempt paths, that self-verification is wrapped in a conditional: it runs
only if an *optional* secret is configured. When the secret is unset, the check does not
fail — it is skipped entirely, and the request proceeds to the handler with no caller
credential of any kind. The endpoint's router is registered unconditionally and its path is
permanently exempt, so the only thing standing between the public internet and the handler
body is a setting that three of the project's own documents describe as optional and that
its `.env.example` ships blank.

The sibling webhook, handling the same class of external caller in the same application,
does it the other way round: it verifies unconditionally and returns 401 both when the
credential is missing and when it is forged. **That intra-repo difference is the proof of
intended contract** — nobody has to accept an outside opinion about what the check should
do, because the codebase already contains the correct version of it, one file away.

A second control downstream does meaningfully limit the impact, and the maintainers deserve
credit for it: reaching the interesting behaviour requires knowing an identifier that is not
published, and the endpoint returns an identical response whether or not that identifier
matches, so it offers no oracle for guessing. That is why this is filed as **Medium** and not
High. But it is the *second* gate doing that work. The first gate — the one the security
documentation says is there — is not running.

**Verified by execution, not by reading.** The differential was reproduced locally against
the repository's real router code with the real middleware: control route rejects without the
shared secret; sibling webhook rejects both a missing and a forged credential; the subject
webhook rejects correctly *when the optional secret is set*; and accepts an unauthenticated,
attacker-composed request when it is not. Four cases, one of which is supposed to be
impossible.

## The other finding, which is not a vulnerability

The project's `SECURITY.md` is a good one — it is specific, it names the components in scope,
and it explicitly invites a class of report most projects never think to mention. It gives
exactly one channel:

> Instead, use GitHub's private vulnerability reporting: Go to the repository's **Security**
> tab. Click **"Report a vulnerability"**. […] Please use this channel rather than email so
> reports are tracked and not missed.

Private vulnerability reporting is **disabled** on the repository. `GET
/repos/SenteLabsAI/OpenExecutive/private-vulnerability-reporting` returns
`{"enabled": false}`, and the button the policy describes is not rendered. So the policy
forbids public issues, directs reporters away from email, and points at a form that does not
exist. A reporter who follows the instructions exactly arrives at a dead end.

This is worth saying plainly because it is invisible from inside the project: the policy file
is correct, the intent is correct, and a maintainer reading their own `SECURITY.md` has no
way to notice that the switch behind it is off. It costs one checkbox in Settings → Security
to fix. It is also a general lesson — a documented channel is a claim about infrastructure,
and claims about infrastructure should be probed with a request, not read.

## What retired, and why

The gap between 124 and 1 is the whole job. In order of size:

**60 SQL findings → 0.** Forty `sqlalchemy-execute-raw-query` plus twenty
`formatted-sql-query`, spread across sixteen files. Every one is identifier-only
interpolation in additive schema migrations — `PRAGMA table_info({table})` and
`ALTER TABLE {table} ADD COLUMN {col} {ddl}`, where `table`, `col` and `ddl` are literals
from a hardcoded tuple in the loop directly above. A sweep for interpolated *values* in SQL
across the 393 `execute()` calls in the package returned nothing but log strings. This is now
the **tenth** appearance of this exact cluster in the series and remains its single largest
noise source.

**7 secret hits → 0.** All seven are `discord-client-id` matches in one unit test, on
strings like `111222333444555666` and `123456789012345678`. They are placeholder Discord
snowflakes — and Discord user IDs are public identifiers in any case, not credentials.

**1 critical Docker finding → 0.** "Secrets passed via `build-args` or envs" fires on
`docker/Dockerfile:105`, which reads
`ENV WORKSPACE_MCP_CREDENTIALS_DIR=/data/google_credentials`. That is a **directory path**.
The rule matched the word `CREDENTIALS` in a variable name and rated it critical.

**2 critical + 2 high ChromaDB CVEs → not reachable.** ChromaDB 1.5.9 is locked, and the
advisories are real: pre-authentication code execution via `trust_remote_code`, and
cross-tenant authorization failures, both against
`/api/v2/tenants/{tenant}/databases/{db}/collections`. The project instantiates
`chromadb.PersistentClient` — embedded, on-disk, no HTTP listener, no tenants API, no server
to send that request to. The affected surface is not deployed here.

**PyJWT "authentication bypass via forged JWT" → not reachable from first-party code.**
The inviting inference is that a JWT bypass lands somewhere in the authentication path. It
does not: there is no `import jwt` anywhere in the package, and the token verification the
application does perform runs through a Google-maintained library rather than PyJWT. The
dependency is transitive. Worth upgrading on general principle; it is not an active bypass in
this application. Resolving a flagged package to its actual import graph took one grep and
removed a "high" from the report.

**Starlette UNC/StaticFiles SSRF → not applicable.** Windows-only; the deployment is a Linux
container on Fly.

**20 GitHub Actions "mutable action tag" findings → hardening.** Real supply-chain advice —
pin actions by commit SHA. But all three workflows trigger on `push` and `pull_request`, not
`pull_request_target`, so fork PRs run without repository secrets. The severity of this class
is a function of the trigger, and this trigger is the safe one.

**The pypdf DoS cluster (~12 findings) → hardening.** Genuine denial-of-service bugs, but
they require an attacker-supplied PDF, and document upload sits behind the allow-list the
threat model explicitly defines as trusted.

## Credit where it is due

Four decisions in this codebase are worth naming, because a scan write-up that only lists
defects gives a false picture of the thing it scanned:

- **The shared-secret gate is written correctly.** `hmac.compare_digest`, exact-match path
  exemptions rather than prefix matching, and a `RuntimeError` at startup if the secret is
  missing while running on Fly. It fails closed in the place where failing open would be
  invisible.
- **The MCP endpoint's DNS-rebinding decision is right, and the reasoning is written down.**
  FastMCP's Host-header check is disabled — normally a flag worth chasing. Here the module
  docstring explains it: `/mcp` is deliberately *not* in the exempt-paths set, so the
  shared-secret middleware gates it, and the credential is a header rather than a cookie, so
  a rebinding browser cannot supply it. That is a correct analysis of what rebinding actually
  exploits. Two of the three flagged MCP SDK advisories concern the WebSocket transport,
  which this project does not use.
- **Elsewhere in the same application, this is done correctly.** Verify first, branch second,
  401 on both a missing and a forged credential — no configuration required to make it hold.
- **The threat model documents its own limits.** `docs/auth.md` lists what the design does
  *not* mitigate, including the absence of per-user data isolation. That declaration is why
  this scan does not report cross-user data access as a finding: it is a stated product
  boundary, not an oversight. A project that tells you where its walls end is much easier to
  assess honestly than one that implies there are walls everywhere.

## Patterns observed

**An optional secret is a security control with an off switch, and defaults decide which
position it ships in.** The pattern that produced this finding is not exotic. Someone added
a verification step, made it configurable so local development would not require it, and the
conditional that enables local development is the same conditional that disables the check in
production. The documentation then diverged: one file calls the secret required, two call it
optional, and the security document describes the check as unconditional. All three
statements were written by people who were correct about their own layer.

**The sibling is the strongest available evidence.** This is the second scan in a row where
the most persuasive part of the report was not an external standard but a second
implementation inside the same repository. It removes the argument. A maintainer can dispute
whether a check is necessary; it is much harder to dispute that two handlers doing the same
job should agree, when one of them is already right.

**Scanners find dangerous calls; the defects are missing checks.** All 124 findings describe
something the code *does*. The real one is something it *skips*. Three scans running, the
item that survived curation was invisible to every rule — and the retired findings, by count,
were 100% of the scanner's output.

## Notes on the tool

- **The dependency scanner covered nothing again.** `scan_dependency` probes only the
  repository root, found no manifest there, and emitted
  `dependency-scan-no-supported-manifest`. The real Python surface is
  `packages/core/pyproject.toml` + `uv.lock`. Trivy found it and produced the CVE table, so
  coverage was not zero — but pip-audit contributed nothing, and on a monorepo the "no
  manifest" message reads like "clean." This is the **second consecutive scan** to hit it
  (Zleap-AI/SAG, 2026-08-27). Promoting it from note to backlog item: the dependency scanner
  should walk `packages/*/` and `apps/*/` the way the fingerprint indexer already recurses.
- **Semgrep coverage was near-complete but not complete.** Five `PartialParsing` errors, zero
  rule timeouts: two Dockerfiles, two shell scripts, and `packages/ui/src/app/demo/page.tsx`.
  The one that matters is the `.tsx` — a real UI source file that no rule ran against. Its
  absence from the results is not evidence that it is clean.
- **The "critical" tier did no work this scan.** Three criticals: one directory path matched
  on a variable name, two CVEs against a server that is not deployed. A severity label
  assigned without knowing the deployment shape is a guess, and here all three guesses were
  wrong in the same direction.

## Disclosure timeline

- 2026-08-30 — scan run; the webhook differential reproduced by execution against the real
  router code
- 2026-08-30 — private report drafted. The channel named in `SECURITY.md` (GitHub private
  vulnerability reporting) is disabled, and the policy directs reporters away from email, so
  the report is being routed to the organisation's published contact address with a note
  about the closed channel.

## Reproduce

```bash
git clone https://github.com/SenteLabsAI/OpenExecutive /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/sentelabsai-openexecutive --min-severity medium

# the dependency surface the root-only scan misses:
cd /tmp/scan-target/packages/core && pip-audit .

# the channel probe — a documented reporting channel is a claim about
# infrastructure, so send a request rather than reading the policy file:
gh api repos/SenteLabsAI/OpenExecutive/private-vulnerability-reporting
```
