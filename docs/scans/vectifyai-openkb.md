---
layout: default
title: "VectifyAI/OpenKB: security scan"
date: 2026-07-09
---

# VectifyAI/OpenKB - security scan

**Repository:** [VectifyAI/OpenKB](https://github.com/VectifyAI/OpenKB)
**Commit scanned:** `6774c593bdccc7ddc19b504214dbccfb7e9de82b`
**Scan date:** 2026-07-09
**Disclosure status:** public — post-only (clean scan; no upstream issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 8 |
| Medium | 15 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 23 (0 real after curation)

OpenKB is a CLI that compiles raw documents into a structured, interlinked
wiki-style knowledge base using LLMs, with PageIndex's vectorless retrieval for
long PDFs. Because it's a **CLI** — no server, no auth, no request handler — its
attack surface is document ingestion and its dependency tree, not a network
boundary. This is the **14th clean scan**: the code is clean, the maintainer
pins dependencies deliberately for supply-chain reasons, and the scary-looking
"high" dep advisories are transitive server/auth packages that a CLI never
reaches.

## Top findings

### 1. The two code findings are by-design and lint

- **File:** `openkb/url_ingest.py:240`, `openkb/visualize.py:6`
- **Tool:** semgrep (`dynamic-urllib-use-detected`, `python37-compatibility`)
- **Confidence:** high — by-design / FP
- **Why it matters / why it doesn't:** `url_ingest.py` fetches a URL the CLI user
  passed to `openkb add <url>` — a user-directed download (with a timeout), the
  same shape as `wget`, not a link-following crawler that a malicious document
  could steer. There's no SSRF here because the operator chooses the target and
  nothing auto-follows links out of ingested content. The other hit is a
  `python37-compatibility` lint on a modern-Python project. gitleaks found no
  secrets.

### 2. The "high" dep advisories are unreachable server/auth packages

- **File:** `uv.lock` (`starlette`, `python-multipart`, `pyjwt`)
- **Tool:** trivy
- **Confidence:** high — version-match, not reachable
- **Why it matters / why it doesn't:** trivy's highs are `starlette`
  (SSRF/Host-header), `python-multipart` (form-parsing DoS), and `pyjwt`
  (token-verification CVEs). All three describe a **web service** — an ASGI app
  parsing multipart forms, a server verifying JWTs. OpenKB is a CLI: it starts no
  `starlette` app, parses no multipart bodies, and verifies no JWTs. These
  packages arrive transitively (through the LLM/agent stack) and sit inert. The
  reachability question — "does this code path run here?" — answers no for every
  high.

### 3. The reachable deps are a deprecated PDF parser and HTTP-client DoS bumps

- **File:** `uv.lock` (`pypdf2` 3.0.1, `lxml-html-clean`, `aiohttp`)
- **Tool:** trivy + pip-audit
- **Confidence:** reachable, low severity
- **Why it matters:** The deps that *are* on OpenKB's path are the ingestion
  ones. `pypdf2` 3.0.1 (CVE-2023-36464 / PYSEC-2026-1835) parses user-supplied
  PDFs, so a crafted PDF can trigger the parser DoS — and `PyPDF2` is
  **deprecated** (renamed to `pypdf`), so it will get no further fixes.
  `lxml-html-clean` sanitizes ingested HTML; `aiohttp` (several CVEs) is the
  async HTTP client behind LLM calls and downloads. These are the reachable
  surface, and they're DoS/parsing-class, not RCE.
- **Recommendation:** Migrate `PyPDF2 → pypdf` (the maintained successor) since
  it's on the untrusted-PDF path, and refresh `lxml-html-clean` / `aiohttp`.

## Patterns observed

**"CLI, not server" is a reachability filter the scanner doesn't apply.** The
single most useful curation move here is noticing that OpenKB runs no web
service, which instantly demotes every `starlette` / `python-multipart` / `pyjwt`
advisory from "high" to "not reachable." This is the same version-match-vs-
reachability discipline the Ouroboros and Kiln scans used, but the tell is even
cleaner: an advisory whose entire premise is "an attacker sends an HTTP request"
is inert in a tool that has no HTTP listener. The reachable deps are the boring
ones — a PDF parser and an HTTP client — and they're where the (modest) real
work is.

**Deliberate pinning is a security posture, not drift.** OpenKB's `pyproject.toml`
opens with a comment that all dependencies are pinned exactly "supply-chain
caution — e.g. the litellm package-poisoning incident … bump deliberately after
vetting," with `litellm==1.87.2` pinned to a vetted release. That's the same
call the Ouroboros maintainer made (declining a fast `uv lock --upgrade` because
of the March-2026 litellm PyPI incident). So the dependency tail isn't neglect —
it's a maintainer who pins on purpose and vets before bumping. The right advice
is "the PDF parser is deprecated and on the untrusted path, prioritize that
one," not "run `--upgrade`."

**Clean code, security-aware maintainer, no filing.** Two semgrep hits (both
benign), no secrets, no `eval`/`exec`/`pickle` on untrusted input, and a
dependency posture that already reflects supply-chain awareness. There's no
real, reachable, undefended item, so this stands as a clean-scan write-up.

## Notes on the tool

- **A "no HTTP server" signal would auto-demote server-dep advisories.** If the
  scanner detected that a project imports no ASGI/WSGI framework and starts no
  listener, `starlette`/`python-multipart`/`uvicorn` CVEs could be tagged
  "framework present transitively, no server entrypoint found" instead of
  surfacing as highs. Pairs with the transport-reachability note from the
  tradingview-mcp scan.
- **`pypdf2` deprecation deserves its own flag.** The most actionable dep item
  wasn't the highest-severity one — it was a *medium* on a **deprecated** package
  sitting on the untrusted-input path. A "package is EOL/renamed" signal would
  rank it above the unreachable highs.
- **Honor an explicit pinning rationale.** The `pyproject.toml` comment states a
  deliberate supply-chain pinning policy. A dep report that reads that intent
  (or a `# pragma`-style marker) could soften "outdated" framing into "vet and
  bump the reachable ones."

## Disclosure timeline

- 2026-07-09 — scan run
- 2026-07-09 — public post (this page); post-only, no upstream issue filed

This is a post-only clean-scan write-up. The code is clean, the URL ingestion is
operator-directed (not SSRF), the high-severity dep advisories are unreachable
server/auth packages in a CLI, and the reachable deps are DoS/parsing-class
bumps — with a deprecated `PyPDF2` on the untrusted-PDF path as the one item
worth prioritizing. Nothing cleared the quality gate.

## Reproduce

```bash
git clone https://github.com/VectifyAI/OpenKB /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/vectifyai-openkb \
  --min-severity medium --ignore-samples
```
