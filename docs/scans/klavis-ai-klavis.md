---
layout: default
title: "Klavis-AI/klavis: security scan"
date: 2026-05-20
---

# Klavis-AI/klavis — security scan

**Repository:** [Klavis-AI/klavis](https://github.com/Klavis-AI/klavis) — 5.7k★, Apache-2.0, an MCP integration platform — a monorepo of 50+ Model Context Protocol servers plus client SDKs.
**Commit scanned:** `669e95dc716b` (HEAD of `main` at scan time)
**Scan date:** 2026-05-20
**Disclosure status:** Public courtesy issue filed on the Klavis repo. Every finding traces to a published CVE in a dependency — no private coordination required.

## Summary

| Severity | Count (raw) | Count (after ignore-file) |
| --- | ---: | ---: |
| Critical | 22 | 22 |
| High | 855 | 703 |
| Medium | 679 | 624 |
| Low | 0 | 0 |
| Info | 0 (filtered) | 0 (filtered) |

**1,556 raw findings → 1,349 after suppressing `docs/**` and `examples/**`. This is the largest finding count in the series by an order of magnitude — and unlike [PraisonAI](mervinpraison-praisonai.html) (where volume was mostly false-positive SQL noise), here the volume is *real*: ~1,190 Trivy dependency findings across the monorepo's 50+ independently-managed sub-projects.**

Klavis is structurally different from every prior target. It is not one application — it is a monorepo where each `mcp_servers/<service>/` directory is its own independently-dependency-managed project, each with its own `package-lock.json`, `requirements.txt`, or `uv.lock`. The security story here is **dependency drift at monorepo scale**: 50+ sub-projects, each pinning dependencies independently, collectively accumulating into a large surface of known-CVE versions.

## Top findings (curated)

### 1. 22 critical dependency CVEs — three of them matter a lot for an MCP platform

All 22 criticals are Trivy-surfaced published CVEs in dependency lockfiles. Grouped by package:

| Package | Count | CVE | Why it matters |
| --- | ---: | --- | --- |
| **authlib** | 3 | [CVE-2026-27962](https://avd.aquasec.com/nvd/cve-2026-27962) | **Authentication bypass via JWK Header Injection.** Prior to 1.6.9, an *unauthenticated* attacker can forge arbitrary JWT tokens that pass signature verification when `key=None` is passed to a JWS deserialization function. Affects `google_cloud_toolathlon`, `Poste.io`, and `excel` MCP servers. |
| **fastmcp** | 3 | [CVE-2026-32871](https://avd.aquasec.com/nvd/cve-2026-32871) | **Authenticated SSRF via path traversal** in OpenAPI path parameters. Prior to 3.2.0, the `OpenAPIProvider`'s `_build_url()` can be coerced into requests to unintended backends. Affects the same three servers. |
| h11 | 8 | malformed Chunked-Encoding body acceptance | Request-smuggling-adjacent; fix is a version bump. |
| form-data | 4 | unsafe random boundary generation | |
| basic-ftp | 2 | path-traversal file overwrite | |
| fast-xml-parser | 1 | XSS via improper handling | |
| excel-mcp-server | 1 | path traversal | |

The **authlib** and **fastmcp** criticals are the ones to fix first. An MCP server is, by definition, a thing that receives tool-invocation requests and acts on them — an auth-bypass or an SSRF in that layer is directly in the threat path. Both fixes are single-line dependency bumps: `authlib >= 1.6.9`, `fastmcp >= 3.2.0`.

### 2. The MCP SDK's own advisories propagate across ~60 sub-projects

**Tool:** Trivy (high confidence — named advisories)
**Verdict:** Real, and structurally interesting.

Two advisories against the MCP SDKs themselves show up at scale:

- **[CVE-2025-66416](https://avd.aquasec.com/nvd/cve-2025-66416)** — the MCP Python SDK (`mcp` on PyPI) does **not enable DNS-rebinding protection by default** for HTTP-based servers prior to 1.23.0. An HTTP MCP server on localhost without authentication is reachable by a malicious web page via DNS rebinding. Surfaces in ~59 sub-project lockfiles.
- **ReDoS in the MCP TypeScript SDK** (`@modelcontextprotocol/sdk`) — ~20 sub-projects.

Because Klavis *is* an MCP platform, the MCP SDK is its single most-depended-on package — so a single SDK advisory multiplies across the whole monorepo. The fix is centralized in principle (bump the SDK pin everywhere) but mechanically spread across ~60 lockfiles. This is the strongest argument in the scan for **monorepo-wide dependency automation** (see below).

### 3. ~135 Dockerfiles run as root

**Tool:** Trivy (`missing-user` / `missing-user-entrypoint`, medium confidence)
**Verdict:** Real best-practice, at monorepo scale.

Each MCP server ships its own `Dockerfile`, and ~135 of them end without a `USER` directive — every containerized MCP server runs as root. The fix is one mechanical pattern applied broadly:

```dockerfile
RUN groupadd -r app && useradd -r -g app -d /app app
USER app
```

For an MCP platform this matters more than for a typical web app: MCP servers execute tool calls — file operations, shell commands, API requests — so "container compromise" and "runs as root" compound. A shared base image with the `USER` directive baked in would fix all ~135 at once and prevent the next server from regressing.

### 4. 41 secret findings — mixed

**Tool:** Gitleaks
**Verdict:** Mostly false positives (doc-style `curl -H "Authorization: Bearer <token>"` patterns that survived into non-`docs/` files, placeholder `.env.example` values), but 41 is too many to wave away wholesale. The courtesy issue recommends a Gitleaks pass with a project `.gitleaksignore` so the real signal — if any — isn't buried. This scan did not surface a confirmed live credential, but the volume itself is a triage cost worth removing.

## Patterns observed

**Monorepo dependency drift is a distinct failure mode, and Klavis is a clean specimen of it.** Every prior scan in this series was one application (or a small cluster of packages) where dependency findings, when they appeared at all, were a short list — [guardrails' 7 litellm CVEs](guardrails-ai-guardrails.html) was the prior high-water mark. Klavis has 50+ sub-projects, each with an independent lockfile, none of them on a shared dependency-update cadence. The result isn't that any one server is badly maintained — it's that *the aggregate* drifts, because no single lockfile is anyone's daily concern. 1,190 Trivy findings is what dependency entropy looks like when it's allowed to run across 50 lockfiles for a year.

**The fix is process, not patches.** Hand-bumping 22 critical CVEs clears today's criticals; it does nothing about the drift that produced them. The durable fix is monorepo-wide dependency automation — Dependabot or Renovate with a config that covers every `mcp_servers/*/` sub-directory — plus a shared Docker base image so the `USER` directive and a pinned-SDK floor are defined once. The courtesy issue leads with this recommendation rather than the 22-item patch list, because the patch list regenerates itself in three months otherwise.

**Volume is not severity, but volume is not nothing either.** [The PraisonAI scan](mervinpraison-praisonai.html) had 489 findings that curated down to 5 real items — there, volume was noise. Klavis has 1,349 findings and the volume is *real*: these are named CVEs in shipped dependency versions, not scanner conservatism. The curation work here isn't "which of these are false positives" — it's "which of these are reachable enough to fix this week" (the authlib/fastmcp/MCP-SDK criticals) versus "which are part of the standing drift the automation will handle" (the long tail of axios/minimatch/urllib3/path-to-regexp transitive bumps).

**`--ignore-file` paid for itself again.** Suppressing `docs/**` and `examples/**` removed 207 findings — the `curl -H "Authorization: Bearer ..."` documentation examples and the example-integration projects' own lockfiles — none of which are Klavis's deployed surface. Second monorepo-scale scan ([after PraisonAI](mervinpraison-praisonai.html)) where the feature was load-bearing for keeping the curation tractable.

## Notes on the tool

This scan stress-tested AI PatchLab harder than any prior one. Backlog items, sharpened:

- **Cross-lockfile dependency deduplication is now the top priority.** The MCP Python SDK DNS-rebinding advisory is reported ~59 times — once per sub-project lockfile that pins `mcp`. The *vulnerability* is one advisory; the *fix surface* is 59 files. The report should present it as "1 advisory, 59 affected lockfiles" with the file list collapsed, not 59 separate findings. This is the single biggest readability win available.
- **A severity-ordered, dedup'd "dependency summary" section** would make a 1,300-finding report usable. Right now the 22 criticals are scattered through the JSON; they should be a table at the top.
- **The `.` file field on Trivy/dep-scan findings** (still showing the resolution root rather than the specific lockfile) is now actively painful at this scale — the post had to reconstruct which sub-project each finding belongs to from the raw JSON.

## Disclosure timeline

- **2026-05-20** — Scan run at commit `669e95dc716b`; `docs/**` + `examples/**` suppressed; findings triaged.
- **2026-05-20** — Public courtesy issue filed on Klavis-AI/klavis, leading with the dependency-automation recommendation and the 22 critical CVEs. All findings trace to published CVEs; no private coordination required.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/Klavis-AI/klavis" \
  --reports-dir reports/klavis-ai-klavis \
  --min-severity medium \
  --ignore-file reports/klavis-ai-klavis/.aipatchlabignore
```

The `.aipatchlabignore` used (`docs/**`, `examples/**`, `LLM.md`) is in the report directory; without it the raw scan reports 1,556 findings.

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
