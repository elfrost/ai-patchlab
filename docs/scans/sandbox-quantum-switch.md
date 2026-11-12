---
layout: default
title: "sandbox-quantum/switch: security scan"
description: "Security scan of sandbox-quantum/switch: 442 findings at medium+, none of them real after curation; 3 real findings from reading the code by hand (2 High, 1 Medium), reported privately through GitHub private vulnerability reporting and withheld here. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-12
---

# sandbox-quantum/switch — security scan

**Repository:** [sandbox-quantum/switch](https://github.com/sandbox-quantum/switch)
**Commit scanned:** `517d1e5` (`main`)
**Scan date:** 2026-11-12
**Disclosure status:** withheld — three findings reported privately through GitHub private
vulnerability reporting, which the project's `SECURITY.md` asks for. All three are in triage.
This page describes none of them beyond their severity until the maintainers have resolved them.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 6 |
| High | 206 |
| Medium | 227 |
| Low | 0 |
| Info | 3 |

**Total findings:** 442 at `--min-severity medium` (the 3 info rows are coverage meta findings).
None of the 439 tool findings survived curation as a vulnerability. Three real findings came
from reading the code by hand: **two High and one Medium**, reported privately on the day of the
scan.

Switch puts AI agents into the chat tools a team already uses: Slack, Microsoft Teams, Discord,
Telegram, Mattermost and seven more platforms, plus its own desktop app, Switch Console. Each
channel becomes a room where people and agents (Claude Code, Codex, Cursor, OpenCode, or one
you built) work together, with connectors to Google Workspace, Atlassian, GitHub, Datadog and
Airtable (4.4k★, Apache 2.0 with the Commons Clause, backed by SandboxAQ). It is a large
codebase: the control plane `switch_core` is 715 Python files and about 230,000 lines, with
another 895 test files; Switch Console is about 2,600 TypeScript files, and the web dashboard
another 228. It is also a busy one: in the 60 days before the scan, 26 people merged more than
100 pull requests and 87 issues from 30 people were closed.

**Scope of this write-up.** Every tool finding below was checked at its call site. The hand
review ran as six slices in parallel: inbound requests from all twelve messaging platforms
(signature checks and app-install flows), the API that agents call, authorization on the 234
routes of the human-facing gateway, sessions and tokens, the management plane with the shipped
Compose, Helm and Terraform defaults, and connectors, server-side fetches and files. Read
separately: the six loopback servers in Switch Console, the policy that decides who may address
an agent and how a chat account is linked to a Switch user, the decision service, and the CI
workflows. Not read line by line: the outbound rendering in each platform adapter, the model
servers, and Switch Console's renderer beyond the places a tool flagged. Read the result as "the
tools' findings are accounted for and the controls named below hold", not as an audit of every
module.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | No supported Python dependency manifest found |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep scanned 4,147 paths and reported 85 errors. Ten were rule
timeouts: nine on TypeScript in Switch Console and the dashboard (three of them test files), and
one on `core/switch_core/bridges/collaboration/mattermost/adapter.py`, for the rule that flags
plain-HTTP `requests` calls. The other 75 were parse errors on files that are not Python: Helm
templates, which are Go templates rather than YAML until rendered, GitHub workflows, shell
scripts, Dockerfiles and a few TypeScript files. No `switch_core` module failed to parse. The
workflows were read by hand instead: PR CI runs on `pull_request`, with a comment saying never to
switch it to `pull_request_target`, and the one `pull_request_target` workflow (the CLA bot)
checks out no pull-request code and pins its actions by SHA. The `dependency-scan` row is
`partial` because the Python project lives in `core/`, not at the root, so pip-audit found no
manifest. Trivy read `core/uv.lock`, and that lock is what ships: the image runs
`uv sync --frozen --no-dev` on it. Trivy also read `console/pnpm-lock.yaml` and the hosted
controller's `uv.lock`.

## Top findings

### 1–3. Three findings reported privately (2 High, 1 Medium)

- **Found by:** reading the code; none of the 439 tool findings points at them.
- **Channel:** GitHub private vulnerability reporting, one report per finding, as the project's
  `SECURITY.md` asks. All three were accepted into triage on 2026-11-12.
- **Detail:** withheld until the maintainers have resolved them. This page will be updated then.

### 4. A hardening note in Switch Console: one placeholder of the "Open in" commands is not quoted

- **Files:** `console/apps/switch-console-desktop/src/main/core/app/service.ts:254-266`,
  `console/apps/switch-console-desktop/src/shared/openInApps.ts`
- **Tool:** manual review (behind a `detect-child-process` hit)
- **Confidence:** high on the behaviour; it needs a folder name the user picked
- **Why it matters:** "Open in" runs each app's command template through a shell. The
  `{{path}}` placeholder is quoted properly for each platform, but `{{path_raw}}` is substituted
  as is, inside double quotes, in the templates for Alacritty, Athas, Trae and Trae Solo and in
  the Windows `cmd /K "cd /d …"` entry. `$(…)` still expands inside double quotes on macOS and
  Linux, and `&` ends the command inside `cmd /K`. The path is a folder the user chose in the
  system folder picker, so this takes a booby-trapped folder name, for example inside a cloned
  repository. It is not a vulnerability as written.
- **Recommendation:** use the quoted form everywhere, or pass the path as an argument to
  `execFile` rather than building a shell string.

## Why the rest were dismissed

All 439 tool findings are accounted for below, and the 3 meta findings are the coverage rows
above. No ignore pattern removed anything (`--ignore-samples` was on and matched nothing); the
scanner dropped 24 findings under the `--min-severity medium` floor. The `confirmed-real` row is
the three private reports; the one `product-surface` hardening row is note 4, recorded so the
corpus counts the hand-found items as well.

| Reason | Findings |
| --- | ---: |
| `sql-identifier-fp` | 266 |
| `not-reachable` | 68 |
| `product-surface` (25 tool findings + note 4) | 26 |
| `below-min-severity` (scanner) | 24 |
| `by-design` | 24 |
| `dependency-currency` | 21 |
| `domain-noun-collision` | 13 |
| `test-or-fixture-path` | 9 |
| `mitigated-in-app` | 8 |
| `active-harm-fp` | 3 |
| `confirmed-real` (manual review, withheld) | 3 |
| `credited-defense` | 2 |

**The SQL rows are 266 of the 439.** 258 of them sit in `core/switch_core/migrations/versions/`:
Alembic migrations that format constant index and table names into DDL at deploy time. Of the
other eight, six build `text()` statements from module-level fragments with every value bound,
and two, in the hosted controller's store, check the column name against an explicit allowlist
first ("invalid intent column").

**The 25 `product-surface` rows are Switch Console starting processes**, which is its job: it
installs and launches agent CLIs, a local Switch server and Docker. Arguments come from bundled
constants or the user's own choices, and agent CLIs are spawned with argument arrays; on Windows,
npm's `.cmd` shims are quoted by hand rather than run with `shell: true`.

**Dependencies.** The image ships `core/uv.lock`, so its versions are the ones that run. The
reachable items: `aiohttp` 3.14.3 (fixed in 3.14.4) serves the inbound webhook listener and the
bring-your-own Teams listener, so its missing timeout before the first request byte applies to a
public port (availability only); `certifi` predates the removal of the compromised emSign root;
`anyio` has the IDNA 2003 hostname check, which needs a non-ASCII host and an on-path attacker.
Not reachable: the eight `authlib` advisories, because Switch imports only its Starlette OIDC
client (an authorization-code flow) and the advisories cover JWS JSON parsing, OAuth server
endpoints and implicit flows; FastMCP's transform authorization, because no transforms are used;
the MCP SDK's session-retention advisory, because the server runs `stateless_http=True`. In
Switch Console, the MCP SDK's request-size advisories are behind the bearer check that the
runtime makes before the SDK sees a request, and the Express, Hono and URI-parser advisories
arrive as transitive dependencies (of the SDK and of `ajv`) and serve nothing.

**Three rows would do harm if "fixed".** Semgrep's SHA-1 rules matched RSA-OAEP with SHA-1, which
is how Microsoft Graph wraps the key of an encrypted change notification, and the legacy `x5t`
certificate thumbprint that older Entra endpoints still read (sent beside `x5t#S256`, marked
`usedforsecurity=False`). Changing either breaks the integration.

## Patterns observed

**Every token check in Switch Console's loopback servers is right.** Desktop apps in this series
have more than once shipped `127.0.0.1` servers that any web page could reach. Switch Console
opens six: the control API, the relay agents use to reach the server, the MCP endpoint for hosted
agents, two host endpoints and a raw TCP control socket. Each demands a secret before it routes
anything. Five compare in constant time or look the token up by its hash. The sixth compares
with `!==`, but it speaks a line protocol a browser cannot produce, and its token file is written
`0o600` through an atomic rename. The secret travels in a header or a first
message, so a page that rebinds its domain to loopback still has nothing to send. The relay mints
one 256-bit token per agent, refuses a path that names a different agent, and takes the room of a
call only from the calling agent's own placements, so a session id belonging to another agent
returns nothing.

**Twelve platforms, and every inbound request is checked before it is acted on.** Slack's HMAC
with its five-minute window, the Bot Framework JWT with key endorsement and a `serviceurl` claim that must
match the body, Microsoft Graph validation tokens, Telegram's secret header, WhatsApp's
`X-Hub-Signature-256`, and per-bridge HMAC on Mattermost buttons. Every comparison goes through
`compare_digest`. The secret is chosen by the platform or bridge named in the URL, never by a
field in the body, and a missing secret fails closed. The other platforms connect outward
(Socket Mode, the Discord Gateway, Pub/Sub, websockets, long polling) and so have no inbound
surface at all.

**A restricted agent is deny-by-default, and a chat account has to prove itself.** With an
addressing policy set, a sender that cannot be resolved is refused rather than given the benefit
of the doubt, and a platform's "on behalf of" marker is honoured only on the platform's own
messages. Senders resolve by the platform's account id, not a display handle that can change
hands. A new link between a Slack or Mattermost account and a Switch user counts for nothing
until the account posts a one-time code that only the person being linked was shown; links made
before that rule existed keep counting until an admin requires confirmation. The links are
non-exclusive on purpose: an exclusive claim would let whoever came first lock the real person
out of being recognised by their own agents.

**Where the defaults come from.** Every port in both Compose files binds
`${SWITCH_BIND_ADDR:-127.0.0.1}`. `.env.example` ships blank secrets with a generator that uses
`openssl rand`. Helm marks its secrets `required`, and it gives the decision service a
NetworkPolicy plus a generated bearer token, with a comment saying the token is what keeps other
pods out on a CNI that ignores NetworkPolicy. Hosted workers have no inbound rule, egress only to
ports 80 and 443, IMDSv2 enforced by an IAM deny, and an "isolation" security group that the
controller has no permission to undo. The SSRF guard on connector traffic resolves the host,
checks every address, then connects to the address it checked, and connector URLs come only from
the built-in catalog.

## Notes on the tool

- **None of the three real findings came from a tool**, and none of the 439 tool findings was
  real. Each of the three only appears when two parts of the code, each reasonable on its own,
  are read against each other. A per-file rule cannot see that.
- **Alembic migrations should be auto-flagged.** 258 of 439 findings, 59%, sit in
  `migrations/versions/`. The backlog item exists for `alembic/versions/**`; it should match
  `**/migrations/versions/**` too.
- **pip-audit only looks at the root**, so a monorepo whose Python project sits in `core/` reads
  as "no manifest". Trivy covered it this time. The dependency scan should look one level down
  when the root has nothing.
- **Helm templates are not YAML until rendered.** 30 of Semgrep's 75 parse errors were chart
  templates. Rendering the chart with its default values before scanning would turn them into
  coverage instead of noise.

## Disclosure timeline

- 2026-11-12 — scan run at `517d1e5`; three findings verified by reading the code
- 2026-11-12 — reported privately through GitHub private vulnerability reporting, one report per
  finding; all three accepted into triage the same day
- 2026-11-12 — this post, with the findings withheld

## Reproduce

```bash
git clone https://github.com/sandbox-quantum/switch /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/sandbox-quantum-switch --min-severity medium --ignore-samples
```

---

## More from this series

- **Previous scan:** [haris-musa/excel-mcp-server](haris-musa-excel-mcp-server.html) — 2026-11-09, 0 real
- [Every scan in the series]({{ '/' | relative_url }}) — 117 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 29 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
