---
layout: default
title: "patrickchugh/terravision: security scan"
description: "Security scan of patrickchugh/terravision: 384 findings at medium+, 2 real (Medium) found by hand and reported privately through GitHub, withheld here until a fix ships. All 381 tool findings dismissed, 360 of them rules applied to test-fixture Terraform. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-19
---

# patrickchugh/terravision — security scan

**Repository:** [patrickchugh/terravision](https://github.com/patrickchugh/terravision)
**Commit scanned:** `c49bba6` (`main`, v0.56.3)
**Scan date:** 2026-11-19
**Disclosure status:** reported privately. Two Medium-severity findings were filed through GitHub
private vulnerability reporting on 2026-11-19, one report each, as the project's `SECURITY.md` asks
([GHSA-gr2g-28fj-fgmq](https://github.com/patrickchugh/terravision/security/advisories/GHSA-gr2g-28fj-fgmq)
and
[GHSA-24gx-f2fh-749r](https://github.com/patrickchugh/terravision/security/advisories/GHSA-24gx-f2fh-749r),
in triage). This page does not describe them, or the part of the project they are in, until a fix
ships.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 28 |
| High | 135 |
| Medium | 218 |
| Low | 0 |
| Info | 3 |

**Total findings:** 384 at `--min-severity medium` (2 real after curation, both found by reading the
code; none of the 381 tool findings was real; the 3 info rows are coverage meta findings)

TerraVision draws cloud architecture diagrams for AWS, Azure and GCP from Terraform code, plan files
or a JSON graph, and goes the other way too: an MCP server lets an AI app turn a diagram into
Terraform (1.7k★, AGPL-3.0). It ships as a CLI, a Docker image and plugins for several coding agents.
It is active: 56 pull requests merged from 3 authors and 12 issues closed from 5 authors in the 60
days before the scan, with releases on each of the two days before it. Its `SECURITY.md` prefers
private vulnerability reporting, gives an email fallback, rules out public issues, and promises an
acknowledgement within five business days and an assessment within fourteen. It also does something
rare: it publishes a security model that says what the tool does, what counts as a vulnerability
and what does not.

**Scope of this write-up.** Every tool finding was checked at its call site. The hand review
followed the in-scope list of `SECURITY.md` in three slices. One of them covered remote module
download and caching, and the data the optional AI backend integration sends to a model. An automated safety
check stopped it partway through, it was not resumed, and those areas are not covered here. Read
the result as "the tools' 381 findings are accounted for, plus two findings from hand review", not
as a full review of the tool.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | A shipped lockfile was not covered by the dependency scan |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no, but the gaps are small. Semgrep's three errors are partial parses of
files that are not Python: the `Dockerfile` and two demo HTML pages under `docs/`. Every Python file
was analysed, with no rule timeouts. pip-audit resolved `requirements.txt` (26 packages, no
advisories) but does not read `poetry.lock`. Trivy read both, and reported no advisories in either,
so both install paths are covered.

## Top findings

### 1. Two Medium-severity findings, reported privately

- **Tool:** manual review; no rule in the four tools covers them
- **Confidence:** high; each was verified on the shipped code with inert markers before filing
- **Status:** reported through GitHub private vulnerability reporting on 2026-11-19, one report per
  finding
  ([GHSA-gr2g-28fj-fgmq](https://github.com/patrickchugh/terravision/security/advisories/GHSA-gr2g-28fj-fgmq),
  [GHSA-24gx-f2fh-749r](https://github.com/patrickchugh/terravision/security/advisories/GHSA-24gx-f2fh-749r)),
  in triage
- **Detail:** withheld, including the part of the project they are in, until the maintainer ships a
  fix. This page will be updated then.

## Why the rest were dismissed

All 381 tool findings are accounted for below. The scanner dropped 151 more below the
`--min-severity` floor, and the 3 info rows are the coverage meta findings above. The
`confirmed-real` row is the two hand-found items, recorded so that the corpus counts them.

| Reason | Findings |
| --- | ---: |
| `test-or-fixture-path` | 360 |
| `by-design` | 11 |
| `not-reachable` | 8 |
| `credited-defense` | 2 |
| `below-min-severity` (scanner) | 151 |
| `confirmed-real` (manual review) | 2 |

The largest family is `test-or-fixture-path` (360), and 356 of those rows are Trivy. They are
infrastructure rules (VPC flow logs, EKS control-plane logging, S3 public-access blocks, Shielded
VM settings) applied to the Terraform under `tests/fixtures/`: the inputs a diagram tool draws in
its own tests. Twenty-one came from remote modules that those fixtures reference, which Trivy
fetched and evaluated. All 28 criticals are in this group. The other four are dummy database
passwords in the same fixtures. The 11 `by-design` rows are dynamic imports and `globals()` lookups
keyed by a provider already limited to `aws`, `azure` or `gcp`, so no input chooses the module. The
8 `not-reachable` rows are in maintainer scripts under `scripts/`, which are not part of the
published package.

## Patterns observed

**A security model you can test against.** Most security policies give a mailbox. This one also
gives a list of what the tool does (runs locally, downloads what your code references, runs local
tools, serves MCP over stdio only), what is in scope, and what is not. That turns "is this a bug or
by design?", the question most reports stall on, into a lookup. Both findings were checked against
it before filing, and its out-of-scope list retired at least one lead before anything was written:
Terraform running code while planning untrusted Terraform is documented as the same as running it.

**The scanner mostly scanned the test corpus.** For a tool whose input is other people's Terraform,
an infrastructure scanner's output describes the inputs, not the product: 356 of the 384 findings,
and every critical, are about fixtures. The one Semgrep high that pointed at the product, an archive
extraction, turned out to be some of the most carefully defended code in the series.

**What the project does well.**
- Module archives are checked member by member before extraction: each resolved path must stay
  inside the destination (`realpath` plus `commonpath`), entry count and uncompressed size are
  capped against archive bombs, tar extraction uses `filter="data"`, and on a Python without that
  filter the tool refuses rather than falling back (`modules/gitlibs.py`).
- Every Terraform call is an argument list with no shell, stdin closed and `TF_INPUT=false`.
- The Docker image verifies HashiCorp downloads against a pinned release-signing key fingerprint.
  Gitleaks flagged that fingerprint as a secret; it is the build's trust anchor.
- Dynamic imports are keyed by an allowlisted provider, and the maintainer scripts that fetch icon
  sources stay out of the published package.

## Notes on the tool

- **Trivy's misconfiguration findings lost their file path.** A Terraform address such as
  `aws_eks_cluster.main` ends in `.main`, so the adapter took it for a file name and stored it as
  the finding's file. Path rules, including `--ignore-samples` and the `tests/` candidate-FP flag,
  never saw that 356 findings lived under `tests/fixtures/`. This is now on the AI PatchLab backlog.
- **Trivy evaluated remote modules.** Twenty-one findings came from modules the fixtures reference
  by Git URL or registry name. A local-first scan should not be fetching third-party code it was
  never pointed at, so this is on the backlog too.

## Disclosure timeline

- 2026-11-19 — scan run at `c49bba6` (`main`, v0.56.3)
- 2026-11-19 — two findings verified and reported privately through GitHub private vulnerability
  reporting, one report each
  ([GHSA-gr2g-28fj-fgmq](https://github.com/patrickchugh/terravision/security/advisories/GHSA-gr2g-28fj-fgmq),
  [GHSA-24gx-f2fh-749r](https://github.com/patrickchugh/terravision/security/advisories/GHSA-24gx-f2fh-749r))
- 2026-11-19 — this page published, with both findings withheld

## Reproduce

```bash
git clone https://github.com/patrickchugh/terravision /tmp/scan-target
git -C /tmp/scan-target checkout c49bba6
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/patrickchugh-terravision --min-severity medium --ignore-samples
```

---

## More from this series

- **Previous scan:** [heymrun/heym](heymrun-heym.html) — 2026-11-18, 1 real
- [Every scan in the series]({{ '/' | relative_url }}) — 120 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 30 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
