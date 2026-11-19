---
layout: default
title: "heymrun/heym: security scan"
description: "Security scan of heymrun/heym: 253 findings at medium+, 1 real (High) found by hand and reported privately through GitHub. The report was closed without being accepted, and the finding stays withheld. All 250 tool findings dismissed. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-18
---

# heymrun/heym — security scan

**Repository:** [heymrun/heym](https://github.com/heymrun/heym)
**Commit scanned:** `83b5ecd` (`main`, v0.0.162)
**Scan date:** 2026-11-18
**Disclosure status:** reported privately, then closed without being accepted. One High-severity
finding was filed through GitHub private vulnerability reporting on 2026-11-18, as the project's
`SECURITY.md` asks
([GHSA-73pj-mcr8-4c3g](https://github.com/heymrun/heym/security/advisories/GHSA-73pj-mcr8-4c3g)).
**The advisory was closed unaccepted 49 minutes after filing** (see
[timeline](#disclosure-timeline)). No reason is visible to me, and the finding stays withheld: this
page does not describe it, or the part of the project it is in.

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

### 1. One High-severity finding, reported privately

- **Tool:** manual review; no rule in the four tools covers it
- **Confidence:** high, verified before filing
- **Status:** reported through GitHub private vulnerability reporting on 2026-11-18
  ([GHSA-73pj-mcr8-4c3g](https://github.com/heymrun/heym/security/advisories/GHSA-73pj-mcr8-4c3g));
  closed the same day without being accepted
- **Detail:** withheld, including the part of the project it is in. A declined private report is
  not permission to publish one, so this stays as it is.

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
