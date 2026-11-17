---
layout: default
title: "jordan-gibbs/hyperresearch: security scan"
description: "Security scan of jordan-gibbs/hyperresearch: 45 findings at medium+, 0 real after curation. A careful SSRF gate and prompt-injection fence; two hardening notes, one on an MCP path the fence does not cover. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-11-17
---

# jordan-gibbs/hyperresearch — security scan

**Repository:** [jordan-gibbs/hyperresearch](https://github.com/jordan-gibbs/hyperresearch)
**Commit scanned:** `8f192b8` (`main`)
**Scan date:** 2026-11-17
**Disclosure status:** post-only. Nothing survived curation as a vulnerability, so nothing was filed upstream. The two hardening notes below concern a defence that one path skips and a header that is never checked, not a defect anyone can exploit reliably.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 28 |
| Medium | 16 |
| Low | 0 |
| Info | 1 |

**Total findings:** 45 at `--min-severity medium` (0 real after curation; the 1 info row is the coverage meta finding for the disabled AI review)

hyperresearch turns Claude Code, and now OpenAI Codex, into a deep-research agent (4.8k★, MIT;
`hyperresearch` 0.13.3 on PyPI at the time of the scan). One prompt starts a pipeline of up to
16 steps, run by skills and subagents. The pipeline searches the web and scholarly sources
(OpenAlex, Crossref, CORE, ClinicalTrials.gov, SEC EDGAR, FRED and others), fetches pages with a
headless browser, has the citations checked by a separate agent, and keeps every source in a
local Markdown-plus-SQLite vault that later sessions reuse. Around the CLI (`hyperresearch`,
also `hpr`) it ships a stdio MCP server, a small web viewer for the vault (`hyperresearch
serve`), and installers that write skills, subagents and hooks into `.claude/` and `.codex/`.
The source is 115 Python files and about 32,000 lines under `src/`, with 95 test files. The
project is seven months old and busy. In the 60 days before the scan, 55 pull requests were
merged from 14 human authors (26 of them by the maintainer), and 16 issues opened by 12
different people were closed. A hosted version exists (hyperresearch.ai, with a REST API and a
remote MCP server). That is a live service, so it was not examined: everything below is about
the open-source repository. The commercial tier is why this scan was run as strict-norm. Anything
real would have gone through GitHub private vulnerability reporting, which is enabled on the
repository. There is no `SECURITY.md`.

**Scope of this write-up.** Every tool finding below was checked at its call site. Read by
hand: the SSRF gate (`web/safe_http.py`, all of it), the URL and TLS handling of the browser lane
(`web/crawl4ai_provider.py`), the open-access fetch gate (`core/oa.py`), the untrusted-content
fence (`core/untrusted.py`) and every caller of it, all 13 MCP tools (`mcp/server.py`), the vault
viewer and its Markdown renderer (`serve/`, all of it), the Claude Code and Codex hook installers,
the path from a fetched page to a note on disk (`core/fetcher.py`, the frontmatter writer, image
downloads) and the destination check in `import`. Swept by search across `src/`: every process
launch (six call sites, all argv lists), every outbound HTTP client, every SQL statement the
tools flagged, and where API keys come from. Not swept by hand: PDF parsing (`web/pdf.py` on
PyMuPDF), the scholarly providers' response parsers, run manifests and `run resume`
(`core/runs.py`), the 1,900-line linter, and the pipeline's prompts themselves (the 16 step
skills and about 4,600 lines of agent instructions in `core/hooks.py`). Read the result as "the
tools' findings are accounted for, and the defences named below hold as written", not as a
review of the prompt pipeline.

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `ran` | Ran without reporting a coverage problem. |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `ran` | Ran without reporting a coverage problem. |
| `ai-security-review` | `not_run` | AI security review is disabled |

**Coverage complete:** yes. Semgrep scanned 173 paths with no errors. One row needs a sentence:
Trivy ran, but the repository ships no lockfile (only `pyproject.toml`), so it had nothing to read
and returned zero targets. The dependency result therefore comes from pip-audit alone. It
resolved the `pyproject.toml` floors to 107 packages with no known advisories, which is exactly
what `pip install hyperresearch`, the install the README documents, gets today.

## Top findings

There is no vulnerability to lead with. Two hardening notes:

### 1. The MCP server hands out fetched pages without the `<untrusted-source>` fence the CLI applies

- **Files:** `src/hyperresearch/mcp/server.py:92`, `:118`, `:141`; compare
  `src/hyperresearch/cli/note.py:223` and `src/hyperresearch/cli/search.py:212`; `README.md:342`
- **Tool:** manual review
- **Confidence:** high on the behaviour. What the fence would have stopped in a given session
  cannot be known, because the fence is a mitigation, not a boundary.
