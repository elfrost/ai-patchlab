---
layout: default
title: "heymrun/heym: security scan"
description: "Security scan of heymrun/heym: 253 findings at medium+, 1 real (High) found by hand: the official deployment publishes PostgreSQL on every interface with the example superuser password. Reported privately and declined by the maintainers as a configuration matter, so this page gives operators the fix. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-18
---

# heymrun/heym — security scan

**Repository:** [heymrun/heym](https://github.com/heymrun/heym)
**Commit scanned:** `83b5ecd` (`main`, v0.0.162)
**Scan date:** 2026-11-18
**Disclosure status:** ❌ **declined**. One High-severity finding was reported privately through
GitHub private vulnerability reporting on 2026-11-18, as the project's `SECURITY.md` asks
([GHSA-73pj-mcr8-4c3g](https://github.com/heymrun/heym/security/advisories/GHSA-73pj-mcr8-4c3g)).
The maintainers closed it the same day. In their view it is a matter of deployment configuration,
not a product vulnerability, and no fix is planned; their reply is quoted
[below](#the-maintainers-answer). Because nothing will change upstream, this page now describes the
finding and the three steps operators can take.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 114 |
| Medium | 136 |
| Low | 0 |
| Info | 3 |

**Total findings:** 253 at `--min-severity medium` (1 real after curation, found by reading the
code; none of the 250 tool findings was real; the 3 info rows are coverage meta findings)

heym is a self-hosted platform for building and running agentic workflows (1.7k★, MIT with the
Commons Clause). It has a FastAPI backend and a Vue editor, workflow nodes that call models, tools
and other services, MCP and A2A servers, and retrieval over a vector store. It is busy: 66 issues
closed from 15 authors in the 60 days before the scan. It also has a security process that works.
Its `SECURITY.md` prefers private vulnerability reporting, gives an email fallback, rules out public
issues for vulnerabilities, promises an acknowledgement within three business days, and asks
researchers to test only on their own instance. The repository already lists five published
security advisories.

**Scope of this write-up.** Every tool finding was checked at its call site. The planned hand
sweeps of the sharing boundary, the unauthenticated and token-gated routes, and egress and path
confinement did not complete, because the automated run ended before they returned. Read the result
as "the tools' 250 findings are accounted for, plus one finding from hand review", not as a full
review of the platform.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | No supported Python dependency manifest found |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep scanned 2,002 paths and reported 14 errors. One matters most:
the backend's 3,178-line ORM models module (`backend/app/db/models.py`) got no rules at all.
Semgrep failed on its own temporary file under Windows and reported the failure as a syntax error.
Five rule timeouts hit three large modules (`workflow_executor.py` and two frontend files), and
eight partial parses lost some lines elsewhere. `dependency-scan` looked for a Python manifest at the
repository root and found none, because the backend's lives in `backend/`. Trivy read both
lockfiles: `backend/uv.lock`, with no advisories, and `frontend/bun.lock`, with the 56 advisories
counted below.

## Top findings

### 1. The official deployment publishes the database with the example password (High, declined)

- **Files:** `docker-compose.yml:29` and `:36-37`, `.env.example:5-7`, `deploy.sh` (`prepare_env()`)
- **Tool:** manual review; no rule in the four tools covers it
- **Confidence:** high, verified with Docker's own renderer (`docker compose config`) on the files as
  shipped. Nothing was started and no instance was contacted
- **Why it matters:** `deploy.sh`, the documented production path, copies `.env.example` to `.env`,
  generates `SECRET_KEY` and `ENCRYPTION_KEY`, and starts `docker-compose.yml`. It leaves the
  database password at its example value. The compose file publishes PostgreSQL as
  `"${POSTGRES_PORT:-6543}:5432"` with no host address, so Docker binds every interface, and
  `.env.example` sets `POSTGRES_USER=postgres` and `POSTGRES_PASSWORD=postgres`. A default
  deployment therefore accepts a superuser login, with a publicly known password, on port 6543 of
  every network the host is on. Docker's published ports also bypass host firewalls such as ufw.
  The deployment guide says the opposite: *"there is only one public-facing port in production."*
- **Impact:** whoever reaches that port can read and change the whole heym database: users and
  password hashes, sessions, workflows and their stored outputs. Stored credentials are encrypted
  with `ENCRYPTION_KEY`, which is not in the database, but write access is enough to take over any
  account.

**If you run heym, three steps close it.** None of them depends on an upstream change.

1. **Stop publishing the database port.** In `docker-compose.yml`, remove the `ports:` entry of the
   `postgres` service, or bind it to loopback: `"127.0.0.1:${POSTGRES_PORT:-6543}:5432"`. The
   backend reaches the database as `postgres:5432` on the internal network and does not need the
   published port.
2. **Change the database password.** Editing `.env` is not enough for a database that already
   exists, because the postgres image applies the password only when it first creates its data. Run
   `ALTER USER postgres PASSWORD '...'` inside the database container, then put the same value in
   `.env`.
3. **Close port 6543 at your provider's firewall** as well, since Docker's published ports bypass
   ufw.

The local development script `run.sh` publishes the same port with the same default, and
`docker-compose.cluster.yml` follows the same pattern on port 6544.

## The maintainers' answer

Quoted in full, as the series does for every declined report:

> Hi,
>
> Thanks for the report.
>
> We've reviewed the findings and decided to reject this advisory.
>
> Heym is a self-hosted platform. Database credentials, ports, and network settings are documented
> and configurable through environment variables.
>
> The credentials in .env.example are example values, not secrets. Operators are expected to
> configure their deployment environment, including database credentials and network access,
> according to their security requirements.
>
> The reported scenario assumes that an operator deploys the application with example credentials
> and makes the database accessible to untrusted networks.
>
> The report does not demonstrate an authentication bypass or an application-level authorization
> vulnerability. It describes the security implications of a particular deployment configuration.
>
> We do not consider the findings sufficient to establish a distinct product vulnerability or
> justify a CVE.
>
> Thanks for your contribution.
>
> Best regards,
> The Heym Team

They are right on several points. The values in `.env.example` are examples, operators own their
deployments, and nothing here bypasses authentication in the application itself. The disagreement
is narrower. The project's own production script turns the examples into the deployed values: it
replaces the two application secrets and keeps the example database password. The compose file it
starts then publishes the database on every interface, while the guide tells operators that only one
port is public. An operator who follows the documentation makes the choice the reply describes
without knowing it. One line in the compose file and one more generated value in the script would
make the documented path safe by default. I respect the decision; this page exists so that operators
do not have to find this out on their own.

## Why the rest were dismissed

All 250 tool findings are accounted for below. The scanner dropped 53 more below the
`--min-severity` floor, and the 3 info rows are the coverage meta findings above. The
`confirmed-real` row is the hand-found item, recorded so that the corpus counts it.

| Reason | Findings |
| --- | ---: |
| `by-design` | 53 |
| `credited-defense` | 34 |
| `test-or-fixture-path` | 31 |
| `placeholder-secret` | 28 |
| `dependency-currency` | 27 |
| `not-reachable` | 25 |
| `domain-noun-collision` | 21 |
| `sql-identifier-fp` | 17 |
| `product-surface` | 8 |
| `sample-or-demo` | 6 |
| `below-min-severity` (scanner) | 53 |
| `confirmed-real` (manual review) | 1 |

The largest curated family is `by-design` (53). Eighteen of those rows are workflow actions pinned
by tag rather than by commit SHA; the rest are hardening and lint rules that describe a choice, not
a flaw. The `credited-defense` rows say the most about the code: 30 of the 34 are Vue `v-html`
sinks, and every one of them renders through `DOMPurify.sanitize`. The 27 `dependency-currency` rows
are `axios` 1.15.2 in the frontend bundle, one release line behind the fix. Most of its advisories
describe the Node adapter, which the browser build does not use.

## Patterns observed

**A security process that already works.** The project has five published advisories, a policy
that names its channel and its timeline, and private reporting turned on. That combination makes a
private report cheap for everyone, which is why this one went out the same day it was found.

**An example that a script copies is a default.** `.env.example` is an example until `deploy.sh`
copies it to `.env`. From then on, its values are what ships, and the line between "example value"
and "deployment configuration" is exactly where this finding sits. The project already treats two
of those values as defaults to replace: it generates `SECRET_KEY` and `ENCRYPTION_KEY`, and refuses
a legacy placeholder key. The database password is the one that was left behind.

**The tools' findings and the real one did not overlap.** As in most well-built projects in this
series, the scanner output could be dismissed quickly, and the finding came from reading. The
tools' useful work here was negative: they showed, fast, where nothing was wrong.

**What the project does well.**
- Every `v-html` sink in the Vue frontend goes through `DOMPurify.sanitize`, either in
  `lib/markdown.ts` or in a component-level renderer.
- `lib/fileAccept.ts` escapes every regex metacharacter before it turns a MIME glob into a `RegExp`.
- The OpenCode runner starts with `subprocess.Popen` on an argument list, with no shell and stdin
  closed.
- WebSocket URLs map `https` to `wss` instead of forcing plaintext.
- The 17 raw-SQL hits interpolate only module constants (a table name, a fixed search query), and
  every value is bound.
- The 21 "secret in a log" hits log ids, names and counts, never the secret itself.

## Notes on the tool

- **Semgrep failed on a file and called it a syntax error.** The ORM models module got no rules
  because Semgrep could not use its own temporary file under Windows (`Permission denied`), yet the
  error type read "syntax error". A tool-side failure and a real parse error need different
  responses, so the coverage report should tell them apart. This is now on the AI PatchLab backlog.
- **pip-audit looks only at the repository root**, so a backend kept in a subdirectory reads as
  "no manifest". Trivy's read of `backend/uv.lock` is what kept the Python dependencies covered.

## Disclosure timeline

- 2026-11-18 — scan run at `83b5ecd` (`main`, v0.0.162)
- 2026-11-18 — one finding verified and reported privately through GitHub private vulnerability
  reporting
  ([GHSA-73pj-mcr8-4c3g](https://github.com/heymrun/heym/security/advisories/GHSA-73pj-mcr8-4c3g)).
  The automated run that found it ended before filing, so the report and this page were completed
  from an attended session the same day
- 2026-11-18 — this page published, with the finding withheld
- 2026-11-18 — the advisory was closed 49 minutes after it was filed (14:21:25Z to 15:10:10Z), with
  `submission.accepted` still `false`. That is a declined report, not a resolved one. GitHub's
  advisory API does not expose the private comment thread, so I cannot see whether a reason was
  given, and I am not going to guess at one
- 2026-11-19 — re-checked upstream at `ddb1493`. The files the report named are unchanged since the
  scan, and v0.0.163 shipped after the closure without touching them, so this was not a quiet fix
  followed by a cleanup close. The finding stays withheld: the project's `SECURITY.md` rules out
  public reports, and a closed private report does not change that. This entry is here because the
  series records declined reports rather than deleting them. It is not a complaint: a project is
  entitled to triage an unsolicited report however it sees fit
- 2026-11-19 — the maintainers' reasoning, posted in the advisory thread, reached me and is quoted
  [above](#the-maintainers-answer): a matter of deployment configuration, not a product
  vulnerability, and no CVE
- 2026-11-19 — this page updated to describe the finding, with three steps for operators. The
  previous entry kept the finding withheld because a closed report alone does not say whether a fix
  is coming. The answer does: none is coming, and the maintainers' position is that operators must
  secure the database themselves. The steps above are what that takes on the official deployment

## Reproduce

```bash
git clone https://github.com/heymrun/heym /tmp/scan-target
git -C /tmp/scan-target checkout 83b5ecd
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/heymrun-heym --min-severity medium
```

---

## More from this series

- **Previous scan:** [jordan-gibbs/hyperresearch](jordan-gibbs-hyperresearch.html) — 2026-11-17, 0 real
- [Every scan in the series]({{ '/' | relative_url }}) — 119 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 30 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
