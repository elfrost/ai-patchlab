---
layout: default
title: "haris-musa/excel-mcp-server: security scan"
description: "Security scan of haris-musa/excel-mcp-server: 5 findings at medium+, 0 real after curation. The security model in its SECURITY.md held everywhere it was checked; one hardening note on a README placeholder token. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-09
---

# haris-musa/excel-mcp-server — security scan

**Repository:** [haris-musa/excel-mcp-server](https://github.com/haris-musa/excel-mcp-server)
**Commit scanned:** `1e6af4e` (`main`)
**Scan date:** 2026-11-09
**Disclosure status:** post-only — nothing survived curation as a vulnerability, so nothing was filed upstream. The one hardening note below concerns an example in the README, not the server's defences.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 0 |
| Medium | 2 |
| Low | 0 |
| Info | 3 |

**Total findings:** 5 at `--min-severity medium` (0 real after curation; the 3 info rows are coverage meta findings)

excel-mcp-server lets AI clients (Claude, Cursor, VS Code, Codex and other MCP clients) create
and edit Excel workbooks without Excel installed: cells and formulas, charts, PivotTables and
slicers, conditional formats, CSV import and export, and reading VBA (4.3k★, MIT). It runs
over stdio for a local client or over Streamable HTTP on port 8017, ships a Docker image, and
carries its own formula calculator so it can return the values Excel would show. The source is
218 Python files and about 32,500 lines, with 93 test files. It is a one-maintainer project that
moves fast: all 69 pull requests merged in the 60 days before the scan are the maintainer's
own; in the same window 62 issues opened by 55 different people were closed, 60 of them with a
reply; and versions 2.2.7, 2.2.8 and 2.2.9 all shipped on the day of the scan.

**Scope of this write-up.** Every finding below was checked at its call site. Read by hand:
path confinement (`paths.py`, all of it), the HTTP transport and its token check
(`server/http.py`, `cli.py`), the workspace code that opens, size-checks and saves workbooks,
the directory listing, the formula gate (`formulas.py`, `xlm.py`, `links.py`), the CSV export
default, the table tools that write calculated columns and totals, the `Dockerfile`, and the
DNS-rebinding code in the MCP SDK release that the lockfile pins (`mcp` 2.3.0). Swept by search
across `src/`: process execution, outbound HTTP clients, deserialization and XML parsing. Not
swept by hand: the upload scanner behind `import_workbook` (`upload_scan.py`,
`upload_links.py`), the calculator and its resource bounds (`calc/`), and the VBA container
reader and writer (`ovba*.py`, `cfb.py`). The formula gate was read, not run against test
inputs. Read the result as "the tools' findings are accounted for, and the defences named above
hold as documented", not as a clean bill of health for the upload scanner or the calculator.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `partial` | A shipped lockfile was not covered by the dependency scan |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** no. Semgrep scanned 275 paths but could not parse
`src/excel_mcp/calc/parser.py`: line 90 opens a `match node:` statement, valid since Python
3.10, and Semgrep's parser rejected it, so no rule ran on that file. It holds the calculator's
syntax-tree types and the parser that builds them (344 lines). Its imports are `re`,
`dataclasses`, openpyxl's formula tokenizer and the calculator's own modules, so it touches no
file, process or network; it was read for that, not reviewed line by line. The
`dependency-scan` row is `partial` because its own check fired: pip-audit resolved the
`pyproject.toml` version floors (33 packages, no advisories), while the Docker image installs
from `uv.lock`, which pip-audit does not read. Trivy read that lockfile (45 packages, the
development group included, no advisories). Both install paths come out clean: `uvx
excel-mcp-server`, which the README leads with, resolves the floors fresh, and the image runs
`uv sync --locked`.

## Top findings

There is no vulnerability to lead with. One hardening note:

### 1. The README's examples for remote use set the token to `change-me`, and the server accepts it

- **Files:** `README.md` ("Remote use" and "Docker"); `src/excel_mcp/cli.py:42`
- **Tool:** manual review
- **Confidence:** high on the behaviour; how often the example is run as written is unknowable
- **Why it matters:** the server refuses to listen on any host other than `127.0.0.1`,
  `localhost` or `::1` without `EXCEL_MCP_AUTH_TOKEN`. That is the part that matters, and it is
  done right. The two examples that show how to open the server to other machines both set the
  token to `change-me`, next to `--host 0.0.0.0` and `docker run -p 8017:8017`. `cli.py:42`
  takes any non-empty value, so a command pasted as written serves the workbook folder to the
  network behind a token printed in the project's own README. The value says to change it;
  nothing checks that it was.
- **Recommendation:** refuse to start when the token is the documented placeholder or shorter
  than about 16 characters, and show how to generate one in the README
  (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) instead of a literal. That is
  a few lines in `main()`, next to the refusal that already exists.

## Why the rest were dismissed

Both non-meta findings are accounted for below; the other 3 are the coverage meta findings
above. The scanner dropped one finding under the `--min-severity medium` floor, Trivy's
low-severity "No HEALTHCHECK defined" on the `Dockerfile`, and no ignore pattern was used. The
`placeholder-secret` row is not scanner output: it is the hardening note above, recorded so the
corpus counts the hand-found item as well.

| Reason | Findings |
| --- | ---: |
| `below-min-severity` (scanner) | 1 |
| `domain-noun-collision` | 1 |
| `by-design` | 1 |
| `placeholder-secret` (note 1, manual review) | 1 |

The `domain-noun-collision` row is a Django rule, `unvalidated-password`, matching
`operations/protection.py:99`: `SheetProtection.set_password()` is openpyxl writing Excel's
sheet-protection hash into a workbook, not an account password, in a project that does not use
Django. The `by-design` row is `missing-integrity` on `docs/index.html:9`, the landing page's
`<link rel="canonical">`: a self-link, not a script or stylesheet, so Subresource Integrity has
nothing to protect.

## Patterns observed

**A security model you can check, and the code keeps to it.** `SECURITY.md` does not stop at a
reporting address. It lists the defences for files, formulas, CSV, uploads, the calculator, the
network, resources, XML text, preserved content and macros, each specific enough to test, and
every claim checked here held. Path confinement resolves symlinks and then compares with
`Path.is_relative_to`, not a string prefix, so `/srv/workbooks2` does not count as inside
`/srv/workbooks`. Network paths are refused before anything touches them, with or without
`--allow-dir`, because resolving one already opens a connection that can carry the user's
Windows credentials; with `--allow-dir`, so is a path on any other drive. After resolving, the
path is checked again, since "a link can lead to a network share or a device that the typed
path did not name". Windows device names are refused in every folder, including `COM¹` to
`COM³`, which Windows also treats as devices, a detail that is easy to miss. The directory
listing passes every hit back through the same check, so a symlink inside the folder that
points out of it is not listed. Saves go to a `mkstemp` file in the target folder and are then
swapped in, and the docstring says why: a symlink planted at the temporary name cannot redirect
the write.

**The loopback gap, closed by reading the SDK.** The previous scan in this series,
[claude-code-local](nicedreamzapp-claude-code-local.html), had two `127.0.0.1` servers that
checked neither `Host` nor `Origin`. This one binds localhost by default with no token and
relies on the MCP SDK's DNS-rebinding protection, which the SDK turns on for exactly three host
strings. The project's `LOOPBACK_HOSTS` is those three, with a comment saying why: any other
loopback address, such as `127.0.0.2`, would be reachable through a rebound domain, so it needs
a token like a public address. Checked against the pinned `mcp` 2.3.0 wheel:
`streamable_http_app(host=...)` enables the `Host` and `Origin` allowlist for `127.0.0.1`,
`localhost` and `::1`, and for nothing else. Everything outside that set needs
`EXCEL_MCP_AUTH_TOKEN`, compared with `hmac.compare_digest`, unless `--allow-unauthenticated` is
passed for a proxy that authenticates. The Docker image binds `0.0.0.0`, so it will not start
without a token, and it runs as a non-root user.

**A formula gate that knows what Excel can reach.** An agent that writes workbooks can write a
formula that runs when a person opens the file. The gate tokenizes the formulas the server
writes (cell values, rule operands, defined names, table formulas, and the formulas that row
edits and sheet renames rewrite) rather than matching patterns, and rejects anything it cannot
tokenize. It blocks the network functions added to Excel in recent years (`IMAGE`,
`TRANSLATE`, `DETECTLANGUAGE`, `COPILOT`, `PY`) along with `WEBSERVICE` and `STOCKHISTORY`;
Google Sheets' `IMPORT*` family, for files opened there; `RTD`, DDE, `CALL`, `REGISTER` and the
cube functions; the Excel 4.0 macro functions that read files, other workbooks or the
application or start other code, chosen from the 527 names in Microsoft's reference, because
defined names run with macro rights; references to any other workbook; and `HYPERLINK` unless
its target is a literal web, mail or in-workbook address. Function names are normalised through
the file format's prefixes (`_xlfn.`, `_xleta.`), so a function passed by name to `MAP` or
`BYROW` is caught as well. CSV export puts a `'` in front of text that starts with `=`, `+`,
`-` or `@` (or a tab or carriage return) unless the caller turns that off, and by the policy's
account imported fields never become formulas.

**A small surface underneath.** Nothing in `src/` imports `subprocess` or an HTTP client, or
unpickles anything. XML is parsed with the standard library, which does not fetch external
entities, and the code that reads preserved package parts refuses any with a `DOCTYPE`. For a
server whose job is opening files other people made, that is a deliberately small surface.

## Notes on the tool

- **A parse error still gets timeout advice, for the fourth time.** The partial-coverage
  finding reports "0 were rule timeouts" and recommends a higher `--timeout` anyway, though a
  file Semgrep cannot parse fails the same way on every retry. The cause is new to the series:
  a `match` statement on a bare name, valid since Python 3.10. Backlog: split the
  recommendation by error type, and name an unparsed file as unexamined.
- **The lockfile check did its job.** `dependency-scan-unaudited-lockfile` fired because
  pip-audit read the `pyproject.toml` floors while the image installs from `uv.lock`; Trivy
  covered the lockfile, and the two results describe the two install paths the project
  documents. That is the case the check exists for.
- **Two rules fired outside their domain.** A Django password rule matched openpyxl's sheet
  protection, and `missing-integrity` matched a `<link rel="canonical">`, the second scan in
  the corpus where it did. Backlog: skip `link` elements whose `rel` is `canonical`,
  `preconnect` or `dns-prefetch`, which load nothing.
- **The hardening note is invisible to every rule.** A placeholder token lives in prose, not
  code. Gitleaks rightly does not flag `change-me`, and no rule connects a README example to
  the check in `cli.py`. Backlog: during curation, for every token or password variable, find
  the value the docs show and ask whether the code accepts it.

## Disclosure timeline

- 2026-11-09 — scan run at `1e6af4e` (`main`)
- 2026-11-09 — curated: no finding met the bar for a private report, so nothing was filed
  upstream; the project's private channel (GitHub private vulnerability reporting, named in
  `SECURITY.md`) was confirmed enabled
- 2026-11-09 — this page published

## Reproduce

```bash
git clone https://github.com/haris-musa/excel-mcp-server /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/haris-musa-excel-mcp-server --min-severity medium
```

---

## More from this series

- **Previous scan:** [nicedreamzapp/claude-code-local](nicedreamzapp-claude-code-local.html) — 2026-10-25, 0 real
- [Every scan in the series]({{ '/' | relative_url }}) — 116 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 29 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