- **Why it matters:** the README makes a specific promise: every body fetched from the web "is
  served wrapped in `<untrusted-source url="...">` delimiters with an inline treat-as-data
  preamble, on both paths that serve bodies (`note show` in single, batch, and JSON forms, and
  `search` with bodies included)". Both of those
  paths call `wrap_body()`. There is a third path. The MCP server's `search_notes`, `read_note`
  and `read_many` return the same note bodies from the same table, and none of them wraps
  anything. So an MCP client (Claude Desktop, Cursor and the like) receives fetched web text with
  no fence and no preamble. The same server registers `fetch_url`, `create_note` and
  `update_note` next to those readers, so the agent reading the unfenced text is one that can
  also make the tool fetch and write. The module docstring has not caught up either: it still
  says "Exposes 8 tools" and "Read-only by design", and 13 are registered.
- **Recommendation:** in the three tools, call `is_untrusted()` and `wrap_body()` exactly as
  `note show` does: one small helper, three call sites. Add a test asserting that every MCP tool
  that returns a body returns a fetched note fenced. Rewrite the docstring to list all 13 tools,
  including the three that fetch or write.

### 2. The local vault viewer answers to any `Host`

- **Files:** `src/hyperresearch/serve/server.py:365` (`do_GET`), `:614` (bind);
  `src/hyperresearch/cli/serve.py:11` (default port 8080)
- **Tool:** manual review
- **Confidence:** high on the behaviour. Whether a given browser lets a public page reach
  loopback depends on its own local-network protections.
- **Why it matters:** `hyperresearch serve` binds `127.0.0.1` and only reads, and both are right.
  It never looks at `Host` or `Origin`, though. A web page that rebinds its own domain to
  `127.0.0.1` can therefore read `/api/graph` and `/note/<id>`, which serve the whole vault:
  fetched sources, and the research questions and reports the user wrote, on a predictable
  default port, for as long as the viewer runs. The series has met this before: two loopback
  servers in [claude-code-local](nicedreamzapp-claude-code-local.html) checked neither header,
  and [excel-mcp-server](haris-musa-excel-mcp-server.html) closed the same gap with an explicit
  host list.
- **Recommendation:** at the top of `do_GET`, refuse any request whose `Host` is not
  `127.0.0.1:<port>` or `localhost:<port>`. That is a few lines. A smaller item on the same page:
  `server.py:475-478` puts `row["status"]` into a `class` attribute unescaped while escaping it in
  the text beside it. Nothing can reach it today, because `status` is an enum enforced when
  frontmatter is parsed and when `update_note` writes it, but escaping it would make the line
  match its neighbour.

## Why the rest were dismissed

All 44 non-meta tool findings are accounted for below. The scanner dropped two more under the
`--min-severity medium` floor (Semgrep's low-severity `dependabot-missing-cooldown`, twice), and
no ignore pattern was used. Three rows are not scanner output: they are the hand-found notes
above, recorded so the corpus counts them too.

| Reason | Findings |
| --- | ---: |
| `sql-identifier-fp` | 27 |
| `by-design` | 11 |
| `not-reachable` (5 tool findings + the unescaped-attribute nit) | 6 |
| `below-min-severity` (scanner) | 2 |
| `placeholder-secret` | 1 |
| `product-surface` (note 1, manual review) | 1 |
| `mitigated-in-app` (note 2, manual review) | 1 |

The largest family is the series' most common false positive. All 27 SQL hits (21
`sqlalchemy-execute-raw-query`, 6 `formatted-sql-query` on the same migration lines) are in a
project that uses `sqlite3`, not SQLAlchemy, and binds every value with `?`. The f-strings carry
only placeholder lists, `WHERE` clauses assembled from constant fragments (`ORDER BY` comes from a
fixed `sort_map`), table names from constant tuples, and migration column names read back from
`PRAGMA table_info`; one migration even quotes them. The 11 `by-design` rows are three gitleaks
hits on the `sealed_token` of the README's star-history.com chart, a token the service issues
encrypted for README embeds; a Jinja2 environment without autoescape that renders the
package's own prompt files to Markdown for a model, never HTML for a browser; and seven mutable
action tags. Those are the one hardening item among the dismissals. The workflows run on push,
tags and releases only, `publish.yml` grants `contents: read` globally, and it isolates
`id-token: write` in an environment-gated job that only downloads the built artifact. Pinning
`pypa/gh-action-pypi-publish@release/v1` in that job to a SHA is the one pin worth adding. The
`not-reachable` rows are Python 3.6 and 3.7 compatibility rules on a project that requires 3.11,
a benchmark harness outside the wheel, and an import whose module name comes from a constant
tuple. The `placeholder-secret` is a sequential 32-character test key.

## Patterns observed

