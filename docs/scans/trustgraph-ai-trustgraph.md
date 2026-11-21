---
layout: default
title: "trustgraph-ai/trustgraph: security scan"
description: "Security scan of trustgraph-ai/trustgraph: 113 findings at medium+, 2 real (one High, one Medium) found by hand and reported privately through GitHub, withheld here until a fix ships. All 110 tool findings dismissed. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-21
---

# trustgraph-ai/trustgraph — security scan

**Repository:** [trustgraph-ai/trustgraph](https://github.com/trustgraph-ai/trustgraph)
**Commit scanned:** `17e5d74` (`master`, v2.11)
**Scan date:** 2026-11-21
**Disclosure status:** reported privately. Two findings, one High and one Medium, were filed
through GitHub private vulnerability reporting on 2026-11-21, one report each, and are in triage.
The project's `SECURITY.md` rules out public issues. This page does not describe the findings, or
the part of the project they are in, until a fix ships.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 67 |
| Medium | 43 |
| Low | 0 |
| Info | 3 |

**Total findings:** 113 at `--min-severity medium` (2 real after curation, both found by reading the
code; none of the 110 tool findings was real; the 3 info rows are coverage meta findings)

TrustGraph is a platform for building knowledge graphs and graph-based retrieval for AI agents
(3.2k★, Apache-2.0). It runs as a set of Python services on a message bus, with Cassandra and vector
stores behind them, an API gateway in front, an MCP server, and a CLI. It is backed by a company,
TrustGraph.ai, and the hosted service was not examined. The project is active: pull requests merged
from six people and issues closed from six people in the 60 days before the scan, and a 3.0 release
branch was updated the day before it. Its `SECURITY.md` gives an email address for reports, rules
out public issues, pull requests and discussions, and supports only the 2.x line. Private
vulnerability reporting is also enabled on the repository, and that is the channel used.

**Scope of this write-up.** Every tool finding was checked at its call site. The hand review ran as
three parallel slices across the first-party services (about 104,000 lines of Python in 13
packages), and all three completed. Both findings were checked on `master` and on the newer
`release/v3.0` branch before filing. Read the result as "the tools' 110 findings are accounted for,
plus two findings from hand review", not as a full review of the platform.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | No supported Python dependency manifest found |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. **No dependency was audited.** Each of the 13 packages has its own
`pyproject.toml` in a subfolder, there is no manifest at the root and no lockfile anywhere, so
pip-audit had nothing to read. Trivy reports `ran`, but its only targets were the eight
Containerfiles; it read no dependency file either. Treat the absence of dependency findings as
"not examined", not as "clean". Semgrep's 11 errors were partial parses of two workflow files, an
install script, the generated API reference page and one CLI module (`init_pulsar_manager.py`);
there were no rule timeouts.

## Top findings

### 1. Two findings, one High and one Medium, reported privately

- **Tool:** manual review; no rule in the four tools covers them
- **Confidence:** high; each was checked by running the shipped code it depends on, with inert
  values, and traced end to end in the source before filing
- **Status:** reported through GitHub private vulnerability reporting on 2026-11-21, one report per
  finding, in triage
- **Detail:** withheld, including the part of the project they are in, until the maintainers ship a
  fix. This page will be updated then.

## Why the rest were dismissed

All 110 tool findings are accounted for below. The scanner dropped 8 more below the
`--min-severity` floor, and the 3 info rows are the coverage meta findings above. The
`confirmed-real` row is the two hand-found items, recorded so that the corpus counts them.

| Reason | Findings |
| --- | ---: |
| `sql-identifier-fp` | 57 |
| `by-design` | 37 |
| `not-reachable` | 11 |
| `placeholder-secret` | 3 |
| `test-or-fixture-path` | 1 |
| `active-harm-fp` | 1 |
| `below-min-severity` (scanner) | 8 |
| `confirmed-real` (manual review) | 2 |

The largest family is `sql-identifier-fp` (57): Cassandra queries in the graph, row and table
stores, plus a SQLite full-text index. Every value is bound as a parameter. Only keyspace and table
names are built with f-strings, and those names pass through a sanitiser first (anything outside
`[a-zA-Z0-9_]` becomes `_`). The full-text index strips its table name the same way and then quotes
it. The `by-design` rows are 16 WebSocket URLs whose `ws://` or `wss://` scheme follows the gateway
URL the operator configures, 8 containers that run as root, 7 actions pinned by tag, and
dynamic imports of module paths from the operator's own configuration files. The `not-reachable`
rows are three shell-interpolation hits in a container workflow that only maintainer tag pushes can
start, developer scripts that are not packaged, the generated API reference page, and a YAML load
of the operator's process definition file. One `active-harm-fp`: the SHA-1 hit is the SPARQL 1.1
`SHA1()` function, which the standard requires. Replacing it with a stronger hash would break
query compliance.

## Patterns observed

**A specification for nearly everything.** `docs/tech-specs/` holds dozens of design documents,
most of them translated into nine languages. For a reviewer, that turns "is this intended?" into a
lookup, and both findings were checked against the relevant documents before filing. It cuts the
other way too. A precise specification is a list of claims, and the code can be checked against
each one.

**Two install paths, zero audited.** A repository split into many packages, each with its own
`pyproject.toml` and no lockfile, falls through both dependency tools here. The project is not
doing anything wrong. But it is the third shape in this series where a dependency scanner reports
nothing because it found nothing to open, and a reader who skips the coverage block would take
that as a clean result.

**What the project does well.**
- Storage identifiers are sanitised before they reach a query, and every value is bound, across
  dozens of Cassandra and SQLite call sites.
- Object-store keys for uploaded documents are UUIDs generated on the server. No user string
  reaches a storage key or a file path, so there is no traversal to attempt.
- No request data reaches `pickle`, `eval`, `exec`, a subprocess or an unsafe YAML loader. The
  dynamic imports take module paths only from operator files.

## Notes on the tool

- **A split-package repository defeats the dependency scan.** pip-audit looks for a manifest at the
  root, and Trivy found no lockfile. A fallback that audits each subfolder's `pyproject.toml` would
  have covered all 13 packages. This is on the AI PatchLab backlog, next to the earlier note that an
  empty dependency result must never read as clean.

## Disclosure timeline

- 2026-11-21 — scan run at `17e5d74` (`master`, v2.11)
- 2026-11-21 — two findings verified, checked on `release/v3.0`, and reported privately through
  GitHub private vulnerability reporting, one report each
- 2026-11-21 — this page published, with both findings withheld

## Reproduce

```bash
git clone https://github.com/trustgraph-ai/trustgraph /tmp/scan-target
git -C /tmp/scan-target checkout 17e5d74
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/trustgraph-ai-trustgraph --min-severity medium --ignore-samples
```

---

## More from this series

- **Previous scan:** [patrickchugh/terravision](patrickchugh-terravision.html) — 2026-11-19, 2 real, fixed
- [Every scan in the series]({{ '/' | relative_url }}) — 121 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 31 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
