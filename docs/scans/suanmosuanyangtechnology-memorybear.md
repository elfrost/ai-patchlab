---
layout: default
title: "SuanmoSuanyangTechnology/MemoryBear: security scan"
description: "Security scan of SuanmoSuanyangTechnology/MemoryBear: 196 findings, 3 named critical CVEs in a stale api/uv.lock (pytorch RCE-class, fastmcp SSRF"
date: 2026-06-01
---

# SuanmoSuanyangTechnology/MemoryBear — security scan

**Repository:** [SuanmoSuanyangTechnology/MemoryBear](https://github.com/SuanmoSuanyangTechnology/MemoryBear) — 4.2k★, Apache-2.0, an AI memory-management framework ("Perceive · Extract · Associate · Forget") with a memory engine, RAG ingestion pipeline, and an isolated sandbox runner for tool execution.
**Commit scanned:** `9e4a35a7e831` (HEAD of `main` at scan time)
**Scan date:** 2026-06-01
**Disclosure status:** 📝 **Acknowledged (fix pending).** Public courtesy issue ([#1296](https://github.com/SuanmoSuanyangTechnology/MemoryBear/issues/1296)) filed on the MemoryBear repo. The maintainer closed it as completed on 2026-06-12 with an acknowledgment and stated intent to review the advisories and add Dependabot — but as of that close **no fix had landed yet** (the pinned versions are unchanged and no `dependabot.yml` is present). Recorded honestly as an acknowledgment, not a verified resolution. Scope was kept tight: one focused note on the dependency-advisory tail, with the recurring SQL-text class and a methodology note on Jinja2-for-prompt-templates left to this write-up.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 5 |
| High | 52 |
| Medium | 139 |
| Low | 0 |
| Info | 0 (filtered) |

**196 total findings. After curation: the real actionable surface is a stale `api/uv.lock` carrying ~60 named CVE advisories — including three criticals (`pytorch` CVE-2025-32434, `fastmcp` SSRF CVE-2026-32871, `nltk` Zip-Slip RCE CVE-2025-14009) — that a single `uv lock --upgrade` pass would clear most of, on a repo with no Dependabot configured. Almost everything else is either the recurring SQL-text identifier class (5 sites, mostly migrations), a methodologically interesting Jinja2-for-LLM-prompts false-positive cluster, or sandbox/runner code where the flagged behavior is by-design.**

## Top findings (curated)

### 1. `api/uv.lock` — ~60 named CVE advisories across the dependency tree (3 critical)

**Tool:** Trivy
**Verdict:** **Real and the highest-impact item.** No Dependabot is configured on this repo, so this tail has been accumulating uncollected.

The three criticals are the standouts:

| CVE | Package | Class |
|---|---|---|
| [CVE-2025-14009](https://github.com/advisories?query=CVE-2025-14009) | `nltk` | Zip Slip → code execution. Path traversal during zip-archive extraction reaches arbitrary file write / executable drop. Real exploitability against any path that asks `nltk` to extract a downloaded resource. |
| [CVE-2026-32871](https://github.com/advisories?query=CVE-2026-32871) | `fastmcp` | Authenticated Server-Side Request Forgery in FastMCP. Same advisory we flagged on [Klavis](klavis-ai-klavis.html) — fastmcp pinned past the fix is a recurring item across MCP-server projects. |
| [CVE-2025-32434](https://github.com/advisories?query=CVE-2025-32434) | `pytorch` | PyTorch RCE-class. Standard "bump past the fix" item. |

The high-severity tail is mostly the standard dependency pile, but a handful are worth naming because they're useful to anyone running similar stacks:

- `mako` [CVE-2026-41205](https://github.com/advisories?query=CVE-2026-41205) (path traversal via backslash URI on Windows),
- `simpleeval` [CVE-2026-32640](https://github.com/advisories?query=CVE-2026-32640) (sandbox bypass — relevant for a project that ships a sandbox runner),
- `starlette` [CVE-2025-62727](https://github.com/advisories?query=CVE-2025-62727) (Range-header DoS),
- `pyjwt` [CVE-2026-32597](https://github.com/advisories?query=CVE-2026-32597),
- `cryptography` [CVE-2026-26007](https://github.com/advisories?query=CVE-2026-26007),
- 4× `nltk` highs (additional path-traversal / DoS classes),
- 2× `urllib3` highs, 2× `pyasn1` highs, `lxml`, `tornado`, `langchain`, `langsmith-sdk`, etc.

Plus the medium tail (~16× `pypdf`, `aiohttp`×4, `Pillow`×3, etc.).

A single `uv lock --upgrade` pass clears most of this. Wiring Dependabot (or Renovate) would keep it cleared.

### 2. 5× SQL identifier interpolation via `text(f"…")`

**Files:** 4× `api/migrations/versions/915bed077f8d_202601281340.py` (the schema-init migration) and 1× `api/app/models/tool_model.py:190`.
**Tool:** Semgrep (`avoid-sqlalchemy-text` + `sqlalchemy-execute-raw-query`)
**Verdict:** **Same class as on seven prior scans — gated today, brittle to future input-source changes.**

The migrations use `text(f"… {identifier} …")` for schema operations with hardcoded identifiers — the textbook deterministic-input pattern. The one runtime site (`tool_model.py:190`) is a SQLAlchemy column `server_default` that interpolates a Python enum constant:

```python
source_channel = Column(
    String(50),
    default=MCPSourceChannel.SELF_HOSTED,
    server_default=text(f"'{MCPSourceChannel.SELF_HOSTED}'"),
    ...
)
```

Both are config-controlled at compile time. The defensible long-term shape is the `quoted_name()` / `Identifier()` pattern, but the realistic exploit window today is the same as on [Upsonic](upsonic-upsonic.html), [PraisonAI](mervinpraison-praisonai.html), [airweave](airweave-ai-airweave.html), [honcho](plastic-labs-honcho.html), [dstack](dstackai-dstack.html), [pixeltable](pixeltable-pixeltable.html), and [semantic-router](aurelio-labs-semantic-router.html): not exploitable, but brittle.

### 3. 37× `direct-use-of-jinja2` — Jinja2 as LLM prompt templating, not HTML rendering

**Files:** Throughout `api/app/core/memory/agent/{services,utils}/` and `api/app/core/memory/{analytics,storage_services}/...`.
**Tool:** Semgrep (`python.flask.security.xss.audit.direct-use-of-jinja2`)
**Verdict:** **All 37 are false positives — a useful methodology case.**

The rule fires when Jinja2 is used without an explicit `autoescape=True`. The risk model is reflected XSS: an attacker-controlled value goes into a Jinja template that then renders as HTML in a browser. **Every hit in MemoryBear is Jinja2 building an LLM prompt string**, not HTML, e.g.:

```python
template = Template("""Given the following memory item:
{{ memory_item }}
Classify its type as: ...""")
```

These prompts go to a language model, never to a browser. HTML-escaping `<` to `&lt;` here would actively *break* the prompt — it would change what the LLM sees. The Flask XSS rule has no way to know the destination is an LLM and not a `Response`, so it fires identically. The right curated answer is "by-design, this is prompt templating," with the same rule scoped to Flask-view contexts.

This is the same rule-misfit shape as the [HolmesGPT](holmesgpt-holmesgpt.html) deliberately-vulnerable K8s test fixtures: a static rule with no awareness of the data-flow destination produces a large pile of confidently-wrong findings on a structurally-AI-shaped codebase. Worth a top-level note for any team running off-the-shelf SAST against LLM-template-heavy code.

### 4-N. Sandbox / by-design / standard tail

| Finding | Files | Verdict |
|---|---|---|
| 7× `insecure-file-permissions` (`0o755`) | `sandbox/app/core/runners/{nodejs,python}/...` | **By-design** — the runner ships executable lib files into a sandbox dir and `chmod 0o755`s them so the runner process can execute them |
| 5× JavaScript `non-literal-regexp` | (frontend / UI code) | Regex constructed from a non-literal; rarely a real DoS in practice |
| 3× `insecure-hash-algorithms` / 3× `insecure-uuid-version` | `api/app/core/rag/...`, `api/app/repositories/neo4j/add_edges.py:30`, etc. | **Non-crypto uses** — `md5`/`sha1`/`uuid1` for dedup keys, doc fingerprints, graph-edge identifiers (cache-key territory, not auth) |
| 3× `non-literal-import` | Plugin / extension discovery | **By-design** |
| 2× Dockerfile `last-user-is-root` | Container runs as root | Standard container-hardening best-practice |

## Patterns observed

**Jinja2-for-prompts is the cleanest new rule-misfit class in the series.** Across 19 prior scans, the rule-misfit pile was dominated by `logger-credential-leak` (6/6+ FPs — now [downgraded](evalstate-fast-agent.html#notes-on-the-tool)) and `python37/36-compatibility-*` (compat lint flagged as security). MemoryBear adds a third: Flask XSS rules firing on LLM-prompt templating. With LLM-prompt-Jinja becoming standard across the agent / RAG / memory-framework space, this rule is going to fire a lot more often than the Flask scope it was written for. A future scanner-level downgrade or scope-filter (only fire when the file imports Flask or uses `Response()`) would zero it out cleanly without losing the real Flask-view signal.

**A stale lockfile with no Dependabot is the single biggest concrete actionable item we've seen on a non-strict-norm responsive-team repo since the [Klavis monorepo drift](klavis-ai-klavis.html).** MemoryBear's team is clearly active (6 distinct authors merged PRs on the day of the scan; 0 open issues). The dependency-CVE accumulation isn't from neglect, it's just from not having a bot pestering them about it. A single PR adding `.github/dependabot.yml` plus one `uv lock --upgrade` pass clears the entire critical tier.

**Two of the three criticals echo previous scans.** `fastmcp` CVE-2026-32871 (SSRF) is the same advisory we flagged on [Klavis](klavis-ai-klavis.html); `nltk` Zip Slip is the same CVE class as [pixeltable](pixeltable-pixeltable.html)'s tarfile-extractall but in `nltk`'s own zip handling. The cross-scan pattern — recurring critical CVEs from a small set of widely-used Python packages — is the strongest argument we have for shipping a `pip-audit` / Trivy / Renovate setup as a default in any Python-stack AI project.

## Notes on the tool

- **The 37 Jinja2-for-prompts FPs validate the curation-as-product thesis.** A raw "196 findings, 5 critical" output makes the project look on fire. The curated reality is "60+ stale dep advisories that one `uv lock --upgrade` clears, plus three classes of rule misfit." Same data, very different ask of the maintainer.
- The `--ignore-samples` flag (now default-off, opted in here) and the `logger-credential-leak` low-confidence downgrade both contributed: no `examples/` finding pile, no logger-leak FPs in the 196.

## Disclosure timeline

- **2026-06-01** — Scan run at commit `9e4a35a7e831`; findings curated. No Dependabot detected → dependency tail filed as primary item, not delegated.
- **2026-06-01** — Public courtesy issue [#1296](https://github.com/SuanmoSuanyangTechnology/MemoryBear/issues/1296) filed on SuanmoSuanyangTechnology/MemoryBear focused on the dep tail (three criticals named) and a one-line "consider wiring Dependabot" note. The SQL-text and Jinja2-for-prompts items live in this write-up.
- **2026-06-12 (~11 days later)** — 📝 Maintainer (`@keeees`) closed the issue as completed with an acknowledgment: *"Thanks for the detailed report. We will review the advisories against the dependencies currently pinned in `api/uv.lock`. The Dependabot suggestion also makes sense. We plan to add a basic configuration so dependency security issues do not accumulate over time."* **No fix had landed at the time of close** — verified against `main`: `fastmcp` still `3.1.0`, `nltk` still `3.9.2`, `torch` still `2.2.2` (the flagged vulnerable versions), and no `.github/dependabot.yml` present. Recorded as an *acknowledgment with stated intent*, not a verified resolution — the honest-record convention cuts both ways, so this is not counted among the series' confirmed fixes.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/SuanmoSuanyangTechnology/MemoryBear" \
  --reports-dir reports/suanmosuanyangtechnology-memorybear \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
