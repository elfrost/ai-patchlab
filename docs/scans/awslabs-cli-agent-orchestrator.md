---
layout: default
title: "awslabs/cli-agent-orchestrator: security scan"
description: "Security scan of awslabs/cli-agent-orchestrator: 72 findings at medium+, 1 real (Medium) found by hand and reported privately through GitHub, withheld here until a fix ships. All 69 tool findings dismissed. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-24
---

# awslabs/cli-agent-orchestrator — security scan

**Repository:** [awslabs/cli-agent-orchestrator](https://github.com/awslabs/cli-agent-orchestrator)
**Commit scanned:** `6234f1f` (`main`, v2.5.5)
**Scan date:** 2026-11-24
**Disclosure status:** reported privately. One Medium finding was filed through GitHub private
vulnerability reporting on 2026-11-24 and is in triage. The project's `SECURITY.md` rules out
public issues. This page does not describe the finding, or the part of the project it is in,
until a fix ships.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 18 |
| Medium | 51 |
| Low | 0 |
| Info | 3 |

**Total findings:** 72 at `--min-severity medium` (1 real after curation, found by reading the
code; none of the 69 tool findings was real; the 3 info rows are coverage meta findings)

CLI Agent Orchestrator (CAO) runs AI coding CLIs, such as Claude Code, Codex, Kiro and a dozen
others, side by side in tmux sessions, and lets them hand work to each other (1.7k★, Apache-2.0,
published under AWS Labs). Around that core it has a FastAPI server, a stdio MCP server that the
agents use, a web dashboard, a terminal UI, workflows and memory. It is a large project (about
1,400 Python files) and a very busy one: pull requests merged from 22 people and issues closed
from 15 in the 60 days before the scan, with releases on each of the two days before it. Its
`SECURITY.md` names GitHub security advisories and the AWS vulnerability reporting programme as
channels, and rules out public issues. Private vulnerability reporting is enabled, and that is
the channel used.

**Scope of this write-up.** Every tool finding was checked at its call site. The hand review ran
as two parallel slices over the first-party server code, and both completed. The finding was confirmed by running the
function it depends on from the v2.5.5 code with inert values. The full HTTP path was not run,
because the package does not import on Windows, the machine this series runs on. Read the result
as "the tools' 69 findings are accounted for, plus one finding from hand review", not as a full
review of the project.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | A shipped lockfile was not covered by the dependency scan |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep could not parse the 7,500-line
`services/terminal_service.py`, and one subprocess-injection rule timed out on the 12,700-line
`api/main.py`. Both files sit at the centre of the project and were read by hand instead. The
other 18 errors were partial parses of shell scripts, Dockerfiles, a workflow and documentation
HTML. The dependency gap is smaller than the status suggests. pip-audit resolved the
`pyproject.toml` floors and skipped `uv.lock`, but Trivy read `uv.lock`, and both reported zero
advisories.

## Top findings

### 1. One Medium finding, reported privately

- **Tool:** manual review; no rule in the four tools covers it
- **Confidence:** high; the code path was traced end to end in the source, and the function it
  depends on was run from the shipped code with inert values before filing
- **Status:** reported through GitHub private vulnerability reporting on 2026-11-24, in triage
- **Detail:** withheld, including the part of the project it is in, until the maintainers ship a
  fix. This page will be updated then.

## Why the rest were dismissed

All 69 tool findings are accounted for below. The scanner also dropped 3 below the
`--min-severity` floor and 109 under the `--ignore-samples` patterns (Kubernetes and EKS
examples, demo scripts). The `confirmed-real` row is the hand-found item, recorded so that the
corpus counts it.

| Reason | Findings |
| --- | ---: |
| `sql-identifier-fp` | 18 |
| `active-harm-fp` | 16 |
| `domain-noun-collision` | 10 |
| `not-reachable` | 9 |
| `by-design` | 7 |
| `test-or-fixture-path` | 4 |
| `product-surface` | 3 |
| `mitigated-in-app` | 2 |
| `ignore-pattern` (scanner) | 109 |
| `below-min-severity` (scanner) | 3 |
| `confirmed-real` (manual review) | 1 |

The largest family is `sql-identifier-fp` (18). These are SQLite migrations and journals that
build `PRAGMA table_info` and `ALTER TABLE` from hardcoded table names, and `busy_timeout` from
module constants. Every value is bound as a parameter. Next come 16 `active-harm-fp` rows: every
"insecure file permissions" hit is the project's own `0o700` on its home directory, database,
audit log and per-provider runtime folders, and the rule's suggested fix would loosen them. The
10 "credential leak" log lines are inside the project's secret-redaction code, and they log the
name of a key or of the pattern that matched, never a value.

## Patterns observed

**Security work that leaves a paper trail.** Guards in this codebase come with a comment that
names the attack, the CWE, and why the guard sits where it does. The middleware order is an
example. The `Origin` check is registered so that it runs inside the `Host` allowlist, because
it trusts a same-origin `Host` only after that `Host` has been validated. The WebSocket handler
repeats the `Origin` check itself, because CORS middleware never sees a WebSocket scope. Comments
like these make review fast. Each one is a claim, and the code can be checked against it.

**A loopback server that does not rely on loopback.** Desktop tools that bind `127.0.0.1` often
assume that nothing else can reach them. Earlier scans in this series found that a web page
can, through DNS rebinding or a cross-site form post. CAO closes both: a `Host` allowlist, an
`Origin` check on every state-changing method, and a separate `Origin` check on the terminal
WebSocket.

**What the project does well.**
- File reads that take a name from a request resolve it, check it against the allowed base,
  refuse symlinks that point out, and force a fixed suffix. Tried against `..`, absolute paths,
  encoded separators and symlinks, none of them gets out.
- Owner-only permissions are applied everywhere state is written: the home directory, the
  database, the audit log and each provider's runtime folder are `0o700`.
- The MCP Apps views pin the host's origin on the first correlated reply and drop messages from
  any other origin. The wildcard `postMessage` that Semgrep flagged is the documented outbound
  half of that design.

## Notes on the tool

- **A parse failure on a core file reads as quiet.** Semgrep's report on
  `services/terminal_service.py` was an "Other syntax error" line among 21 others, and the
  coverage block surfaced it only because errors are read from Semgrep's `errors` array. The
  backlog item stands: rank coverage errors by the size and centrality of the file, so that a
  7,500-line core module does not sit in the same list as a broken `bootstrap.sh`.

## Disclosure timeline

- 2026-11-24 — scan run at `6234f1f` (`main`, v2.5.5)
- 2026-11-24 — finding verified and reported privately through GitHub private vulnerability
  reporting
- 2026-11-24 — this page published, with the finding withheld

## Reproduce

```bash
git clone https://github.com/awslabs/cli-agent-orchestrator /tmp/scan-target
git -C /tmp/scan-target checkout 6234f1f
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/awslabs-cli-agent-orchestrator --min-severity medium --ignore-samples
```

---

## More from this series

- **Previous scan:** [trustgraph-ai/trustgraph](trustgraph-ai-trustgraph.html) — 2026-11-21, 2 real, withheld
- [Every scan in the series]({{ '/' | relative_url }}) — 122 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 31 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
