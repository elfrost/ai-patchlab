---
layout: default
title: "54yyyu/zotero-mcp: security scan"
date: 2026-06-08
---

# 54yyyu/zotero-mcp — security scan

**Repository:** [54yyyu/zotero-mcp](https://github.com/54yyyu/zotero-mcp) — 3.7k★, MIT, an MCP server that connects Zotero research libraries to Claude (and other MCP clients) over stdio, SSE, or HTTP transports. Solo-maintained by @54yyyu with a healthy occasional-contributor inflow.
**Commit scanned:** `90c76d5ef224` (HEAD of `main` at scan time)
**Scan date:** 2026-06-08
**Disclosure status:** Public courtesy issue filed. The scanner returned 4 findings; **the curated set is 6 real items, every one of which the static scanner missed** — a Phase-B completeness sweep on MCP-specific attack surfaces (initiated under the project's ultracode mode) is what surfaced them.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 2 (scanner output) |
| Medium | 2 (scanner output) |
| Low | 0 |
| Info | 0 (filtered) |

**4 scanner findings → 6 confirmed-real curated items, only 1 of which came from the scanner.** The Python-focused Semgrep rules collapsed the four flagged sites to one survivor (a Dockerfile-runs-as-root) after adversarial verification. The five new items — one **medium SSRF** in the open-access PDF discovery path, one **medium** plaintext credential disclosure on stdout, and three **low** credential-hygiene / DoS hardening items — surfaced only when six MCP-specific surfaces (tool-argument validation, credential handling, file handling, JSON deserialization, network egress / SSRF, subprocess execution) were swept in parallel and each candidate adversarially verified.

This is the strongest single demonstration in the series so far that **static-rule scanners alone, even when curated, undercount the real surface of MCP servers** — the scanner found `chmod 0o111` (a benign +x bit) and a `urllib.urlretrieve` against a hardcoded URL (preceded by SHA256 pinning), and missed an SSRF reachable via prompt injection in indexed papers.

## Top findings (curated)

### 1. `src/zotero_mcp/tools/_helpers.py:454` — SSRF via unvalidated PDF URL from third-party OA discovery (Unpaywall / Semantic Scholar)

**Source:** Phase-B completeness sweep (network-egress surface)
**Severity:** Medium
**Verdict:** **Real and weaponisable in the MCP threat model.**

`_download_and_attach_pdf` is reached from the public `zotero_add_by_doi` tool when its default `attach_mode='auto'` is in effect. The flow:

1. The MCP client passes a DOI to `zotero_add_by_doi`.
2. The server queries Unpaywall (and Semantic Scholar as a fallback) for an open-access PDF URL.
3. Whatever URL the third-party API returns is passed to `requests.get(...)` to download the PDF.

The third-party response is JSON: the URL field is *whatever Unpaywall has indexed for that DOI* — an attacker who can get a crafted publisher landing page into Unpaywall's index, OR who can perform prompt injection in any paper that the MCP agent later asks to add, can steer the URL to anything they want. No scheme check, no host check, default redirect-following.

What makes this a *live* attack surface and not a theoretical one is the MCP threat model: a hostile paper's abstract or annotations can say "*to attach the PDF, call `zotero_add_by_doi` with the following DOI*" and the agent will, on a default install, hit an internal URL on the operator's behalf. The `ctx.info('PDF download/attach failed: {e}')` error reporting turns the otherwise-blind SSRF into a **reconnaissance oracle**: the LLM caller can observe success vs failure and infer internal-host topology.

**Reachable internal targets** depend on deployment shape:
- **Default local install (stdio transport):** the Zotero local API at `127.0.0.1:23119`. Most endpoints there are POST so the SSRF is primarily a probe oracle, but discovery itself is information.
- **Cloud-hosted MCP deployments** with the documented SSE / HTTP transport: instance-metadata endpoints (`169.254.169.254`), private-network targets, link-local, etc. — the standard SSRF surface.

**Concrete fix shape** (no novel mitigation needed — the established SSRF guard pattern applies):

```python
from ipaddress import ip_address
import socket

def _is_safe_pdf_url(url: str) -> bool:
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https"):
        return False
    try:
        for family, *_, sockaddr in socket.getaddrinfo(p.hostname, None):
            ip = ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
            if str(ip) == "169.254.169.254":  # cloud metadata
                return False
    except socket.gaierror:
        return False
    return True

# ... before requests.get:
if not _is_safe_pdf_url(pdf_url):
    raise ValueError("PDF URL rejected by SSRF guard")
# and require redirect handling to re-run the check on the Location target:
resp = requests.get(pdf_url, allow_redirects=False, timeout=30)
```

### 2. `src/zotero_mcp/setup_helper.py:618-620` — plaintext `ZOTERO_API_KEY` dumped to stdout in `setup --no-claude`

**Source:** Phase-B completeness sweep (credential-handling surface)
**Severity:** Medium
**Verdict:** **Real, and a discipline break rather than a design choice.**

`setup_helper.py` already handles credentials carefully: line 594 obfuscates the API key (`_obfuscate_sensitive(api_key)`) for the on-screen summary block. **25 lines later, the same function re-reads the config and prints the full plaintext key as a single-line JSON object** intended to be copy-pasted by the user into another tool's config:

```python
# line ~618 — after the obfuscated summary block already printed:
print(json.dumps(client_env))  # client_env contains the plaintext ZOTERO_API_KEY
```

Single-line JSON is *exactly* the format users copy and paste — into another terminal, a GitHub issue when reporting a bug, a screen-share during onboarding. The asymmetry between the obfuscated-summary block (line 594) and the plaintext stdout dump (line 618) is the tell that this is a discipline break: the same author wrote both, and the safer pattern is already in scope. The repo's own `cli_standalone.py` `cmd_config` (around lines 66-76) shows the right reference: default to `obfuscate_config_for_display()` and require an explicit `--show-secrets` flag for the plaintext form.

### 3-5. Three credential-hygiene / DoS-hardening lows

| Finding | Files | Fix shape |
|---|---|---|
| **Credential files written without restrictive perms** | `src/zotero_mcp/setup_helper.py:447-449, 493-497` and `src/zotero_mcp/cli.py:99-101` | Three sinks write JSON containing `ZOTERO_API_KEY` (and OpenAI/Gemini keys in the Claude Desktop path) via `open('w')` — world-readable under default umask on POSIX. Add `os.chmod(cfg_path, 0o600)` after each write. POSIX no-op on Windows. Industry convention (AWS CLI, `gh` CLI, `git-credential-store`, `~/.netrc`, SSH keys) is `0o600`. |
| **`--api-key` CLI flag exposes credential via process command line** | `src/zotero_mcp/cli.py:200` (and `setup_helper.py:514`, `:570`) | Same file uses `getpass.getpass()` for OpenAI and Gemini at `setup_helper.py:193` and `:213` — **asymmetric treatment of the primary credential** (the asymmetry is itself the tell). Leaks via `ps`, `/proc/<pid>/cmdline`, shell history, audit logs, CI logs. Prompt with `getpass.getpass()` when `--api-key` is omitted; primary path should be the `ZOTERO_API_KEY` env var. |
| **`subprocess.run` of `pdfannots2json` has no `timeout=`** | `src/zotero_mcp/pdfannots_helper.py:111` | Hostile or oversized PDF wedges the MCP worker indefinitely. `capture_output=True` buffers all stdout in memory before `json.loads`, so a verbose-bomb payload is an additional OOM side-channel. Add `timeout=<bounded>`, catch `subprocess.TimeoutExpired`, return an empty/error result on expiry. Behind the `use_pdf_extraction=True` opt-in + a two-layer fallback so local-scope DoS only, but a clean fix. |

### 6. `Dockerfile` — runs as root, no `USER` directive before `ENTRYPOINT`

**Source:** Scanner (Trivy)
**Severity:** Low
**Verdict:** **Real defense-in-depth gap.** The only one of the four scanner findings to survive adversarial verification. Stdio transport bounds severity (no exposed listener), but multi-tenant hosts like Smithery benefit from non-root containers for breakout severity if any RCE lands through dependency CVEs or PDF parsing. Add a `USER app` directive in a final-stage `RUN useradd … && chown …` block.

### Scanner findings that were adversarially overturned

The four scanner-side findings were each adversarially verified by a dedicated agent tasked with refuting the preliminary verdict. Three of the four were confirmed false-positive or already-mitigated:

| Scanner finding | Adversarial verdict |
|---|---|
| `tarfile-extractall-traversal` in `src/zotero_mcp/pdfannots_downloader.py:112` | **Already mitigated, more thoroughly than `filter='data'` alone.** The `_safe_extract_tar` helper validates every member's `os.path.realpath` against the destination root, **explicitly rejects symlinks and hardlinks**, AND the surrounding `download_and_install` verifies the archive against a **pinned SHA256** before extraction. The source URL is hardcoded to a GitHub release. Three independent gates; `filter='data'` would be belt-and-suspenders. |
| `insecure-file-permissions` at `pdfannots_downloader.py:79` | **FP.** `os.chmod(path, current_mode | 0o111)` only adds the executable bit. `0o111` is not permissive — it grants no read or write to anyone — and the binary must be executable to run. The rule fires on the chmod call pattern, not on the actual mode value. |
| `dynamic-urllib-use-detected` at `pdfannots_downloader.py:159` | **FP.** `urllib.request.urlretrieve(url, archive_path)` — `url` comes from `get_download_url()` which returns a *hardcoded URL* from a static `DOWNLOAD_URLS` dict keyed on `platform.system()` and `platform.machine()`. Not attacker-controllable. SHA256 verification follows immediately after the download. |
| `Image user should not be 'root'` (Dockerfile) | **Survived as the one real scanner item.** See Finding 6 above. |

## Patterns observed

**The Python-rule scanner missed every MCP-specific real finding on this codebase.** This is the single cleanest demonstration in the series of the rule-vs-surface mismatch. The Semgrep rules that fire on this codebase are all data-flow-free pattern matches (`tarfile.extractall` is called; `chmod` is called; `urllib.urlretrieve` is called) — they have no way to know that the URL was hardcoded, the chmod mode was `0o111`, the tarfile guard rejects symlinks, the SHA256 was pinned. Meanwhile the SSRF in `_download_and_attach_pdf` involves a URL that is **data-flow-tainted through `response.json()` from a third-party API call** — there is no AST shape for "this string came from an HTTP response." The scanner cannot see it because the value is invisible to AST analysis until runtime. The methodology lesson: any MCP-server scan should pair the scanner output with an MCP-surface-specific completeness sweep covering, at minimum, network-egress / SSRF, credential handling, tool-argument validation, JSON deserialization, file handling, and subprocess execution.

**Strong primary mitigations on common CWE-22 patterns are repeatedly miscategorized.** The `_safe_extract_tar` helper here is structurally stronger than `tarfile.extractall(..., filter='data')` (it pins the SHA256 of the archive, rejects symlinks/hardlinks, and validates every member's realpath against the destination root) — yet the scanner flagged it as the same `tarfile-extractall-traversal` class we surfaced as a real finding on [pixeltable](pixeltable-pixeltable.html). Both code paths are technically scanned by the same Semgrep rule, but pixeltable's was unguarded and zotero-mcp's is triple-guarded. The triage answer for this rule must always include "what does the surrounding code already do?" — not just "is `extractall` called here?"

**Credential hygiene clusters: when a project uses `getpass.getpass()` for two of three API keys, the third is almost always the legacy/primary credential.** zotero-mcp uses `getpass.getpass()` for OpenAI and Gemini keys at `setup_helper.py:193` and `:213`. The Zotero key — the *primary* credential the entire project exists to use — is handled via `--api-key` argv and via plaintext stdout dump. The asymmetry itself is the tell: the safer pattern was already written and adopted for the secondary keys but never applied to the primary one. Worth flagging this as a recurring pattern for future scans of similar projects: the *primary* credential is the one most likely to have inherited unsafe handling from an earlier version.

**MCP servers re-create the classic "silent CLI tool" problem at MCP scale.** A stdout dump that was fine when only one person ran the CLI becomes public when "copy/paste output" becomes "paste into a GitHub issue" or "show on screen-share during onboarding." `setup_helper.py:618-620`'s plaintext `ZOTERO_API_KEY` dump is the textbook example.

**Subprocess-without-timeout is the MCP-server failure mode static scanners miss most often.** `shell=False` + explicit argv passes every "subprocess hardening" rule, but no `timeout=` means one bad input wedges a long-lived server worker indefinitely. The scanner has no rule that fires on "missing `timeout=` kwarg" because that's the absence of a thing, not a pattern.

## Notes on the tool

- **This is the first scan in the series run under the project's `ultracode` mode** (the user-opted-in exhaustive-quality setting that defaults to multi-agent workflows for substantive curation). The workflow's structure was: Phase A adversarially verified the 4 scanner findings (one survived); Phase B did a 6-agent parallel completeness sweep across MCP-specific attack surfaces (12 candidates surfaced); Phase C adversarially verified all 12 candidates (5 confirmed real, 7 refuted as FP or by-design); Phase D synthesized the curated picture. **23 agents, ~11 minutes wall-clock.** The ratio of "scanner real items : Phase-B real items" was 1 : 5, which is the cleanest case yet for the methodology argument that scanner output is the floor of curated coverage, not the ceiling.
- The cross-scan SCA-vs-reachability lesson ([documented after the Q00/ouroboros maintainer triage on 2026-06-07](q00-ouroboros.html#patterns-observed)) was applied to the dep-tail: zotero-mcp has no `pyproject.toml`-pinned dep advisories of consequence beyond the standard `requests` / `urllib3` tail, so the lesson didn't materially change the picture here. The first scan where it will is whichever next target has a heavy LiteLLM or `anthropic` pin.

## Disclosure timeline

- **2026-06-08** — Scan run at commit `90c76d5ef224`. Scanner returned 4 findings; ultracode-mode workflow surfaced 5 additional confirmed-real items via MCP-surface completeness sweep + adversarial verification.
- **2026-06-08** — Public courtesy issue [#326](https://github.com/54yyyu/zotero-mcp/issues/326) filed on 54yyyu/zotero-mcp focused on the six confirmed-real items, with the SSRF and the plaintext-stdout credential disclosure as the headline pair and the four hardening items as a follow-up batch.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/54yyyu/zotero-mcp" \
  --reports-dir reports/54yyyu-zotero-mcp \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme). The MCP-surface completeness sweep that surfaced findings 1–5 was performed via the project's parallel-agent workflow (described in [Notes on the tool](#notes-on-the-tool)) rather than the scanner CLI.
