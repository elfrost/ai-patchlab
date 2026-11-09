---
layout: default
title: "eugeniughelbur/obsidian-second-brain: security scan"
description: "Security scan of eugeniughelbur/obsidian-second-brain: 30 findings at medium+, 2 real (Medium + Low), both fixed by the maintainer the day after a private report. The background agent's tool list restricted nothing under --dangerously-skip-permissions. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-10-24
---

# eugeniughelbur/obsidian-second-brain — security scan

**Repository:** [eugeniughelbur/obsidian-second-brain](https://github.com/eugeniughelbur/obsidian-second-brain)
**Commit scanned:** `f11ffb37` (`main`)
**Scan date:** 2026-10-24
**Disclosure status:** ✅ **resolved** — two findings (one Medium, one Low) reported privately by
email on 2026-10-26, as the project's `SECURITY.md` asks, and both fixed by the maintainer the
next day in [#373](https://github.com/eugeniughelbur/obsidian-second-brain/pull/373). The fix is on
`main` but not yet in a tagged release (latest: `v0.20.0`, 2026-10-25). If you turned on the opt-in
background agent, check that your copy of `hooks/obsidian-bg-agent.sh` passes `--tools`, or leave
the agent off until the next release.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 6 |
| Medium | 19 |
| Low | 0 |
| Info | 3 |

**Total findings:** 30 at `--min-severity medium` (2 real after curation, both found by reading the
code rather than by a tool; the 3 info rows are coverage meta findings)

obsidian-second-brain gives Claude Code, Codex and other coding agents a persistent memory, stored as
plain markdown in an Obsidian vault (4.9k★ at scan time, MIT). It ships as a Claude Code plugin with
nearly fifty commands, a stdio MCP server, a key-less research toolkit run through `uv`, a Telegram
bot, an Obsidian plugin, and an opt-in background agent that runs after Claude Code compacts a
conversation. It is one of the most active projects in the series: 58 pull requests merged from 19
human authors and 59 issues closed in the 60 days before the scan. Its `SECURITY.md` is a real one.
It lists its own scope (hooks, API keys in logs or notes, prompt injection that exfiltrates vault
content), gives an email address and rules out public issues. GitHub private vulnerability
reporting is disabled on the repository, so email was the channel.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | A shipped lockfile was not covered by the dependency scan |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep scanned 289 paths and could not parse two shell scripts:
`adapters/lib.sh`, rejected from its first line, and `hooks/validate-ai-first.sh`, at a `case` arm
on line 238. No rule ran on the first, and only part of the second was covered. pip-audit did not
audit `uv.lock`; Trivy read it, and its 11 advisories are the dependency rows below. Neither gap
touches the two findings, which no rule in any of the four tools could have expressed.

## Top findings

Both items came from reading the code against the scope the project's `SECURITY.md` declares. Both
were fixed upstream in one pull request, each with a test.

### 1. The background agent's tool list restricted nothing (Medium, fixed)

- **File:** `hooks/obsidian-bg-agent.sh:231-233` (the claim is in the comment at 226-230 and in
  `README.md:590`)
- **Tool:** manual review; no rule covers it
- **Confidence:** high, verified with a two-arm differential
- **Why it matters:** the background agent runs headless with `--dangerously-skip-permissions`, on
  a compaction summary that can carry text from the open web. The comment above the command says
  *"Filesystem only: no Bash, no network"*, and the README tells users it *"cannot run shell
  commands or reach the network"*. The tool list was passed with `--allowedTools`, which only
  pre-approves the tools it names. Under the bypass flag every tool is already approved, so the
  list removed nothing. `--tools` is the flag that decides which tools exist in the session.
- **Recommendation:** pass the list with `--tools`. Adopted in #373, with a test on the command line.

The check was simple. The hook's exact flags, a harmless probe, an empty directory, Claude Code
2.1.310. As shipped, the session offered 29 tools, shell and web fetch among them. With
`--tools "Read,Write,Edit,Glob,Grep"`, it offered exactly those five and could still write and read
back a note, which is all the agent needs.

The preconditions, stated honestly. The agent is opt-in. However, the plugin registers the hook
itself, so for a normal install `OBSIDIAN_BG_AGENT_ENABLED=1` is the only step, and README line 590
is the sentence a user reads before taking it. Exploitation also needs an injection that survives
into the compaction summary and that the headless model then follows. That threat is not mine: the
hook's own comment names it (*"a page read by /research, a transcript, a cloned repo's README"*).

### 2. A YouTube API key in error output (Low, fixed)

- **File:** `scripts/research/lib/youtube.py:97` and `:133`
- **Tool:** manual review
- **Confidence:** high, verified with a fake key against the real API endpoint
- **Why it matters:** both error handlers printed the `HttpError` text from the Google API client,
  and that text includes the request URI, which carries `key=<YOUTUBE_API_KEY>`. A valid key reaches
  these paths routinely: comments disabled on a video, quota used up, API not enabled. The output
  goes to stdout, so into the calling agent's transcript, and on the Telegram path into the chat
  when a run fails.
- **Recommendation:** print the status and reason only. Adopted in #373, with a test.

## Why the rest were dismissed

All 27 non-meta tool findings are accounted for below. The 3 info rows are the coverage meta
findings above, and the 2 `confirmed-real` rows are the hand-found items, recorded so that the
corpus counts them. The scanner dropped 3 findings below the `--min-severity` floor.

| Reason | Findings |
| --- | ---: |
| `by-design` | 11 |
| `not-reachable` | 10 |
| `dependency-currency` | 6 |
| `below-min-severity` (scanner) | 3 |
| `confirmed-real` (manual review) | 2 |

The largest family is `github-actions-mutable-action-tag`, 9 of the 11 `by-design` rows. They are
actions referenced by tag in `ci.yml` and `scorecard.yml`: SHA-pinning is hardening, and Dependabot
already watches the workflows. The other two are SHA-1 used as cache keys. The `not-reachable` rows
are four `dynamic-urllib-use-detected` hits that build the embedding endpoint from operator
configuration (`OLLAMA_URL`, localhost by default) or a literal, a RegExp compiled from a constant,
and five lockfile advisories with no path in: `anyio` (no shipped script is async) and `pyasn1`
(it parses only local credential material). The six `dependency-currency` rows were live, because
`uv.lock` is the user's install path here (`install.sh` runs `uv sync`): `certifi`, the CA bundle
behind every `requests` call, plus `urllib3` (3), `idna` and `httplib2`. Another reporter had raised
the same lock the day before ([#356](https://github.com/eugeniughelbur/obsidian-second-brain/issues/356)),
it was refreshed the day of the scan, and Dependabot now watches `uv` as well.

## Patterns observed

**An allow-list is not a sandbox.** This is the lesson for anyone wiring Claude Code into a hook, a
cron job or a CI step. `--allowedTools` answers "which tools may run without asking", while
`--tools` answers "which tools exist". With `--dangerously-skip-permissions` nothing asks, so only
the second one still restricts anything. The same distinction appeared from the other side in
[overwirehq/claude-code-telegram](overwirehq-claude-code-telegram.html), whose maintainers kept
their guarded tools *out* of the SDK's `allowed_tools`, because a pre-approved tool never reaches
the permission callback that guards it.

**The test checked the flag, not what it did.** `tests/test_bg_agent_hook.py` recorded the command
line with a fake `claude`. That proves a flag was passed. It cannot prove what the flag does, which
is the only property the README promised. #373 now asserts the right flag. A test that pins a
security control needs to pin the control's effect, or at least the one flag that has it.

**The soft layer was there; the hard layer was a no-op.** In September the project fenced the
compaction summary as untrusted data, between fixed markers, with an instruction to treat it as
data. That is the right instruction-level defence, and it is advisory by nature: a model can still
be talked out of it. The tool list was meant to be the deterministic layer behind it, and it was the
layer that silently did nothing. Defence in depth only counts the layers that run.

**What the project does well.**
- One correct path boundary, `_resolve_in_vault`, resolves symlinks before its containment check,
  and every MCP tool that takes a path goes through it.
- `get_skill` uses a strict slug allowlist, and `move_note` creates its destination with `O_EXCL`.
- The MCP server speaks stdio, so there is no listening socket.
- The Telegram bot's sender gate fails closed and keys on numeric chat IDs, which stay bound to one
  account, unlike @usernames. It runs before any download or API spend, and model-written
  `[[wikilinks]]` go through `safe_note_path`.
- Link routing runs `uv run` with an argument list, not a shell, and the env file is created with
  mode `0600`.

Then the response: one day from the email to a merged fix, covering both findings and the
scheduled-run example in `SKILL.md` that the report had flagged as hardening, each with a test.

## Notes on the tool

- **No rule could have found either item.** The Medium is what a command-line flag means inside a
  shell script. The Low is what a third-party exception's text contains. A narrow custom rule is
  feasible for the first: flag `claude` run with `--dangerously-skip-permissions` and no `--tools`.
  It is now on the AI PatchLab backlog.
- **pip-audit skipped `uv.lock` again, and Trivy read it.** The coverage block says so, which is
  the only way a reader can tell "pip-audit found nothing" from "pip-audit examined nothing".
- **Semgrep's shell parser rejected two scripts**, so shell coverage is partial on a project that is
  mostly hooks and scripts, which is where this finding lived.

## Disclosure timeline

- 2026-10-24 — scan run at `f11ffb37` (`main`); both findings verified (the tool list by a two-arm
  differential on Claude Code 2.1.310, the key by a fake key against the real API endpoint)
- 2026-10-24 — report drafted for email. `SECURITY.md` rules out public issues and names an address;
  GitHub private vulnerability reporting is disabled on the repository (checked)
- 2026-10-24 — the automated run that drafted the report stopped before publishing this page, so the
  report's link to it led nowhere until today
- 2026-10-26 — report sent by email to the maintainer
- 2026-10-27 — both findings fixed by the maintainer in
  [#373](https://github.com/eugeniughelbur/obsidian-second-brain/pull/373), merged at 21:31 UTC, with
  a test for each
- 2026-11-08 — this page published. The fix was checked by reading the merged code; the
  differential was not re-run. It is not yet in a tagged release (latest `v0.20.0`, 2026-10-25)

## Reproduce

```bash
git clone https://github.com/eugeniughelbur/obsidian-second-brain /tmp/scan-target
git -C /tmp/scan-target checkout f11ffb37
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/eugeniughelbur-obsidian-second-brain --min-severity medium
```

---

## More from this series

- **Previous scan:** [huggingface/tau](huggingface-tau.html) — 2026-10-23, 0 first-party — dependency
- [Every scan in the series]({{ '/' | relative_url }}) — 115 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 29 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
