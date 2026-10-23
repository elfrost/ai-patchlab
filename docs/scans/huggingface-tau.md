---
layout: default
title: "huggingface/tau: security scan"
description: "Security scan of huggingface/tau: 49 findings at medium+, 0 first-party defects after curation; all 42 dependency advisories sit in uv.lock, which only the contributor install reads. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-10-23
---

# huggingface/tau — security scan

**Repository:** [huggingface/tau](https://github.com/huggingface/tau)
**Commit scanned:** `261662b` (`main`)
**Scan date:** 2026-10-23
**Disclosure status:** post-only — nothing first-party survived curation, so nothing was filed upstream. All 42 dependency advisories sit in `uv.lock`, which none of the documented user installs reads.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 6 |
| High | 26 |
| Medium | 14 |
| Low | 0 |
| Info | 3 |

**Total findings:** 49 at `--min-severity medium` (0 first-party defects after curation; 42 dependency advisories, all from the lockfile; the 3 info rows are coverage meta findings)

tau is a Python port of Pi's minimalist coding-agent harness, published on PyPI as `tau-ai`
(0.4.8 at the scanned commit): a Textual terminal UI, an RPC mode, an extension system, project skills and
prompts, session export, and sign-in with an OpenAI Codex subscription alongside API keys
(2,984★, MIT). It is young and busy: created in June 2026, with 63 merged pull requests from
11 human authors and 21 closed issues in the 60 days before the scan.

**Scope of this write-up.** Every finding family below was checked at its call site, and
five surfaces no rule inspects were read by hand: the one listening socket (the OAuth
callback), the project-trust gate, the session HTML export, the image-decoding path and the
self-updater's command form. Not swept by hand: the provider adapters, the API offered to
trusted extensions, the RPC protocol, how the TUI renders model and tool output, and
`tui/widgets.py`, which Semgrep could not parse (below). Read the result as "the tools' 49
findings are accounted for, plus those five surfaces", not as a clean bill of health for
the rest.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | A shipped lockfile was not covered by the dependency scan |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep scanned 384 paths but could not parse
`src/tau_coding/tui/widgets.py`: line 3061 declares a Python 3.12 constrained type parameter
(`def _grouped_sidebar_file_widgets[SidebarResource: (Skill, PromptTemplate)](`), so no
Semgrep rule ran on that file. Its two timeouts were the boto3 `hardcoded-token` rule on
`session_export.py` and `tui/app.py`, in a project that does not import boto3; every other
rule completed on both files, and Gitleaks reads all three. `dependency-scan` (pip-audit)
resolved the version floors in `pyproject.toml` and did not read the shipped `uv.lock`;
Trivy read `uv.lock`, and every dependency finding below comes from it.

## Top findings

There is no first-party finding to lead with. The one item worth acting on is a lockfile
that has fallen behind, and it reaches fewer people than its 42 rows suggest.

### 1. `uv.lock` pins Pillow 12.3.0, anyio 4.13.0 and certifi 2026.5.20 — the contributor install only

- **File:** `uv.lock`
- **Tool:** trivy (42 advisories: Pillow 39, of them 4 critical, 23 high, 12 medium; anyio 2;
  certifi 1)
- **Confidence:** high that the pins are behind; they reach only people who install from the
  lock
- **Why it matters:** every install path the README documents resolves the floors in
  `pyproject.toml` at install time rather than the lock: the one-line installers (both sources,
  `website/static/install.sh` and `install.ps1`, run `uv tool install tau-ai`), `uv tool install tau-ai`,
  `pipx install tau-ai` and `pip install tau-ai`. The floors are `pillow>=11.0`,
  `anyio>=4.0` and `httpx[socks]>=0.27`; resolved today they give Pillow 13.0.0, anyio
  4.15.1 and certifi 2026.10.23, each at or past its fixed version (13.0.0, 4.14.2,
  2026.10.19). pip-audit's zero and Trivy's 42 are both right: they describe two install
  paths. The lock is what `uv sync --dev` installs, so it reaches people developing tau.
  On that path Pillow has one caller, the `read` tool's `process_image`, and it sits behind
  a magic-byte allowlist: JPEG, static PNG, GIF, WebP and header-checked BMP. TIFF, EPS,
  PDF, XBM and animated PNG data never reaches a decoder, though several of the 39
  advisories are in the GIF, BMP and JPEG code that remains.
- **Recommendation:** `uv lock --upgrade-package pillow --upgrade-package anyio
  --upgrade-package certifi`, and a `uv` entry in `.github/dependabot.yml`, which today
  covers only `github-actions`. Raising the floors (for example `pillow>=13.0.0`) would also
  close the one user-side gap: `pip install tau-ai` into an existing environment keeps an
  older Pillow that already satisfies `>=11.0`.

## Why the rest were dismissed

All 46 non-meta findings are accounted for below; the other 3 are the coverage meta
findings above. The scanner dropped nothing: no finding fell below the `--min-severity`
floor, and none sat under an ignored sample path.

| Reason | Findings |
| --- | ---: |
| `dependency-currency` (finding 1) | 42 |
| `by-design` | 3 |
| `not-reachable` | 1 |

The three `by-design` rows are Semgrep's `python37-compatibility-importlib2`, which warns
that `importlib.resources` does not exist before Python 3.7 in a project that requires
3.12. The `not-reachable` row is `dynamic-urllib-use-detected` in
`scripts/generate_models.py:26`, a maintainer build script for the model catalogue: its
loader hands only `http://` and `https://` locations to `urlopen`, so the `file://` read the
rule warns about cannot reach it, and the line already carries a reviewed `noqa: S310`.

## Patterns observed

**The coding-agent risk that matters most is gated, and gated wide.** A coding agent
opened in someone else's repository reads whatever that repository ships for it. tau's
project-trust layer (`src/tau_coding/project_trust.py`) covers seven kinds of
project-supplied input: context (`AGENTS.md` at every level from the project root down to
the working directory, plus `.tau/AGENTS.md` and `.agents/AGENTS.md`), extensions
(`.tau/extensions`, Python that runs at session startup), prompts, settings, skills, system
prompts (`.tau/SYSTEM.md`, `.tau/APPEND_SYSTEM.md`) and themes. In the CLI, none of it loads
until the project is trusted. The default is to ask, and a session that cannot ask — headless, or
with no UI to ask in — resolves to untrusted. The project path is canonicalized with
`resolve(strict=True)` before trust is resolved. Gating `AGENTS.md` is the strict choice: it is
easy to treat as harmless documentation, and it is the file a hostile repository would
write first. The module states its own limit in one sentence: project trust "is deliberately
not a filesystem, process, network, tool, model, or prompt-injection sandbox". That
sentence matters. A trust prompt that implied containment would be the finding; one that
disclaims it is an honest boundary. Past the gate, tau does what the Pi design it ports
does: the model's tool calls, shell included, run without a per-call approval step, and
nothing in the README or the code claims otherwise. For a coding agent that is product
surface, not a defect.

**One listening socket, built the careful way.** The only server socket in the codebase is
the OAuth callback for signing in with an OpenAI Codex subscription. It binds `127.0.0.1` by
default (`TAU_OAUTH_CALLBACK_HOST` overrides it), the flow uses PKCE with an S256 challenge
and a `secrets.token_hex(16)` state, and the callback handler rejects a missing or wrong
state. The one lenient check is deliberate: when the user pastes the redirect URL or a bare
code by hand, `_validate_state` accepts input that carries no state, because a bare code has
none. Elsewhere in this series that shape is the finding: a check skipped whenever the
caller leaves the field out. Here PKCE retires it. A code is redeemable only with the
verifier this process generated, so a code minted by anyone else's login fails at the token
endpoint.

**Output that leaves the machine is escaped.** Session export writes a standalone HTML
file. Text goes through `_escape` and attributes through `_attr`. The session itself is
embedded base64-encoded in a `<script type="application/octet-stream">` block, which no
base64 string can close, and read back with `textContent`. `session_export.py` never
assigns `innerHTML` and loads no external script or stylesheet. A transcript is
attacker-influenced by nature — it holds whatever a fetched page or a repository's files
said — so this is the right default for a file people share.

**The drift is where automation does not reach.** Dependabot runs weekly for GitHub
Actions with a seven-day cooldown, and the day's newest commit was one of its grouped
updates. Nothing watches `uv.lock`, which is why the lockfile carries three packages past
their fixes while every user install is current. It is the same gap
[voxbento](fossasia-voxbento.html) had in its docs-site `npm` lockfile. tau has no
`SECURITY.md`, but private vulnerability reporting is enabled on the repository, so a
reporter does have a private channel.

## Notes on the tool

- **Python 3.12 syntax defeats Semgrep's parser.** A single PEP 695 type parameter kept
  every Semgrep rule off a 3,000-line first-party module, and the only trace is one entry in
  the meta finding. More projects will adopt `requires-python >=3.12`. Backlog: when the
  unparsed file is first-party source, name it as an unexamined module in the coverage
  detail, not just as an "other scan error".
- **A timeout is not always a coverage loss.** Both timeouts were a boto3 rule on a
  project with no boto3 import. Backlog: mark timed-out rules whose target library is
  absent from the dependency set, so the partial-coverage row reads as what it is.
- **The compatibility rule fires on modern projects.** `python37-compatibility-importlib2`
  has now been dismissed on three of the last four scans (boss-agent-cli, treg,
  tau). Backlog: drop `python37-compatibility` rules when `requires-python` already
  excludes the versions they protect.
- **The `uv.lock` gap, with the answer reversed.** pip-audit read the floors and found
  nothing; Trivy read the lock and found 42. On voxbento the lockfile was what users ran.
  Here it is the contributor path and the floors are the user path, so the meta finding's
  question ("which install path does the project document?") decided the result.

## Disclosure timeline

- 2026-10-23 — scan run at `261662b` (`main`)
- 2026-10-23 — curated: no first-party finding, so the bar for filing upstream was not met
  and nothing was filed
- 2026-10-23 — this page published

## Reproduce

```bash
git clone https://github.com/huggingface/tau /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/huggingface-tau --min-severity medium --ignore-samples
```

---

## More from this series

- **Previous scan:** [fossasia/voxbento](fossasia-voxbento.html) — 2026-09-28, 0 first-party — dependency
- [Every scan in the series]({{ '/' | relative_url }}) — 113 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 27 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
