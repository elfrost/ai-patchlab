---
layout: default
title: "VRSEN/agency-swarm: security scan"
date: 2026-06-02
---

# VRSEN/agency-swarm — security scan

**Repository:** [VRSEN/agency-swarm](https://github.com/VRSEN/agency-swarm) — 4.4k★, MIT, a multi-agent orchestration framework that wires together specialist agents over OpenAI/MCP backends, including a FastAPI integration server and built-in tools.
**Commit scanned:** `f4317cde9248` (HEAD of `main` at scan time)
**Scan date:** 2026-06-02
**Disclosure status:** Public courtesy issue filed on the agency-swarm repo. Scope kept tight: one focused note on the auth-heavy dependency advisory cluster (`authlib` + `fastmcp` + `mcp` — exactly the libraries this project depends on for OAuth and MCP server integration).

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 21 |
| Medium | 25 |
| Low | 0 |
| Info | 0 (filtered) |

**48 total findings. After curation: the headline is the auth-class CVE concentration in the pinned `uv.lock` — `authlib` carries 1 critical + 3 high all in the authentication-bypass / signature-verification class, `fastmcp` carries 1 critical SSRF + multiple high OAuth-related advisories, and `mcp` is pinned past a known DNS-rebinding-default CVE. For a multi-agent orchestration framework whose value-add is exactly OAuth/MCP integration, this is the dependency-tree-fits-the-product-shape concern that benefits most from a single coordinated refresh.**

## Top findings (curated)

### 1. `uv.lock` — auth-tier dependency advisories in the exact libraries the project depends on for auth

**Tool:** Trivy
**Verdict:** **Real, named, and unusually well-correlated with the project's surface.**

The two scanner-reported criticals plus the high-severity auth tail in `authlib` and `fastmcp` form a cluster that's worth treating as one item rather than two:

| CVE | Package | Class | Why it lands here |
|---|---|---|---|
| [CVE-2026-27962](https://github.com/advisories?query=CVE-2026-27962) | `authlib` | **Authentication bypass via JWK Header Injection** (critical) | An attacker can craft a JWT whose JWK header steers signature verification to an attacker-controlled key — i.e. trusted-token forgery. |
| [CVE-2026-32871](https://github.com/advisories?query=CVE-2026-32871) | `fastmcp` | **Authenticated Server-Side Request Forgery** (critical) | A trusted MCP client pivots the FastMCP server into making requests to arbitrary internal URLs. Same advisory previously seen on [Klavis](klavis-ai-klavis.html) and [MemoryBear](suanmosuanyangtechnology-memorybear.html). |
| [CVE-2026-28490](https://github.com/advisories?query=CVE-2026-28490) | `authlib` | Information disclosure via cryptographic padding | High |
| [CVE-2026-28498](https://github.com/advisories?query=CVE-2026-28498) | `authlib` | Authentication bypass via forged OpenID Connect tokens | High |
| [CVE-2026-28802](https://github.com/advisories?query=CVE-2026-28802) | `authlib` | Signature verification bypass via malicious JWT | High |
| [CVE-2026-27124](https://github.com/advisories?query=CVE-2026-27124) | `fastmcp` | OAuth-related advisory | High |
| [CVE-2025-69196](https://github.com/advisories?query=CVE-2025-69196) | `fastmcp` | Improper token issuance / incorrect resource | High |
| [CVE-2025-66416](https://github.com/advisories?query=CVE-2025-66416) | `mcp` | DNS rebinding protection disabled by default | High |

That's 4 distinct **authentication-bypass-class** advisories in a single dependency (`authlib`) plus 3 OAuth/MCP advisories across `fastmcp` and `mcp`. The realistic exploitability depends on whether the project's surface actually exercises the affected `authlib` API (token verification on inbound requests in the FastAPI integration is the most likely path), but the dependency-tree exposure is unambiguous: every consumer of agency-swarm pulls these versions.

The rest of the tail is the standard pile — `urllib3` ×4 highs, `tornado` ×2, `aiohttp` ×1 high + ×7 medium, `python-multipart` ×1 high (path-traversal class), `starlette` `CVE-2025-62727`, `pyjwt` `CVE-2026-32597`, `cryptography` `CVE-2026-26007`. A single `uv lock --upgrade` pass clears the vast majority.

**Dependabot is not configured** on the repo (no `.github/dependabot.yml`, no Dependabot PRs in the history), so this tail has been accumulating uncollected — same pattern as [MemoryBear](suanmosuanyangtechnology-memorybear.html) yesterday.

### 2. `src/agency_swarm/tools/built_in/PersistentShellTool.py:61` — `subprocess.run(self.command, shell=True)` in a shell-by-design tool

**Tool:** Semgrep (`subprocess-shell-true`)
**Verdict:** **By-design — the tool's whole purpose is to give the agent a shell.**

The same call-site shape as [fast-agent](evalstate-fast-agent.html)'s `interactive_shell.py`: the LLM controls `self.command` because the agent is *supposed to* run shell commands. Opting into a `PersistentShellTool` is opting into LLM-driven shell execution on the host. The Windows branch uses `["powershell", "-Command", self.command]` (no `shell=True` but the LLM still controls the command string fully), so the Unix branch's `shell=True` doesn't change the threat surface — both are intentional.

The right operator-level mitigation is the same as for fast-agent: don't enable the persistent-shell tool on an agent whose prompt or input you don't trust.

### 3. `src/agency_swarm/integrations/fastapi.py:132` — wildcard CORS, **but already mitigated**

**Tool:** Semgrep (`wildcard-cors`)
**Verdict:** **FP at the exploitability level — the surrounding code handles the unsafe case correctly.**

The CORS configuration block already does the conventional safe handling:

```python
should_allow_credentials = True
if "*" in cors_origins:
    if app_token:
        logger.warning(
            "CORS wildcard '*' with credentials enabled is insecure and often "
            "blocked by browsers. Disabling credentials for wildcard origins."
        )
    should_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=should_allow_credentials,
    ...
)
```

The rule fires on `allow_origins=cors_origins` because `cors_origins` *could* contain `*`, but the surrounding code explicitly downgrades `allow_credentials` to `False` when it does. That's exactly the spec-compliant safe pattern.

### 4. `src/agency_swarm/tools/utils.py:465` — `exec(result, exec_globals)` for schema→Pydantic compilation

**Tool:** Semgrep (`exec-detected`)
**Verdict:** **Real-but-design-context-dependent.**

The pattern is schema-to-model compilation: take a generated Python source string for a Pydantic-like class, `exec` it into a controlled `exec_globals` namespace, then extract the class with `exec_globals.get(class_name)`. The `exec_globals` is restricted to a small whitelist (`datetime`, `date`, `Set`, `Tuple`, `Any`, `Callable`, `Decimal`, `Literal`, `Enum`). The risk hinges entirely on where `result` comes from: if it's developer-authored schemas at install time, the surface is low; if it's LLM-generated code at runtime, the surface is "LLM-driven RCE within the exec sandbox limits."

Worth a maintainer's eyes on the call-site flow into this function — flagged in the issue as out-of-scope-for-now but mentioned.

### 5-N. Standard noise / by-design

| Finding | Files | Verdict |
|---|---|---|
| 1× `logger-credential-leak` | `src/agency_swarm/integrations/openclaw.py:517` | **Low confidence** (per the [series downgrade](evalstate-fast-agent.html#notes-on-the-tool)) — historically 6/6+ FPs |
| 1× `non-literal-import` | `src/agency_swarm/utils/files.py:49` | **By-design** — plugin / file-loader discovery |

## Patterns observed

**Dependency advisory composition can be as informative as the count.** Most scans surface dep tails that are essentially random (whatever pinned versions happen to be stale). agency-swarm's tail is the opposite: the heavy hitters concentrate in exactly the libraries this project *depends on for the value it provides* — `authlib`, `fastmcp`, `mcp`. That's the difference between "a stale lockfile" and "stale where it counts." The curated issue leads with the auth-class concentration for exactly that reason.

**Two `uv lock` scans in a row, two repos with no Dependabot, two coherent "this is what `uv lock --upgrade` would clear" issues.** MemoryBear ([yesterday](suanmosuanyangtechnology-memorybear.html)) and agency-swarm (today) are both responsive non-strict-norm mid-popularity Python projects whose owners just haven't wired Dependabot yet. After ten scans of "dep-CVE tail" mentions across the series, the takeaway is concrete: shipping a default `.github/dependabot.yml` template in any AI-stack project starter would remove this entire class of finding from the next year of scans.

**`shell=True` in an agent-framework "shell tool" is now a recurring by-design pattern.** [fast-agent](evalstate-fast-agent.html)'s `interactive_shell.py` is the same shape. The class is large enough to deserve its own curation note across the series: when an agent framework ships a "Shell" / "Bash" / "PersistentShell" tool, the `shell=True` finding inside it is the *feature*, not a vulnerability. Treating it otherwise would either kill the feature or push maintainers toward more complex but no-more-secure workarounds.

## Notes on the tool

- This scan re-validates the **`logger-credential-leak` low-confidence downgrade** shipped on 2026-05-28: one hit, correctly deprioritized, and (on inspection of the call site) consistent with the 6/6+ FP pattern across the series.
- The **dep-only scans pattern** (where the actionable surface is `uv.lock`, not source) is now the modal shape for non-strict-norm responsive-team scans — three of the last four (MemoryBear, agency-swarm, plus the earlier guardrails / Klavis flavor). A tool-side feature that previewed *what `uv lock --upgrade` would do* would directly answer the curator's question in one step.

## Disclosure timeline

- **2026-06-02** — Scan run at commit `f4317cde9248`; findings curated. No Dependabot detected → dep advisory cluster filed as the primary item with `authlib` auth-bypass class as the headline.
- **2026-06-02** — Public courtesy issue [#658](https://github.com/VRSEN/agency-swarm/issues/658) filed on VRSEN/agency-swarm focused on the auth-tier `uv.lock` cluster (`authlib` 4-pack, `fastmcp` SSRF + OAuth pile, `mcp` DNS rebinding) and a one-line "consider wiring Dependabot" note.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/VRSEN/agency-swarm" \
  --reports-dir reports/vrsen-agency-swarm \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
