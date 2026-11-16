---
layout: default
title: "ucbepic/docetl: security scan"
description: "Security scan of ucbepic/docetl: 124 findings, 1 real — and no tool ranked it — an agentic map-reduce / document-ETL engine (3.9k★"
date: 2026-07-21
---

# ucbepic/docetl — security scan

**Repository:** [ucbepic/docetl](https://github.com/ucbepic/docetl)
**Commit scanned:** `ae7f10f1ba35`
**Scan date:** 2026-07-21
**Disclosure status:** ✅ **resolved** — [filed ucbepic/docetl#505](https://github.com/ucbepic/docetl/issues/505) on the day of the scan; a contributor's fix for the file read/write was merged 116 days later in [#507](https://github.com/ucbepic/docetl/pull/507) and the issue closed as completed. Re-verified by this series against the merged code. The fix confines paths; it adds no authentication and leaves the URL-ingest SSRF in place, and both are recorded below as open.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 55 |
| Medium | 68 |
| Low | 0 |
| Info | 0 |

**Total findings:** 124 (1 real, and the scanner didn't rank it)

## Top findings

### 1. Unauthenticated arbitrary file read/write in the `/fs` filesystem router — *scanner-silent*

- **File:** `server/app/routes/filesystem.py:218` (`read-file`), `:234` (`read-file-page`), `:306` (`check-file`), `:194` (`write-pipeline-config`), `:293` (`save_workspace`)
- **Tool:** none — surfaced by hand; Semgrep's 14 `path-join-resolve-traversal` hits all landed in the Next.js frontend, not this Python backend
- **Confidence:** high
- **Why it matters:** every one of those endpoints takes a raw client-supplied `path` / `namespace` / `workspace_id` and hands it straight to `Path(...)` with **no base-directory confinement and no authentication**. `GET /fs/read-file?path=<abs>` returns any file the process can read; `read-file-page` and `check-file` are the same with a paging/oracle twist; `write-pipeline-config` and `save_workspace` build the write path from an unsanitized `namespace`/`workspace_id`, so `../` escapes the `.docetl` root and writes client-controlled YAML anywhere. The tell is `serve-document/{path}` one function up (`:262`), which *does* carry an `if ".." in path` guard — the pattern is understood, just not applied to the raw-path endpoints.
- **Recommendation:** resolve every request path against a fixed allowed root and reject anything that escapes it (`Path(root, user).resolve().is_relative_to(root.resolve())`), and put the whole `/fs` router behind an auth dependency before any non-loopback bind.

### 2. SSRF in `/fs/upload-file` (URL ingest)

- **File:** `server/app/routes/filesystem.py:83`
- **Tool:** none (Semgrep flagged the *write*, `request-data-write`, not the fetch)
- **Confidence:** high
- **Why it matters:** `upload_file` accepts a `url` form field and does `httpx.AsyncClient().stream("GET", url, follow_redirects=True)` with no scheme or host allowlist. Cloud-metadata and internal JSON APIs return valid JSON, which then passes `validate_json_content` and is written to disk — so this is a *fetch-and-store* SSRF, not just a blind one, and `follow_redirects=True` defeats a naive "only public URLs" client check.
- **Recommendation:** allowlist schemes to `http(s)`, resolve the host and block private/link-local/loopback ranges (incl. after redirects), or drop URL ingest server-side and fetch from the browser.

### 3. Dependency drift across two lockfiles, no Dependabot

- **File:** `uv.lock`, `website/package-lock.json`
- **Tool:** trivy
- **Confidence:** medium
- **Why it matters:** 3 critical / 102 high across the two ecosystems — but reachability splits them. The Python "critical" is `nltk` 3.9.2 Zip-Slip (CVE-2025-14009), which needs a malicious NLTK *data* archive and is low-reachability (corpora come from the official index); the two npm criticals (`tar`, `protobufjs`) are frontend build-chain. No `dependabot.yml` in the repo, so neither lockfile is on auto-updates.
- **Recommendation:** bump `nltk`→3.9.3, `tar`→7.5.19, `protobufjs`→7.5.5; add a two-ecosystem `dependabot.yml` (pip + npm).

## Patterns observed

DocETL is a declarative + agentic map-reduce engine — its whole reason to exist is running LLM-authored data-processing pipelines, so the `exec(code)` in `code_operations.py:158` and the `asteval`/`eval` fallback in `validation.py:132` read as alarms but are the **documented programming model**: a pipeline author writes a `transform` function or a filter expression and the engine runs it. That's the same "the dangerous call *is* the product" shape as [ag2](ag2ai-ag2.html) and [datachain](datachain-ai-datachain.html) — by-design for a *trusted local user*, and not a finding on its own.

What makes docetl different is that the trust assumption is quietly broken by how it ships. The `/fs` router assumes it's talking to a friendly localhost browser, so it never confines a path or checks a caller. On bare metal that assumption mostly holds — `.env.example` binds `BACKEND_HOST=localhost` and the CORS default is a tight `localhost:3000` allowlist (both worth crediting). But the recommended DocWrangler deployment is the shipped `docker-compose.yml`, and there `BACKEND_HOST=0.0.0.0` with **no authentication anywhere in the server**. At that point `read-file`, the pipeline-execution route (`pipeline.py` drives `DSLRunner` straight from a request-supplied `yaml_config`, and a pipeline can carry `code` operators), and the SSRF ingest are all reachable from the network — and the `docetl-aws` compose profile bind-mounts `~/.aws:ro` into the container, so an unauthenticated file read is a cloud-credential read. The file-read is the floor here; the code-operator model is the ceiling.

This is the [optillm](algorithmicsuperintelligence-optillm.html) / [zotero-mcp](54yyyu-zotero-mcp.html) egress-and-exposure lesson pointed inward: the finding that matters isn't in the AI machinery the scanner obsesses over, it's in the mundane file/URL plumbing bolted onto the side of it. Reachability discipline cuts both ways — it demoted the nltk "critical" to a footnote *and* promoted a zero-tool-hits file-read to the headline.

## Notes on the tool

- **Semgrep ranked the wrong path-traversal.** All 14 `path-join-resolve-traversal` hits fired on the TypeScript frontend (`website/src/...`); the Python `FileResponse(path)` / `Path(path)` sinks in `server/app/routes/filesystem.py` produced *zero* hits. The real unauthenticated file read was invisible to the scanner — a repeat of the "scanner under-count, run the manual surface sweep" pattern from [zotero-mcp](54yyyu-zotero-mcp.html). **Backlog:** a Python rule for `FileResponse`/`open`/`Path` fed by a FastAPI query/form param without a confinement check.
- **Severity ranking was dep-dominated.** The report's headline "critical" was a low-reachability `nltk` Zip-Slip; the actual high-severity issue carried no tool severity at all because no tool raised it. The severity table describes the dependency tree, not the app.
- **Gitleaks:** 1 hit, a `docs/python/examples.md` placeholder (`split_0_chunk_num`) — FP, doc example.
- CI `github-actions-mutable-action-tag` (13) + `gha-curl-pipe-shell` (3) are the usual workflow-hardening tail, not the story here.

## Resolution

**What shipped.** [#507](https://github.com/ucbepic/docetl/pull/507) (+442/−98, `server/app/routes/filesystem.py` plus a new `tests/test_filesystem_security.py`) was written by contributor [rohankumardubey](https://github.com/rohankumardubey) and merged by the maintainer. Every `/fs` route now takes its path through one helper, `resolve_storage_path`. The helper canonicalises the path with `resolve()` and refuses anything outside `$DOCETL_HOME_DIR/.docetl`. The check is `relative_to`, which compares path components, not string prefixes. Single file and directory names go through `resolve_storage_child`, which refuses separators, `..` and NUL bytes. `serve-document` no longer has its own substring `".."` check, the weaker guard the report had pointed at; it uses the same helper as the other routes. The new tests cover traversal, absolute paths outside the root, sibling-prefix paths and symlink escapes, and they check that legitimate nested paths still work.

**Re-verified 2026-11-15, as a differential.** The five path helpers were extracted from `filesystem.py` at the merge commit `8163c31e` and run against a scratch storage root. Each probe was also run through the pre-fix behaviour, where the client's path went to `Path(path)` unchecked.

| Probe | Before the fix | After the fix |
| --- | --- | --- |
| `../outside.txt` | escapes the root | rejected (400) |
| `ns/../../outside.txt` | escapes the root | rejected (400) |
| an absolute path outside the root | escapes the root | rejected (400) |
| a sibling prefix, `~/.docetl-evil/x.txt` | escapes the root | rejected (400) |
| relative and absolute paths inside the root | served | served |

A `../..` namespace, an empty namespace, and file names containing `../`, `..\` or a NUL byte are all rejected too. The symlink case could not run on the Windows machine used here (no symlink privilege), but the project's own tests cover it. The container sets `DOCETL_HOME_DIR=/docetl-data`, which puts the `~/.aws` mount of the `docetl-aws` profile outside the root, so the cloud-credential read described above is closed.

**Still open.** The pull request describes itself as covering "the filesystem-confinement portion of #505". It took neither of the other two recommendations, and the maintainer closed the issue anyway, so the following are a decision on record, not an open thread:

- **No authentication.** At `8163c31e` the server still has no auth dependency (`server/app/main.py` adds only CORS), and `docker-compose.yml` still binds the backend to `0.0.0.0`. On that deployment, anyone who can reach the backend port can still read and write files *inside* the storage root and run pipelines, `code` operators included.
- **The URL-ingest SSRF.** `/fs/upload-file` still fetches a caller-supplied `url` with `follow_redirects=True` and no scheme or host check, and stores the body when it parses as JSON.
- **Dependencies.** `nltk` is still 3.9.2 in `uv.lock`, and there is still no `dependabot.yml`.

The bare-metal default still binds to loopback (`BACKEND_HOST` defaults to `127.0.0.1`), so all three matter mainly for the container deployment. This counts as the series' 30th fix because the issue closed as completed and the arbitrary host file read and write that this write-up led with is gone.

## Disclosure timeline

- 2026-07-21 — scan run, curation, focused issue [ucbepic/docetl#505](https://github.com/ucbepic/docetl/issues/505) filed upstream (no private security channel is published; the finding requires the operator to expose the server, and the report leads with the fix, not an exploit chain)
- 2026-07-24 — a contributor opens [#507](https://github.com/ucbepic/docetl/pull/507), "fix(server): confine filesystem routes to storage root", scoped to the confinement part of the report
- 2026-11-14 — **fixed**: #507 merged by the maintainer (merge commit `8163c31e`), and #505 closed as completed forty minutes later
- 2026-11-15 — re-verified by this series against the merged code (see Resolution); authentication and the URL-ingest SSRF recorded as still open

## Reproduce

```bash
git clone https://github.com/ucbepic/docetl /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/ucbepic-docetl --min-severity medium
```

---

## More from this series

- **Next scan:** [mixelpixx/KiCAD-MCP-Server](mixelpixx-kicad-mcp-server.html) — 2026-07-22, 0 real
- **Previous scan:** [ModelEngine-Group/nexent](modelengine-group-nexent.html) — 2026-07-20, 0 real
- [Every scan in the series]({{ '/' | relative_url }}) — 105 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 24 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — 40 of them, published as they were