**An SSRF gate written against parsers, not just addresses.** Most SSRF guards resolve a host,
reject private ranges and stop there. `safe_http.py` follows redirects by hand and re-checks
every hop. It classifies an IPv4-mapped IPv6 address by the IPv4 inside it (the comment notes
that Python 3.11, 3.12 and 3.13 disagree on those addresses), decodes the IPv4 inside a 6to4
prefix, and adds the carrier-grade NAT range that the `ipaddress` module does not flag. The
browser lane hands URLs to Chromium, which parses them under the WHATWG standard rather than RFC
3986, so the gate refuses every spelling the two families read differently: a backslash in the
authority, a percent-encoded host, a numeric host such as `0x7f.1`. Hostnames are normalised
with the same IDNA 2008 encoder httpx uses, so `straße` cannot be checked as `strasse` and
connected as `xn--strae-oqa`. Bodies are capped while they stream. The residual risk is written
down instead of hidden: the module docstring says DNS rebinding between the check and the
connect is not closed. The browser lane says the same about its own limit. It re-checks the URL
where navigation ended and keeps private-network content out of the vault, and its docstring
states plainly that "blind SSRF survives" a redirect followed inside the browser. The browser
lane also turns certificate checking back on: crawl4ai launches Chromium with certificate errors
ignored, the provider strips those flags, and it raises rather than fetch unverified if a crawl4ai
upgrade moves the code it patches. The open-access substitution, which fetches whatever URL a
scholarly API returns, goes through the same gate. It refuses bare hostnames and URLs with
credentials in them, with a comment noting that "a repository redirect is the easy way past"
a check that saw only the first URL.

**A fence that expects forgery, and a path it does not reach.** The prompt-injection fence is
better than most. It neutralises fake fence tags in any case or spacing (`</ Untrusted-SOURCE`),
escapes the URL attribute, and wraps after token-budget truncation so the closing tag can never
be cut off. A fetched page also cannot vouch for itself. The fence skips note types that the
pipeline's own subagents write. A fetched note's frontmatter, though, is built from a fixed set of
keys and serialised with `yaml.dump`, so a page title with a newline in it cannot add a `type:`
line and pass as one of them. The weakness is a path the documentation did not count, which
makes this a seam to scan more than a bug to hunt. The series met the inverse in
[obsidian-second-brain](eugeniughelbur-obsidian-second-brain.html): there the untrusted-text fence
held and the hard layer behind it did not. Here the CLI paths have the fence, and the MCP path has
only the client's own tool approvals.

**A viewer that escapes first.** The vault viewer's Markdown renderer escapes the whole body
before it applies a single pattern, and it checks link targets against a scheme allowlist after
decoding HTML entities and dropping control characters, so `&#106;avascript:` and `java\nscript:`
both fail. The search page escapes snippets before inserting its highlight tags, and the comment
says why: an unterminated `<img src=x onerror=...>` in a fetched page would otherwise borrow the
`>` of the highlight tag. On Windows the server turns `SO_REUSEADDR` off, because Winsock reads
that option as "share a port someone else is listening on". What it lacks is note 2.

**Small surfaces handled with care.** Every process launch is an argv list. API keys for the
search and embedding providers come only from environment variables, so none is written into a
vault that often lives inside a git repository. `import` holds every destination to the notes
tree before copying anything. The MCP server clamps result limits, because SQLite reads a
negative `LIMIT` as "no limit" (the comment names a prompt-injected agent as the reason).
`update_note` validates `status` before writing. The Claude Code hook the installer adds is a
reminder that only adds context, and it never returns a permission decision.

## Notes on the tool

- **`ran` is not the same as "read something".** Trivy's coverage row says `ran`, and it did, but
  with no lockfile in the repository it found zero targets. The row reads exactly like a clean
  lockfile audit. Backlog: carry Trivy's target count into `coverage.json` and report a
  zero-target run as such.
- **Compatibility rules on a 3.11+ project.** Three Python 3.6 and 3.7 compatibility rules
  arrived as `high` on a project whose `requires-python` is `>=3.11`. Backlog: read
  `requires-python` and drop compatibility rules below it.
- **Identifier-only SQL, 27 more.** The largest family in the corpus grew again, in the same
  shape: values bound, names constant. Backlog stands: mechanise that check, so a statement whose
  only interpolations are placeholder lists, constant tuples or schema reads is labelled before a
  person reads it.
- **Both hardening notes are absences.** No rule sees a wrapper that one transport forgot to call,
  or a header that is never read. Backlog: when a project documents a sanitising wrapper (here
  `wrap_body`), list every path that returns the same data (CLI, MCP, HTTP) and check that each
  one calls it.

## Disclosure timeline

- 2026-11-17 — scan run at `8f192b8` (`main`)
- 2026-11-17 — curated: no finding met the bar for a private report, so nothing was filed
  upstream; GitHub private vulnerability reporting was confirmed enabled on the repository
- 2026-11-17 — this page published

## Reproduce

```bash
git clone https://github.com/jordan-gibbs/hyperresearch /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/jordan-gibbs-hyperresearch --min-severity medium
```

---

## More from this series

- **Previous scan:** [sandbox-quantum/switch](sandbox-quantum-switch.html) — 2026-11-12, 3 real, withheld while the maintainers triage them
- [Every scan in the series]({{ '/' | relative_url }}) — 118 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 30 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — published as they were
