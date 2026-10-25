---
layout: default
title: "nicedreamzapp/claude-code-local: security scan"
description: "Security scan of nicedreamzapp/claude-code-local: 20 findings at medium+, 0 real after curation. Both local servers bind 127.0.0.1 as the security policy says; three hardening notes. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-10-25
---

# nicedreamzapp/claude-code-local — security scan

**Repository:** [nicedreamzapp/claude-code-local](https://github.com/nicedreamzapp/claude-code-local)
**Commit scanned:** `7361770` (`main`)
**Scan date:** 2026-10-25
**Disclosure status:** post-only — nothing survived curation as a vulnerability, so nothing was filed upstream. The three hardening notes below are published here: the first bounds what a web page can do to compute, the second is CI pinning, the third concerns what other programs on the same Mac can reach.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 1 |
| Medium | 17 |
| Low | 0 |
| Info | 2 |

**Total findings:** 20 at `--min-severity medium` (0 real after curation; the 2 info rows are coverage meta findings)

claude-code-local runs Claude Code against models on the Mac itself (3.4k★, MIT, Apple Silicon
only). Its core is `proxy/server.py`, a 1,922-line MLX server that speaks the Anthropic
Messages API, so Claude Code can point `ANTHROPIC_BASE_URL` at `localhost:4000`. It repairs
malformed tool-call JSON from local models and reuses the KV cache across turns. Around it sit
a one-file terminal coding agent (`agent/agent.py`, the "Native Engine"), `keep going` (resume
the last Claude Code conversation on a free cloud or local model when credits run out),
double-click launchers, a `curl | bash` installer and an experimental smart router. It is a
one-maintainer project that merges outside work: 15 pull requests merged in the 60 days before
the scan, from three authors. One of them came from the reporter of a bug (#54), who wrote the
fix (#56); the maintainer merged it and closed the report together on 2026-09-19.

**Scope of this write-up.** Every finding family below was checked at its call site. Read by
hand: both HTTP servers (bind address, routes, `Host` and `Origin` handling), the proxy's prompt
cache, `install.sh` and `setup.sh` (model selection and download, the generated launcher, the
`~/.zshrc` edit), the launchers, `keep going`, the usage-limit hook, and the one file Semgrep
could not parse. Not swept by hand: the tool-call parser and JSON repair in `proxy/server.py`,
which is one of the four areas the project's own `SECURITY.md` names, the Native Engine's XML
tool dialect, and the separate browser-agent repository that the Browser Agent launcher runs.
Read the result as "the tools' 20 findings are accounted for, plus those surfaces", not as a
clean bill of health for the parser.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `ran` | Ran without reporting a coverage problem. |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep scanned 132 paths but could not parse
`scripts/keepgoing-shell.sh`: line 8 uses a zsh-only expansion (`${${(%):-%x}:A:h:h}`) that a
bash parser rejects, so no rule ran on lines 7–21. The file was read by hand: 21 lines that
define a `keep` function and a `keepgoing` alias, quote their arguments and handle no input.
The `dependency-scan` row says `ran`, and it did, on `requirements-dev.txt`: two pinned test
tools (pytest 9.1.1, ruff 0.11.13) and their dependencies, with no advisories. It does not look
at `requirements-docs.txt`, which the docs workflow installs; checked by hand, its two pins
(mkdocs 1.6.1, mkdocs-material 9.7.7) have no known advisories. The runtime dependency,
`mlx-lm`, is in no manifest at all: `setup.sh` installs the latest release with
`pip install --upgrade`, so there is no stale pin to find and no lockfile for Trivy to read.

## Top findings

There is no vulnerability to lead with. The three notes below are hardening, each with a small
fix. The first is the one a reader of the project's `SECURITY.md` would want to know about.

### 1. The two local servers check neither `Host` nor `Origin`

- **Files:** `proxy/server.py:1778` (`do_POST`, served on `127.0.0.1:4000`);
  `smart-router/router.py:203` (`127.0.0.1:4010`, experimental, started by no launcher)
- **Tool:** manual review
- **Confidence:** high on the behaviour; the impact is bounded to compute
- **Why it matters:** `SECURITY.md` says the proxy "only listens on `127.0.0.1`", and it does:
  both servers bind loopback, so nothing on the LAN reaches them. Loopback does not keep out the
  browser on the same Mac. Neither handler reads `Host` or `Origin`, and both parse the body as
  JSON whatever its `Content-Type`, so a web page can send them a CORS-simple POST that needs no
  preflight. What that buys is small. The page cannot read an answer, because neither server
  sends CORS headers; the proxy has no endpoint that returns another request's data; its prompt
  cache reuses state only for an identical token prefix; and every shell command in the router
  is built from constants. What is left is compute and availability: inference on the proxy,
  which serves one request at a time, and on the router a forced model swap, with the warm pool
  unloaded and an 80 GB model loaded in its place. Without a `Host` check, a DNS-rebinding page
  could also read `/health`, which reports the model path, and that path can include the user's
  account name.
- **Recommendation:** accept only `Host: localhost:<port>` or `127.0.0.1:<port>`, which also
  defeats DNS rebinding, and refuse any request that carries an `Origin` header. Claude Code is
  a command-line client rather than a page, so an `Origin` header does not come from it; one
  logged request confirms that before enforcing. Some browsers now ask the user before a public
  page reaches a local address, but a server-side check does not depend on which browser is in
  use. It is a few lines at the top of `do_POST` and `do_GET` in each server.

### 2. Two CI workflows pin actions by tag; the newest one already pins by SHA

- **Files:** `.github/workflows/ci.yml:28,30`; `.github/workflows/docs.yml:30,32,50,52,64`
- **Tool:** semgrep (`github-actions-mutable-action-tag`, 7)
- **Confidence:** high
- **Why it matters:** a tag can be moved; a commit SHA cannot. `docs.yml` runs on push with
  `pages: write` and `id-token: write`, so an action whose tag was repointed would run with the
  right to publish the project's documentation site. Neither workflow uses
  `pull_request_target`. The scanned commit is the one that added `scorecard.yml`, and it pins
  all four of its actions to full SHAs with a version comment: the fix, already written once in
  a sibling file. OpenSSF Scorecard's `Pinned-Dependencies` check reports the other two
  workflows.
- **Recommendation:** pin the seven `uses:` lines the way `scorecard.yml` does, and add a
  `.github/dependabot.yml` entry for the `github-actions` ecosystem so the pins do not go stale.

### 3. The Browser Agent launcher opens the everyday Brave profile to local programs

- **File:** `launchers/Browser Agent.command:32`
- **Tool:** manual review
- **Confidence:** medium; the outcome depends on how the browser treats the flag
- **Why it matters:** the launcher quits Brave if it is running and reopens it with
  `--remote-debugging-port=9222` and no `--user-data-dir`, so it targets the profile the user
  browses with. It does not pass `--remote-allow-origins`, so Chromium's own checks keep web
  pages off the debugging port, which is the important half, and it is done right. Local
  programs are another matter: while the port is open, any program running as the user can drive
  that profile over the DevTools protocol, signed-in sessions included. Chrome 136 stopped
  honouring the debugging flags on the default profile for exactly this reason. If Brave inherits
  that change, the launcher's port check fails; if it does not, the agent drives the everyday
  profile.
- **Recommendation:** launch with `--user-data-dir="$HOME/.local/browser-agent/profile"`, so the
  agent gets a profile of its own and the user's sessions stay out of reach, whichever way the
  browser handles the flag.

## Why the rest were dismissed

All 18 non-meta findings are accounted for below; the other 2 are the coverage meta findings
above. The scanner dropped nothing: no finding fell below the `--min-severity` floor, and no
ignore pattern was used. The two `mitigated-in-app` rows are not scanner output. They are the
two servers in note 1, recorded so the corpus counts the hand-found item as well.

| Reason | Findings |
| --- | ---: |
| `by-design` | 9 |
| `not-reachable` | 8 |
| `mitigated-in-app` (note 1, manual review) | 2 |
| `product-surface` | 1 |

The largest family is `dynamic-urllib-use-detected`, 7 of the 8 `not-reachable` rows: every URL
handed to `urlopen` is a constant, a `127.0.0.1` port or operator configuration
(`AGENT_BASE_URL`, `MOONSTONE_URL`), so the `file://` read the rule warns about has no way in.
The `by-design` rows are note 2's seven tags, a SHA-1 that names a stamp file
(`scripts/limit-handoff.py:81`), and `setup.sh:33`, which runs Homebrew's official installer only
when Homebrew is missing. The one high, `subprocess-shell-true` at `agent/agent.py:196`, is the
Native Engine's Bash tool (below).

## Patterns observed

**The security policy names its own attack surface, and the code mostly holds to it.**
`SECURITY.md` lists four places where "a mistake could hurt someone": the installers, the local
server, model downloads and the tool-call parser. That is a better map than most repositories
hand a reviewer, and the claims that can be checked hold. The server binds `127.0.0.1`
(`HTTPServer(("127.0.0.1", PORT), ...)`), and so does the router. `install.sh` runs under
`set -euo pipefail`, refuses anything but Apple Silicon macOS, and clones over HTTPS. Every model
ID is a per-memory-tier constant in `setup.sh`, loaded through `mlx_lm` as safetensors; nothing
in the repository passes `trust_remote_code` or loads a pickle. Where note 1 qualifies the
policy, it is about what loopback means, not about whether the bind is real.

**Shell strings built the careful way.** This codebase shells out a lot, and the risky shapes
are handled. The smart router starts and stops model servers through `bash` and `bash -lc`
invocations, but every string is assembled from constants (fixed ports, a fixed model table, a
fixed library path), and request content only picks one key from a closed set in `route()`. The usage-limit hook opens a
Terminal window through AppleScript, so the folder name passes through two languages: it is
quoted for the shell with `shlex.quote`, then escaped for the AppleScript string, in that order,
which is the order that matters. `keep going` passes the session ID quoted, and its two `eval`s
run `KEEPGOING_BEFORE_LOCAL` and `KEEPGOING_AFTER_LOCAL`, hooks the user sets and the docs
describe as exactly that.

**An agent with no approval step, and docs that claim nothing more.** The Native Engine's Bash
tool runs the command the model chose with `shell=True`, a closed stdin and a timeout. That is
Semgrep's one high, and for a terminal coding agent it is the product: the docs describe the
tool, its timeout and why stdin is closed, and promise no sandbox or per-command approval that the
code fails to deliver. The Claude Code launchers pass `--permission-mode auto`, which the launcher
table in the docs also states. As with [tau](huggingface-tau.html), the honest boundary is the one
written down, and nothing here claims more.

**The cache bug that was already found.** The proxy keeps one KV cache across requests to make
long sessions fast, which is exactly where one conversation's state could bleed into the next,
and the code says it once did: a comment records that the trim read `.step` instead of `.offset`,
so "the cache kept the previous session's KV state" (issue #46). Today the cache is reused only
up to the longest shared token prefix, a cache that cannot be trimmed falls back to a full
prefill, and the server handles one request at a time. The explanation sits next to the
arithmetic that was wrong, where the next reader will look.

## Notes on the tool

- **A parse error still gets timeout advice.** The partial-coverage finding reports "0 rule
  timeouts" and recommends a higher `--timeout` anyway. A file Semgrep cannot parse fails the
  same way on every retry. This is the third scan to flag it. Backlog: split the recommendation
  by error type, and name the unparsed file as unexamined.
- **`dependency-scan: ran` overstates what was examined.** It audited the two pins in
  `requirements-dev.txt` and nothing else, while `requirements-docs.txt` sat beside it unread
  and the runtime dependency lived only in a `pip install` line in `setup.sh`. The row reads as
  "dependencies checked". Backlog: add `requirements-*.txt` to the runner's candidates, and mark
  the row `partial` when the only file audited is a development or test manifest.
- **`dynamic-urllib-use-detected` is 19 for 19 dismissed since the corpus began (2026-09-23).**
  It fires on a `urllib.request.Request` built from a literal `https://` URL
  (`bin/keepgoing.py:84`) as readily as on a variable. Backlog: demote it when every URL reaching
  `urlopen` is a literal, a loopback address or an environment variable.
- **Note 1 is invisible to every rule.** A `127.0.0.1` handler that never reads `Host` or
  `Origin` is a recurring shape in local-first AI tools, and its impact ranges from compute, as
  here, to whatever the server can do. Backlog: a rule that flags the shape and leaves the
  impact to curation.

## Disclosure timeline

- 2026-10-25 — scan run at `7361770` (`main`)
- 2026-10-25 — curated: no finding met the bar for a private report, so nothing was filed
  upstream; the project's private channel (GitHub private vulnerability reporting) was
  confirmed enabled
- 2026-10-25 — this page published

## Reproduce

```bash
git clone https://github.com/nicedreamzapp/claude-code-local /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/nicedreamzapp-claude-code-local --min-severity medium
```

---

## More from this series

- **Previous scan:** [huggingface/tau](huggingface-tau.html) — 2026-10-23, 0 first-party — dependency
- [Every scan in the series]({{ '/' | relative_url }}) — 114 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 27 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
