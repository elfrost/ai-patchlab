---
layout: default
title: "Continuum-AI-Corp/OrcaRouter-Lite: security scan"
description: "Security scan of Continuum-AI-Corp/OrcaRouter-Lite: 84 findings at medium+, 1 real (Medium) found by hand, withheld here while a private report is delivered. All 82 tool findings dismissed. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-27
---

# Continuum-AI-Corp/OrcaRouter-Lite — security scan

**Repository:** [Continuum-AI-Corp/OrcaRouter-Lite](https://github.com/Continuum-AI-Corp/OrcaRouter-Lite)
**Commit scanned:** `5d34160` (`main`)
**Scan date:** 2026-11-27
**Disclosure status:** one Medium finding is being reported privately. The project's
`SECURITY.md` asks for reports through GitHub private vulnerability reporting and rules out
public issues. On the scan day that feature was switched off on the repository: the API reported
it disabled, and a report submission was refused with HTTP 403. So the report goes to the
organisation's published contact address. This page does not describe the finding, or the part
of the project it is in, until a fix ships.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 41 |
| Medium | 40 |
| Low | 0 |
| Info | 2 |

**Total findings:** 84 at `--min-severity medium`. One is real after curation, and it was found by
reading the code; none of the 82 tool findings was real. The 2 info rows are coverage meta
findings.

OrcaRouter Lite is a self-hosted, OpenAI-compatible LLM router (3.3k★, MIT, published by
Continuum AI). It sits between coding tools and model providers, holds the user's provider keys
(bring your own key), picks a model per request, and also speaks the Anthropic, Responses and
Gemini APIs. It ships as a pip package, a Docker image and a desktop app (Tauri, Rust) that wires
coding agents such as Claude Code, Codex and Gemini CLI to it. In the 60 days before the scan,
pull requests were merged from 3 people and issues closed from 6. The code is about 49,000 lines
of Python plus the Rust desktop shell.

**Scope of this write-up.** Every tool finding was checked at its call site. The hand review ran
as three parallel slices over the API, the desktop app and the outbound request paths, and all
three completed. The finding was confirmed by tracing its code path end to end in the source; it
was not run end to end. Read the
result as "the tools' 82 findings are accounted for, plus one finding from hand review", not as
a full audit.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `ran` | Ran without reporting a coverage problem. |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep reported 13 errors, none of them rule timeouts. One
JavaScript file (`desktop/ui/panel-lib.js`, 687 lines) failed to parse; it was read by hand. The
other 12 were partial parses of two GitHub workflows, the Dockerfile and a demo shell script. The
dependency tools disagree on nothing: pip-audit read the 89 hash-pinned entries of
`requirements.lock` and found 0 advisories, and Trivy read the desktop app's `Cargo.lock`. The
desktop `package-lock.json` holds only the Tauri CLI, a development tool, which is why no
dependency tool reports anything for it.

## Top findings

### 1. One Medium finding, reported privately

- **Tool:** manual review; no rule in the four tools covers it
- **Confidence:** high; the code path was traced end to end in the source, and the project's own
  code holds a sibling that does the same job correctly
- **Status:** report drafted on 2026-11-27 for the organisation's published contact address,
  because GitHub private vulnerability reporting is switched off
- **Detail:** withheld, including the part of the project it is in, until the maintainers ship a
  fix. This page will be updated then.

## Why the rest were dismissed

All 82 tool findings are accounted for below. The `confirmed-real` row is the hand-found item.
The `by-design` row includes 31 action-tag findings and one Low hand-review note that went into
the private report as a secondary item.

| Reason | Findings |
| --- | ---: |
| `by-design` | 32 |
| `test-or-fixture-path` | 22 |
| `placeholder-secret` | 14 |
| `sql-identifier-fp` | 3 |
| `active-harm-fp` | 3 |
| `not-reachable` | 3 |
| `sample-or-demo` | 3 |
| `domain-noun-collision` | 1 |
| `dependency-currency` | 1 |
| `credited-defense` | 1 |
| `confirmed-real` (manual review) | 1 |

The largest family is the 31 GitHub Actions pinned by tag rather than by commit. That is
supply-chain hardening, and the release workflow already signs every image with cosign through
GitHub's OIDC identity and attaches SLSA provenance and an SBOM. Next come 37 Gitleaks hits, and
none is a secret: key-shaped strings in tests, including Rust test vectors that check that a
key-shaped value is *refused*, and curl examples in eleven README translations. The one Critical
is a `zip` crate advisory in the desktop app's lockfile. Only the updater plugin pulls that crate
in, and it opens an archive only after checking the update's signature against a public key
built into the app. The "image runs as root" finding is answered in the Dockerfile itself: the
entrypoint starts as root only to hand a mounted volume to the `orca` user, then drops to it.

## Patterns observed

**A SECURITY.md written as a specification.** Most security policies say where to send a
report. This one also lists, claim by claim, what each key may do, where secrets live and with
which file mode, what the installer and updater touch, and how a release can be verified. Every
claim can be checked against the code, so it works as a test oracle. The review was organised
around it. These claims held:
- **Scoped keys.** A key handed to a coding agent is refused everywhere except the model
  endpoints, checked across all 55 routes. Agent and app key names are reserved, so a dashboard
  key cannot mint one. Path tricks such as `..`, double slashes and case changes fail closed.
- **Credentials go where they belong.** A request body is validated against a fixed schema
  before anything reaches LiteLLM. So a caller cannot add `api_base`, `base_url`, `extra_headers`
  or `api_key` to steer a stored provider key to another host. Provider key checks use a fixed
  URL per provider and do not follow redirects.
- **Files.** Configuration writes go through `mkstemp`, `chmod` and `os.replace`, and backups and
  key files are `0600` inside `0700` folders. Every "insecure file permissions" hit Semgrep raised
  is one of those `0o700` calls.

**Supply chain treated as a threat, with dates.** The policy names the two backdoored LiteLLM
releases of 2026 and answers them. LiteLLM is pinned to an exact version, a test fails if the pin
loosens or lands on a known-compromised release, and the Docker image installs with
`pip install --require-hashes`. The pip-audit run read those pins and found nothing to report.

**A documented channel that is switched off.** The policy sends reporters to GitHub
private vulnerability reporting, and the repository has it disabled. That is a common drift in
this series: the policy file is written once, and the repository setting is a separate switch.
The setting is the one that decides whether a report can arrive.

## Notes on the tool

- **A policy is a checklist the tools cannot read.** None of the four tools can test a claim
  written in prose, and the most useful review input here was the project's own `SECURITY.md`.
  Backlog: extract the testable claims from a target's security policy into the curation
  checklist before the hand review starts.
- **Trivy is silent on a lockfile with only development dependencies.** That silence looks the
  same as a lockfile it never read. It was resolved by hand here, by opening the lockfile; the
  coverage block could say it directly.

## Disclosure timeline

- 2026-11-27 — scan run at `5d34160` (`main`)
- 2026-11-27 — finding verified by code reading; GitHub private vulnerability reporting refused
  the report (disabled on the repository), so it was drafted for the organisation's contact
  address
- 2026-11-27 — this page published, with the finding withheld

## Reproduce

```bash
git clone https://github.com/Continuum-AI-Corp/OrcaRouter-Lite /tmp/scan-target
git -C /tmp/scan-target checkout 5d34160
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/continuum-ai-corp-orcarouter-lite --min-severity medium
```

---

## More from this series

- **Previous scan:** [converge-ai-labs/agent-foundation](converge-ai-labs-agent-foundation.html) — 2026-11-26, 0 real
- [Every scan in the series]({{ '/' | relative_url }}) — 124 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 31 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
