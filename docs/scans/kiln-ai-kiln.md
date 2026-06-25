---
layout: default
title: "Kiln-AI/Kiln: security scan"
date: 2026-06-25
---

# Kiln-AI/Kiln - security scan

**Repository:** [Kiln-AI/Kiln](https://github.com/Kiln-AI/Kiln)
**Commit scanned:** `4e9bad4fb59d846950fa8d29de9b94c7feb20c2b`
**Scan date:** 2026-06-25
**Disclosure status:** public — post-only (commercial-backed / open-core; quality gate not met, no upstream issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 4 |
| High | 46 |
| Medium | 100 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 150 (0 real, reachable, undefended after curation)

Kiln is a mature open-core "AI workbench" — evals, prompt optimization, RAG,
fine-tuning, synthetic data, agents, and tools, with a desktop GUI, a local
REST server, and an MIT-licensed `kiln-ai` Python library. It runs locally and
brings your own API keys. The repo is a monorepo: a Python core (`libs/core`),
a Python server (`libs/server`), a desktop app with a Svelte/Vite frontend
(`app/web_ui`), and AI-agent dev tooling (`.agents/`).

The 150-finding count is almost entirely a dependency tail spread across four
lockfiles, and the headline of this scan is a reachability story: **the two
"critical" findings and the scariest highs are a `langchain` cluster that is a
test-only dependency** — not present in any shipped runtime path. What's left
is a transitive DoS/decompression tail and one genuinely useful process
observation about lockfile coverage.

## Top findings

### 1. The two criticals (`langchain-core` arbitrary-code-execution) are test-only

- **File:** `libs/core/uv.lock`, `libs/server/uv.lock` (`langchain-core` 0.3.x, serialization-injection RCE)
- **Tool:** trivy (dep) + reachability review
- **Confidence:** high that it is **not reachable in production**
- **Why it matters / why it doesn't:** "Arbitrary code execution via
  serialization injection" on a model-tooling project reads as a five-alarm
  fire. But every one of the eleven `import langchain` / `from langchain`
  sites in the repo is a `test_*.py` file (`test_g_eval.py`,
  `test_prompt_adaptors.py`, `test_run_api.py`, `test_data_gen_api.py`, …).
  Kiln's actual model-adapter layer is **LiteLLM-based**, not LangChain. The
  RCE CVE requires calling `langchain_core.load.loads/load` on
  attacker-controlled data; Kiln's shipped code never imports the module at
  all. The same applies to the LangChain template-injection, `load_prompt`
  path-traversal, and `langchain-text-splitters` XXE highs — all test-scope.
- **Recommendation:** None reachable. If LangChain stays a test dependency,
  the cluster is informational. (Bumping it is still tidy, and trivial since
  it's dev-only.)

### 2. `langsmith` CVEs are transitive, not directly used

- **File:** `libs/core/uv.lock` / `libs/server/uv.lock` (LangSmith SDK file-read + manifest deserialization)
- **Tool:** trivy
- **Confidence:** high — version-match only
- **Why it matters:** The "arbitrary server-side file read" and "deserializes
  untrusted manifests" advisories sound server-reachable. But `langsmith`
  appears zero times in Kiln's source — it arrives purely as a `langchain-core`
  transitive. No `Client.pull_prompt` / tracing-middleware path is wired.
- **Recommendation:** Falls out with the LangChain test-dep cleanup.

### 3. `starlette` advisories are real server deps, but the server is localhost-bound

- **File:** `libs/server/uv.lock`, root `uv.lock` (`starlette` 0.x — SSRF/NTLM via UNC in StaticFiles, Range-header DoS, Host-header bypass)
- **Tool:** trivy
- **Confidence:** reachable-in-principle, low-confidence exploit
- **Why it matters:** Unlike LangChain, `starlette` *is* a runtime dependency —
  it backs the FastAPI REST server. The SSRF/NTLM-via-UNC CVE, though, needs a
  `StaticFiles` mount serving attacker-influenced paths on Windows, and the
  DoS/Host-header issues need the server exposed to a hostile client. Kiln's
  server binds to `localhost:8757` as a desktop companion (the OAuth callback
  URL confirms it), not an internet-facing service.
- **Recommendation:** Bundle into a Python-lockfile refresh (see below). The
  real local-server concern is the next item, not these.

### 4. Local-server hardening: MCP DNS-rebinding default + a localhost API

- **File:** root `uv.lock` (`mcp`: DNS-rebinding protection disabled by default)
- **Tool:** trivy
- **Confidence:** real class, low individual severity
- **Why it matters:** Kiln runs a local HTTP server and integrates MCP tools.
  A localhost server is reachable from any web page the user visits via
  DNS-rebinding unless it validates `Host`/`Origin`. The `mcp` advisory flags
  exactly this default. For a desktop app exposing a control-plane API on
  `localhost`, an `Origin`/`Host` allowlist is the right defense-in-depth.
- **Recommendation:** Confirm the FastAPI server (and any MCP transport)
  validates `Origin`/`Host` for state-changing routes. This is the one item
  here with a genuinely Kiln-specific threat model.

### 5. Hardcoded GitHub App client secret — documented by-design

- **File:** `app/desktop/git_sync/oauth.py:23` (`GITHUB_CLIENT_SECRET`)
- **Tool:** semgrep (`detected-generic-secret`) + gitleaks
- **Confidence:** real published secret, reasoned tradeoff
- **Why it matters:** A GitHub App client secret is committed in plaintext. The
  maintainer pre-empted the finding with an explicit comment: this is a GitHub
  App user-access-token (OAuth) flow in a *distributed desktop binary*, where
  the secret cannot be kept confidential on the user's machine, and **PKCE
  protects the code exchange**. That's the standard native/public-client
  posture, and the reasoning is sound.
- **Recommendation:** None to file — the tradeoff is documented and PKCE is in
  place. The residual (a real published secret) is inherent to embedding any
  OAuth secret in a shipped client; a server-side token-exchange proxy would
  remove it entirely if the threat model ever tightens. The other two gitleaks
  hits are test fixtures (`test_litellm_extractor.py`, `test_config.py`) — FP.

## Patterns observed

**The count is a reachability illusion, and the criticals are the clearest case
yet.** Trivy returns 4 critical / 46 high, and the two criticals are
`langchain-core` RCE — on a repo whose production code never imports LangChain.
This is the same lesson as the Ouroboros, mistral-vibe, and openmed scans, but
sharper: here the dangerous dependency isn't just unreachable, it's *test-only*.
The first curation move on a fat dependency tail is always "is the flagged
package in a shipped import path?" — and for the scariest items on Kiln, the
answer is no.

**The real signal is a lockfile-coverage asymmetry.** Kiln has no
`.github/dependabot.yml`; the Dependabot PRs that *are* landing (undici,
dompurify, vite) come from GitHub's automatic security updates against the npm
`app/web_ui/package-lock.json`. Those updates don't parse `uv.lock`, so the
**three Python lockfiles — root, `libs/core`, `libs/server` — drift
uncovered** while the JS frontend stays patched. Most of what's drifting is a
transitive DoS/decompression tail (`urllib3` ×4, `aiohttp`, `orjson`, `h11`,
`pillow`, `nltk`) that is low-risk for a local BYO-keys tool, but `starlette`
and `mcp` are runtime server deps where staying current actually matters.
Adding `pip`/`uv` ecosystems to a Dependabot config would close the gap with
the same hands-off cadence the frontend already enjoys.

**The maintainer is clearly security-aware where it counts.** The OAuth secret
carries a correct PKCE rationale; the frontend is on auto-updates; the code
that matters (the LiteLLM adapter layer) is clean of the flagged patterns. This
is a well-run open-core project — the residual is process hygiene on the Python
side, not a vulnerability. Combined with the commercial backing (Kiln Pro), the
disciplined call is a post-only write-up, not a courtesy issue: there is no
real, reachable, undefended item that clears the bar.

## Notes on the tool

- **Test-only dependencies should be flagged as such in dep-CVE rows.** AI
  PatchLab reported `langchain-core` RCE as critical without noting that the
  package is imported only from `test_*.py`. A dependency that appears solely
  in test files (or a `[dev]`/`[test]` extra) is a different risk tier than a
  runtime dep. Backlog: cross-reference each flagged package against the set of
  non-test import sites and annotate "test/dev-scope" — it would have collapsed
  the two criticals here to informational automatically.
- **Per-lockfile attribution + a coverage check would surface the real story.**
  The four lockfiles (`uv.lock` ×3 + `package-lock.json`) were flattened into
  one list. Grouping findings by lockfile, and noting which lockfiles a
  `dependabot.yml` actually covers, is what turned this scan from "150 scary
  CVEs" into "the Python locks aren't on Dependabot." Backlog item.
- **`detected-generic-secret` / gitleaks fired 1 real + 2 FP.** The real hit
  was a documented-by-design OAuth secret; the two FPs were test fixtures.
  Consistent with the credential-layer FP pattern across the series — a
  by-design/test-fixture annotation pass would help.
- **`.agents/` tooling scripts are out-of-scope noise.** Six `dynamic-urllib`
  warnings came from `.agents/scripts/*` (Claude/Codex dev tooling), not
  shipped product code. The scanner should treat `.agents/` like `tests/` for
  candidate-FP flagging.

## Disclosure timeline

- 2026-06-25 — scan run
- 2026-06-25 — public post (this page); post-only, no upstream issue filed

This is a post-only write-up. Curation found no real, reachable, undefended
item that clears the quality gate — the criticals are a test-only LangChain
dependency, the server CVEs are localhost-bound, and the OAuth secret is a
documented PKCE-protected tradeoff. The one actionable residual (wiring
Dependabot for the three Python lockfiles) is process hygiene on a
commercial-backed project that already runs frontend auto-updates, below the
bar for an unsolicited issue.

## Reproduce

```bash
git clone https://github.com/Kiln-AI/Kiln /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/kiln-ai-kiln \
  --min-severity medium --ignore-samples
```
