---
layout: default
title: "amd/gaia: security scan"
description: "Security scan of amd/gaia: 1,188 findings at medium+, 1 real (High) found by hand and reported privately through GitHub private vulnerability reporting, detail withheld. All 1,186 tool findings dismissed. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-28
---

# amd/gaia — security scan

**Repository:** [amd/gaia](https://github.com/amd/gaia)
**Commit scanned:** `34065f4` (`main`)
**Scan date:** 2026-11-28
**Disclosure status:** one High finding was reported privately on 2026-11-28 through GitHub
private vulnerability reporting, the channel the project's `SECURITY.md` asks for. The same policy
rules out public issues. This page does not describe the finding, or the part of the project it
is in, until a fix ships.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 266 |
| Medium | 918 |
| Low | 0 |
| Info | 2 |

**Total findings:** 1,188 at `--min-severity medium`. One is real after curation, and it was
found by reading the code; none of the 1,186 tool findings was real. The 2 info rows are coverage
meta findings.

GAIA is AMD's open-source framework for building AI agents that run on the user's own PC (1.6k★,
MIT). It ships a terminal UI written in Go, an Electron desktop app (the Agent UI), a Python agent
core with tools for files, shell, browser and email, connectors to outside services, an agent and
skill hub, and several local HTTP servers: an OpenAI-compatible API, a generic agent server, an
MCP bridge and a background daemon. Pull requests were merged from 5 people and issues closed from
6 in the 60 days before the scan. The Python source alone is about 396,000 lines, plus TypeScript,
Go and C++.

**Scope of this write-up.** Every tool finding was checked at its call site or by family. The hand
review ran as three parallel slices, and all three completed. The slices covered the loopback HTTP
servers, the Agent UI backend, and the boundaries around the agent's tools. The real finding was
confirmed by running the code that carries it in a sandbox, with a harmless marker and a control
run. Read the result as "the tools' 1,186 findings are accounted for, plus one finding from hand
review", not as a full audit of a codebase this size.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `ran` | Ran without reporting a coverage problem. |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Here is what that means.

- **Semgrep errors.** Semgrep reported 573 errors.
  - **Rule timeouts (68).** These include the subprocess-injection rules on the agent base class
    and the shell tool, and taint rules on `cli.py` and several large Agent UI components.
  - **Python files Semgrep could not parse (21).** Several of them are server and client modules,
    so no rule ran on those files at all.
  - **Workflow files (483).** 435 partial parses and 48 internal matching errors, almost all in
    GitHub workflow YAML.
- **Python dependencies: not audited.** The coverage row says `dependency-scan` ran, but no tool
  read them. They are declared only as version floors in `setup.py`, with no lockfile and no
  requirements file. pip-audit was pointed at `pyproject.toml`, which here holds only tool
  settings, so its empty result says nothing about them.
- **What Trivy read.** The JavaScript and Go lockfiles of the website, the docs proxy, the web UI,
  the agent-hub worker and the terminal UI.

## Top findings

### 1. One High finding, reported privately

- **Tool:** manual review; no rule in the four tools covers it
- **Confidence:** high. The code path was traced end to end in the source, then run in a sandbox:
  a marker appeared with the trigger present and did not appear in the control run.
- **Status:** filed through GitHub private vulnerability reporting on 2026-11-28, in triage
- **Detail:** withheld, including the part of the project it is in, until the maintainers ship a
  fix. This page will be updated then.

## Why the rest were dismissed

All 1,186 tool findings are accounted for below. The `confirmed-real` row is the hand-found item.

| Reason | Findings |
| --- | ---: |
| `by-design` | 694 |
| `not-reachable` | 271 |
| `sql-identifier-fp` | 65 |
| `test-or-fixture-path` | 58 |
| `product-surface` | 36 |
| `dependency-currency` | 25 |
| `domain-noun-collision` | 22 |
| `active-harm-fp` | 6 |
| `credited-defense` | 5 |
| `vendored-code` | 2 |
| `placeholder-secret` | 2 |
| `confirmed-real` (manual review) | 1 |

**Mostly CI configuration.** 538 of the 1,188 findings are GitHub Actions pinned by tag rather
than by commit, which is supply-chain hardening. Another 52 are workflow rules. None of the 23
"shell injection" hits interpolates an attacker-controlled event field: each one is a
maintainer-set `workflow_dispatch` or `workflow_call` input.

**Bidirectional text.** 112 "bidirectional characters" hits are the Arabic translation of the
Agent UI and its right-to-left tests.

**The two Criticals.**
- **Astro, AVIF image optimization:** in the marketing website, which Astro builds as a static
  site, so image optimization only ever runs at build time on the project's own images.
- **proxy-addr:** in a small Express proxy in front of the hosted docs. The advisory concerns
  trusted-subnet lists, and that proxy trusts a hop count instead. That proxy fronts a live
  service, so it was not examined further.

**Gitleaks.** All 59 hits are test vectors: for the project's own secret-detection code, fake
`ghp_GAIAEVALfake…` tokens in evaluation scenarios, a vendored key-name table, and an empty
`HF_TOKEN=` in `.env.example`.

## Patterns observed

**One policy module for every loopback server, written with the browser as the attacker.**
`src/gaia/api/local_http.py` opens by saying that "loopback is not a boundary": the threat is a
page in the user's own browser reaching `http://localhost:<port>`. Every server inherits the same
rules:
- A state-changing request from a foreign Origin, including `null`, is refused with a 403 before
  any handler runs.
- Wildcard CORS together with credentials is never configured, and a test enforces that.
- A bind beyond loopback without an API key is refused at startup.
- The agent relay stays disabled until a key exists.

The Agent UI adds three more layers on top:
- a Host allowlist against DNS rebinding;
- an `X-Gaia-UI` header on every state-changing request;
- a per-install token, redeemed once from a launch code into an HttpOnly, SameSite=Strict cookie.

The background daemon requires a 256-bit bearer token on every route. The OAuth callback server
uses PKCE, compares `state` in constant time and lives for at most 15 minutes.

**Windows paths treated as a separate threat model.** The path code handles:
- `\\?\` prefixes, admin and UNC shares;
- 8.3 short names;
- trailing dots and spaces;
- NTFS alternate data streams.

Folder checks compare with a separator appended, so `proj-evil` does not pass as `proj`. Archive
extraction checks every entry before writing anything, refuses links that leave the destination,
caps sizes, and never calls `extractall`. Hub, skill and import downloads all go through that one
function.

**Messaging bots that refuse to run open.** The Telegram and Slack bots refuse to start with an
empty allowlist, and they key it on numeric user ids, not on usernames that can be renamed or
re-registered. Discord uses a short-lived pairing code that changes after five wrong guesses.

**Hardening notes, no exploit today.**
- **Host check.** The Agent UI checks the `Host` header. `gaia api`, the generic agent server and
  the MCP bridge do not. Their state-changing requests are still refused on Origin, and none of
  their GET routes returns more than model and tool listings. So a DNS-rebinding page can read only
  those listings today, but any future GET route that returns data would be readable too.
- **Wildcard origins.** Setting `GAIA_API_CORS_ORIGINS='*'` also turns off the Origin refusal on
  those servers. The docs describe `*` only as dropping credentials. They should add a sentence
  saying it opens the unauthenticated API to any website.

**Self-review in CI.** The project runs a scheduled Semgrep plus model-assisted security audit,
and a gate that rejects any `# nosec` / `# noqa: S` suppression not justified in
`.security-suppressions.json`. The finding above came from reading how two components work
together. That is the kind of path a per-file rule does not follow.

## Notes on the tool

- **"ran" is not "read".** The dependency row says `ran` because pip-audit ran. Here it read a
  `pyproject.toml` with no dependencies, while the project's real dependency list sits in
  `setup.py`. The coverage manifest should mark this case as partial: pip-audit given a manifest
  that declares nothing, while a `setup.py` with `install_requires` exists. Today it reads
  identically to "no vulnerable Python dependency".
- **Semgrep parse failures on modern Python.** 21 valid Python files produced "Other syntax
  error", which means no rule ran on them. The coverage block reports the error count, but not
  which first-party files came out entirely unscanned. Listing those files beside the rule
  timeouts would make the gap visible without reading the raw JSON.
- **Volume.** 538 action-tag findings in one repository drown the rest of the report. The rule
  is right, but at this scale it belongs in a single collapsed row.

## Disclosure timeline

- 2026-11-28 — scan run and hand review
- 2026-11-28 — finding reported privately through GitHub private vulnerability reporting
- 2026-11-28 — public post (this page), detail withheld
