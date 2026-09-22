---
layout: default
title: "overwirehq/claude-code-telegram: security scan"
date: 2026-09-22
---

# overwirehq/claude-code-telegram - security scan

**Repository:** [overwirehq/claude-code-telegram](https://github.com/overwirehq/claude-code-telegram)
**Commit scanned:** `5016aee` (v1.8.0)
**Scan date:** 2026-09-22
**Disclosure status:** post-only — nothing first-party survived curation. The one actionable item is dependency currency in a transitive-dependency lockfile, not a code defect. This repository has a real SECURITY.md and private vulnerability reporting enabled; no advisory was filed because there is no first-party vulnerability to file.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 21 |
| Medium | 30 |
| Low | 0 |
| Info | 2 |

**Total findings:** 54 at `--min-severity medium` (0 first-party defects after curation; one dependency-currency finding composed of the reachable transitive CVEs)

This is a bot that, by design, runs Claude Code with file and Bash tools on a
host machine on behalf of authorised Telegram users. The whole security surface
is therefore *the boundary around that execution* — the approved-directory
sandbox, the user allowlist, the tool-permission callback. That is exactly where
I spent the scan, and it is the part the maintainers have built and **documented**
with more care than almost anything else in this series.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `ran` | Ran without reporting a coverage problem. |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | A shipped lockfile was not covered by the dependency scan |
| `ai-security-review` | `not_run` | disabled by default (ADR-010) |

**Coverage complete:** no — and it is the [same dependency blind spot](harnessrouter-harnessrouter.html)
as yesterday, reached by a different route. `dependency-scan` (pip-audit) found
the root `pyproject.toml`, but this project declares `dynamic = ["dependencies"]`
with the real list under `[tool.poetry.dependencies]`, so pip-audit resolved
**no dependencies** and returned an empty report — which reads identically to
"clean". Trivy reads `poetry.lock` directly, so it saw the pinned graph and
produced every dependency finding below. The lesson stands from the HarnessRouter
scan: when two dependency tools disagree about whether there is anything to scan,
the one that found nothing is usually the one that was pointed at the wrong file.
Everything of dependency interest here came from Trivy.

## Top findings

There is no first-party finding to lead with — the honest headline is that the
execution boundary held up. The one actionable item is dependency currency, and
it is only legible once you split it by reachability.

### 1. Transitive lockfile currency — split cleanly by what the default install actually runs

- **File:** `poetry.lock`
- **Tool:** trivy
- **Confidence:** high that the CVEs are real; the reachability split is the finding
- **Why it matters:** 30 advisories land in `poetry.lock`, and they divide into two
  groups that deserve very different treatment:
  - **Opt-in only (17), not reachable on a default install.** `starlette` (6) and
    `python-multipart` (3) only execute if the FastAPI webhook server is turned on
    — `ENABLE_API_SERVER` is `False` by default. `pyjwt`/`python-pyjwt` (5) matter
    only on the token-auth path — `ENABLE_TOKEN_AUTH` is `False` by default, **and**
    the project's own SECURITY.md documents token auth as incomplete and unusable
    end to end (backed by `InMemoryTokenStorage`, tracked in
    [#58](https://github.com/overwirehq/claude-code-telegram/issues/58)). The MCP
    Python SDK highs (3) need MCP enabled. None of these is on the default
    (long-polling, `ALLOWED_USERS`-gated) deployment.
  - **Unconditionally installed (13), a genuine currency gap.** `anyio` (incl. the
    critical IDNA/TLS host-encoding advisory), the `cryptography` + bundled OpenSSL
    cluster, `urllib3`, `idna`, `requests`, `pydantic-settings`, and `python-dotenv`
    ship on every install. These are the ones to refresh.
- **Recommendation:** Refresh `poetry.lock`. The direct dependencies are current
  (`python-telegram-bot ^22.6`); the drift is entirely in transitive pins, which
  is the specific thing the existing `.github/dependabot.yml` will **not** fix on
  its own (see *Notes on the tool*).

## Why the rest were dismissed

Of 54 findings at `medium+`, zero were first-party defects. The distribution:

| Reason | Findings |
| --- | ---: |
| `not-reachable` | 17 |
| `by-design` | 17 |
| `confirmed-real` (dependency currency) | 13 |
| `sql-identifier-fp` | 2 |
| `test-or-fixture-path` | 2 |
| `placeholder-secret` | 1 |

The largest first-party family is `by-design` (17), and it is worth one sentence
because it is *well* by-design: 16 are `github-actions-mutable-action-tag` (SHA-pin
hardening on CI action refs, a best-practice nudge), and the 1 remaining is a
`pull_request_target` checkout that the maintainers have wrapped in a 40-line
threat-model header — the workflow runs with repository secrets against untrusted
PR code precisely *because* `pull_request_target` sources the workflow from the
default branch (a PR cannot edit it to reach the secrets), and the tool allowlist
handed to the review action is read-only plus `gh pr comment`, no Write/Edit/Bash,
with cloud and Actions secrets scrubbed from subprocess environments. They name
the residual themselves: "worst case is a prompt-injected review comment." That is
[the trigger deciding the severity](lightseekorg-tokenspeed.html), reasoned out in
the file. The two `sqlalchemy-execute-raw-query` highs are the
[recurring identifier false positive](aurelio-labs-semantic-router.html): only a
generated run of `?` placeholders is interpolated into the query string
(`",".join("?" for _ in slugs)`), and every value is bound through
`conn.execute(query, params)`. The three gitleaks hits are a literal
`your-api-secret` placeholder in `docs/setup.md` and two fake tokens in a test
that asserts the project's `_redact_secrets()` helper scrubs them — a
[credited defence](realiti4-claude-swap.html), not a leak.

## Patterns observed

The story here is not a bug; it is what precise security documentation looks like,
and it is rare enough to be worth describing.

This project's real security boundary is the `can_use_tool` callback in
`src/claude/sdk_integration.py` — the thing that stops Claude, when steered
off-course by content it reads mid-task, from writing or reading outside the
approved directory. The interesting part is not that the callback exists; it is
that the maintainers **know and state exactly what it does and does not cover.**
The docs scope path validation to precisely six tools — `Read`, `Write`, `Edit`,
`MultiEdit`, `NotebookEdit`, `NotebookRead` — and no others. Tools like `Grep`,
`Glob`, and `LS` are in the default allow-list and are *not* path-validated by the
callback; agentic mode relies on the OS sandbox for those instead. A scanner-style
reading of that gap ("Read is guarded but Grep is not, so the boundary is
incomplete") is the kind of plausible-but-wrong finding this whole site exists to
resist — because the boundary is [advertised, not
accidental](tracecathq-tracecat.html). The project's `ROADMAP-v2.md` goes further
and records that the SDK itself emits a `CanUseToolShadowedWarning` at connect time
naming every tool the callback will never see, and files it as a tracking item
(#221). When the code and the docs agree on the boundary *and* the docs name the
gap, the gap is a design decision, not a vulnerability.

Two more things earn credit. The `can_use_tool` wiring carries a comment trail
documenting [issue #219](https://github.com/overwirehq/claude-code-telegram/issues/219):
guarded tools are deliberately *stripped from* the SDK's `allowed_tools` list,
because a tool pre-approved by the CLI's permission engine never produces a
`can_use_tool` control request — so leaving them in the allow-list would render
the checks silently inert. They also disable `autoAllowBashIfSandboxed` whenever
the boundary checks are meant to run, because auto-approved sandboxed Bash is a
second bypass of the same control request. That is a maintainer who has actually
traced how the framework resolves permissions, rather than trusting that a
config-file allow-list is an enforcement boundary. It is not — and the code says
so, out loud.

When a project is built and documented this carefully, the finding moves to the
dependency manifest. That is where it moved.

## Notes on the tool

Two backlog items, both already known and both reconfirmed here:

1. **`dependency-scan` reads `pyproject.toml` but not the Poetry lock when
   dependencies are `dynamic`.** pip-audit resolved zero dependencies from a
   `[project]` table declaring `dynamic = ["dependencies"]`, and returned an empty
   report that would render as a clean Python surface. Trivy's `poetry.lock` read
   is what carried the run. `scan_dependency` should treat a `dynamic`-dependency
   `pyproject.toml` with a sibling `poetry.lock` as a lockfile scan, or at minimum
   emit a louder meta-finding when it resolves nothing but Trivy reports pip
   advisories. This is the same underlying gap as the
   [HarnessRouter monorepo case](harnessrouter-harnessrouter.html), reached by a
   different manifest shape.

2. **The reachability split is manual.** The 17 opt-in-only CVEs are dismissible
   only because I read the defaults (`ENABLE_API_SERVER`, `ENABLE_TOKEN_AUTH`,
   `enable_mcp` all `False`) and the SECURITY.md note that token auth is
   non-functional. The scanner reports all 30 at face value. A "feature-gated
   dependency" signal — CVEs whose reachable surface is behind a default-off flag —
   would be a genuinely useful enrichment, but it needs per-project config
   knowledge the current rules do not have.

The dependency finding itself also has a coverage nuance worth stating plainly:
this repository **does** run Dependabot (`.github/dependabot.yml`), but it is
configured for *version* updates — three named direct dependencies weekly, the
rest grouped minor/patch monthly. Transitive-only CVEs like these are surfaced by
Dependabot *security* updates, a separate repository-level toggle, not by version
updates. So the lockfile can carry published transitive CVEs despite a Dependabot
config being present. That is not a criticism of the config; it is the reason the
finding exists at all.

## Disclosure timeline

- 2026-09-22 — scan run; curated to zero first-party defects and one
  dependency-currency finding
- 2026-09-22 — public post (this page). No advisory filed: there is no first-party
  vulnerability, and dependency currency with a clean reachability split is not an
  advisory-shaped item. A short courtesy note via the repository's enabled private
  vulnerability reporting would be reasonable if the maintainer wants the transitive
  refresh on their radar, since Dependabot version-updates will not raise it.

## Reproduce

```bash
git clone https://github.com/overwirehq/claude-code-telegram /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/overwirehq-claude-code-telegram --min-severity medium
```
