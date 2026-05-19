---
layout: default
title: "MervinPraison/PraisonAI: security scan"
date: 2026-05-16
---

# MervinPraison/PraisonAI — security scan

**Repository:** [MervinPraison/PraisonAI](https://github.com/MervinPraison/PraisonAI) — 7.7k★, MIT, "AI Workforce" multi-agent orchestration framework spanning Python, TypeScript, and a CLI.
**Commit scanned:** `68035af76d81` (HEAD of `main` at scan time)
**Scan date:** 2026-05-16
**Disclosure status:** ✅ **Resolved.** All five items in the courtesy issue were addressed by [PraisonAI PR #1677](https://github.com/MervinPraison/PraisonAI/pull/1677), authored by their `praisonai-triage-agent` bot (itself built with the PraisonAI framework) within ~50 minutes, then reviewed and merged by [@MervinPraison](https://github.com/MervinPraison) on 2026-05-19. Issue [#1676](https://github.com/MervinPraison/PraisonAI/issues/1676) auto-closed by the merge. The bot also found an additional ClickHouse identifier-safety site and shipped a new test module covering both vector stores.

## Summary

| Severity | Count (raw) | Count (after ignore-file) |
| --- | ---: | ---: |
| Critical | 0 | 0 |
| High | 226 | 187 |
| Medium | 263 | 214 |
| Low | 0 | 0 |
| Info | 0 (filtered) | 0 (filtered) |

**489 raw findings → 401 after suppressing `examples/**` and `**/tests/**`. After curation: 5 real best-practice items, ~390 false positives or by-design patterns.**

This is by far the largest scan in our series — PraisonAI spans multiple sub-packages (`praisonai-agents`, `praisonai`, `praisonai-ts`), three languages (Python + TypeScript + shell), and ships first-class integrations for ~6 different persistence backends. The scanner has more shapes to fire on. After applying [the project's new `--ignore-file` feature](https://github.com/elfrost/ai-patchlab/pull/14) to suppress the example-code and test directories, the bulk of remaining findings collapse into two large families — both of which we'd already characterized on prior scans.

## Top findings (curated)

### 1. `src/praisonai/praisonai/persistence/knowledge/surrealdb_vector.py:31` — default credentials `root/root`

**Tool:** Semgrep (`hardcoded-password-default-argument`, medium confidence)
**Verdict:** **Real best-practice concern.**

```python
def __init__(
    self,
    url: str = "ws://localhost:8000/rpc",
    namespace: str = "praisonai",
    database: str = "vectors",
    username: str = "root",
    password: str = "root",
    embedding_dim: int = 1536,
):
```

`username="root"`/`password="root"` are SurrealDB's out-of-the-box defaults — they exist precisely so the install-step `quickstart` works without configuration. The risk is that a developer copies the snippet from PraisonAI docs into a deployment context, never changes the credentials, and ships a SurrealDB instance reachable from anything with default-root.

Recommended pattern: omit the password default and `raise` if the caller doesn't pass one, with a docstring pointing at SurrealDB's [secure-defaults guide](https://surrealdb.com/docs/surrealdb/security/authentication):

```python
def __init__(
    self,
    url: str = "ws://localhost:8000/rpc",
    namespace: str = "praisonai",
    database: str = "vectors",
    username: str | None = None,
    password: str | None = None,
    embedding_dim: int = 1536,
):
    if username is None or password is None:
        raise ValueError(
            "SurrealDB username/password must be provided explicitly. "
            "Default 'root/root' is unsafe outside of local dev — see docs."
        )
```

### 2. `src/praisonai/praisonai/cli/commands/port.py:79` and `:169` — `subprocess.run(list, shell=True)`

**Tool:** Semgrep (`subprocess-shell-true`, medium confidence)
**Verdict:** **Real issue — and the `:79` site is also a behavioral bug.**

```python
# Line 79 — the netstat | findstr pipe
result = subprocess.run(
    ["netstat", "-ano", "|", "findstr", f":{port}"],
    capture_output=True,
    text=True,
    shell=True,
    timeout=5,
)
```

Two compounding problems:

1. **`subprocess.run(list, shell=True)` on Windows passes the entire list as a single concatenated command string** — but `|` inside that string is interpreted *by the called program* (`netstat`) as a literal argument, not by `cmd.exe` as a pipe. So the line at `:79` does not actually pipe netstat to findstr. The intended filter never runs.
2. The line at `:169` has the same `shell=True` flag but no pipe; it falls back to parsing all of netstat's output in Python (which works, just unnecessarily passes through cmd.exe).

The cleanest fix is to drop `shell=True` entirely and parse netstat's output in Python with a regex, as `:169` already does. The `:79` site can then become a Python-side filter on `:port` rather than a shell pipe:

```python
result = subprocess.run(
    ["netstat", "-ano"],  # no shell, no pipe
    capture_output=True,
    text=True,
    timeout=5,
)
for line in result.stdout.splitlines():
    if f":{port}" in line:
        # ...
```

### 3. `.github/workflows/{praisonai-issue-triage,praisonai-pr-review}.yml` — `${{ inputs.* }}` shell interpolation

**Tool:** Semgrep (`run-shell-injection`, medium confidence)
**Verdict:** **Real best-practice — same class as [the gptme/gptme scan](gptme-gptme.html), which has [already been fixed in PR #2399](https://github.com/gptme/gptme/pull/2399).**

```yaml
run: |
  if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
    export ISSUE_NUMBER="${{ inputs.issue_number }}"
  else
    export ISSUE_NUMBER="${{ github.event.issue.number }}"
  fi
  praisonai github triage --issue $ISSUE_NUMBER ...
```

GitHub Actions interpolates `${{ ... }}` at workflow-parse time, before any shell quoting can protect the result. The standard fix is to pass values through `env:` and reference them as `$ENV_VAR` from the shell. The gptme fix PR linked above is a concise template (the same contributor's per-file breakdown is reusable).

Realistic exploit window today: narrow — `inputs.issue_number` for `workflow_dispatch` requires a dispatcher with write access who intentionally crafts a malicious input — but the fix is mechanical and removes the class.

### 4. 3× `curl ... | bash` in install scripts

**Files:** `src/praisonai/scripts/install.sh:176`, `src/praisonai/scripts/docker/install-smoke/run.sh:25, 27`
**Tool:** Semgrep (`curl-pipe-bash`, medium confidence)
**Verdict:** **Real best-practice — the classic anti-pattern.**

`curl <url> | bash` (or `wget | sh`) pipes arbitrary network content into an interactive shell. If `<url>` is hijacked, MitM'd, or returns different content on different requests, the user runs malicious code. Even when the URL is trusted (e.g. a project's own install endpoint), the recommended pattern is to download the script first, let the user inspect, then execute:

```bash
curl -L https://example.com/install.sh -o /tmp/install.sh
# (optional: shasum -a 256 /tmp/install.sh and compare against a pinned hash)
bash /tmp/install.sh
```

For the docker-smoke scripts, this is internal CI infrastructure so risk is contained; for the user-facing `install.sh`, switching to the "download then run" pattern is worth the small UX cost.

### 5. ~220 SQL findings: same `text(f"...")` / `f-string into CREATE TABLE` class as on Upsonic

**Files:** `src/praisonai-agents/praisonaiagents/storage/backends.py`, `src/praisonai-agents/praisonaiagents/memory/search.py`, `src/praisonai/praisonai/persistence/conversation/async_postgres.py`, `async_mysql.py`, and 10+ others
**Tools:** Semgrep (`sqlalchemy-execute-raw-query`, `formatted-sql-query`, `asyncpg-sqli`)
**Verdict:** **Same shape as [the Upsonic scan](upsonic-upsonic.html) — `text(f"... {self.table_name} ...")` and `await conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ...")` patterns where the interpolated value is a *config-controlled identifier*.**

Looking at one representative site:

```python
# src/praisonai/praisonai/persistence/conversation/async_postgres.py:113
sessions_table = f"{self.table_prefix}sessions"
async with self._pool.acquire() as conn:
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {sessions_table} (
            session_id VARCHAR(255) PRIMARY KEY,
            ...
        )
    """)
```

`table_prefix` comes from config (Pydantic-shaped). PostgreSQL's identifier rules limit damage at the DB level. The realistic exploitability today is gated, **but** the pattern still appears in 220+ places across the codebase, including the `praisonai-agents/storage/backends.py` core. A future PR that allows `table_prefix` to come from a less-validated source (a CLI arg, a YAML config, a user-provided name) would turn this into a real SQL-injection footgun without any other code change.

The defensible fix across all sites is SQLAlchemy's `quoted_name()` / `Identifier()` quoting (or asyncpg's identifier-escaping equivalent) instead of f-strings. The benefit isn't avoiding today's exploit — it's future-proofing the pattern across a 220-site surface where any one slip in input-validation propagates everywhere.

### 6-N. False positives and cross-references

| Finding | Files | Verdict |
|---|---|---|
| `non-literal-import` ×34 | `praisonai-agents/_lazy.py`, all `__init__.py` files | **By design** — plugin/discovery imports |
| `dangerous-globals-use` ×36 | `praisonai-agents/agent/agent.py`, auth, etc. | Almost all are `globals().get(...)`-style plugin lookup patterns; needs case-by-case review but most are by-design |
| `detect-insecure-websocket` ×13 | All inside `praisonaiagents/mcp/mcp_websocket.py` and friends | **By design — this is literally the WebSocket transport implementation for MCP.** The module's docstring even cites "SEP-1288: WebSocket Transport for MCP (in review)." The scanner doesn't know that the rule's target *is* the module being scanned. |
| `eval-detected` / `exec-detected` ×7 | `praisonai-agents/tools/python_tools.py`, `praisonai/cli/features/job_workflow.py` | **By design** — these are the agent's Python-execution primitives, with explicit `compile()` + namespace control. Like Upsonic's agent shell tools, a one-line trust-boundary code comment would help. |
| `detected-pgp-private-key-block` ×1 | `src/praisonai/praisonai/cli/main.py:3629` | **False positive — meta-pattern.** The flagged line is *PraisonAI's own secret-detector regex*, listing the literal `-----BEGIN PGP PRIVATE KEY BLOCK-----` as a pattern its detector matches against |
| `Potential secret detected: generic-api-key` ×3 | `praisonai-agents/telemetry/telemetry.py:192` (`phc_skZpl3eFLQJ4iYjsERNMbCO6jfeSJi2vyZlPahKgxZ7`) | **By design — PostHog `phc_` public project key.** Same FP class as on [the openllmetry scan](traceloop-openllmetry.html); `phc_`-prefixed keys are public write-only event-ingestion identifiers |
| `python37-compatibility-importlib2` ×2 | Template discovery | **Not security** — Python 3.7 compat hints |

## Patterns observed

**The SQL footprint is the story.** Of 401 findings (post-ignore), 244 — about 60% — are the same `text(f"...")` / `f-string-into-CREATE-TABLE` class we documented on Upsonic. PraisonAI has more of them because it supports more persistence backends (SQLite, MySQL, PostgreSQL, async variants of each, and a shared abstract storage layer). The shape is consistent: a `table_name` or `table_prefix` from config, interpolated into DDL. None of them is exploitable as a remote attacker today; all of them rest on the same single load-bearing assumption (config-controlled table names). A defensible fix in one place generalizes.

**The WebSocket findings collapse the moment you read the file.** 13 of the 18 `insecure-websocket` findings are inside the module *named* `mcp_websocket.py` whose entire purpose is to implement the WebSocket transport for MCP. The Semgrep rule fires on any `ws://` URL string; here every match is in the protocol implementation, not a misuse. This is the kind of FP class that path-suppression alone can't fix (the file *should* be scanned for other rules) and that an `aipatchlab.yaml` with per-file rule overrides would clean up.

**The PGP private key FP is the third "scanner panics on a security-tool's own pattern definitions" case in this series.** First it was agentic_security's PII detector tests, then Upsonic's safety-engine fixtures, now PraisonAI's secret-redaction regex list. Static scanners that don't distinguish *implementations of a detector* from *uses of a credential* will keep firing on this whole subset of projects. It's worth a class-level note in our backlog.

**`--ignore-file` saved real time on this scan.** First pass: 489 raw findings, several minutes of categorization. Second pass (with examples/tests suppressed): 401 findings concentrated in real source, much faster to triage. Without the feature [shipped one PR ago](https://github.com/elfrost/ai-patchlab/pull/14), the curation cost on a target this size would have been prohibitive. This is the first scan to validate the path-suppression workflow on a fresh target — and it landed exactly where we hoped.

## Notes on the tool

Recurring backlog items:

- **Cross-rule deduplication is now urgent.** Three rules (`sqlalchemy-execute-raw-query`, `formatted-sql-query`, `asyncpg-sqli`) fire on overlapping sites — e.g. `async_postgres.py:113` is flagged by both `asyncpg-sqli` and `formatted-sql-query`. The current output reports 244 SQL findings; a deduplicated view would report ~120 unique site-rule pairs.
- **Per-file rule overrides** (in addition to path-based ignore) would let us suppress, for example, "all `insecure-websocket` findings in `mcp_websocket.py`" — fine-grained enough to keep the file in scope for other rules.

New from this scan:

- **Trial of the new `--ignore-file` flag on a fresh real target** confirmed the pattern works end-to-end. 88 findings (mostly the `examples/**` SQL pedagogy) correctly suppressed, the four real items preserved.

## Disclosure timeline

- **2026-05-16** — Scan run, ignore file applied to suppress `examples/**` + `**/tests/**`, top findings curated.
- **2026-05-16** — Public courtesy issue [#1676](https://github.com/MervinPraison/PraisonAI/issues/1676) filed with the five publishable items.
- **2026-05-16 (≈50 min later)** — PraisonAI's `praisonai-triage-agent` bot picked up the issue and opened [PR #1677](https://github.com/MervinPraison/PraisonAI/pull/1677) with fixes for all five items plus an additional ClickHouse vector-store finding and a new test module.
- **2026-05-19** — PR #1677 reviewed and merged by [@MervinPraison](https://github.com/MervinPraison). Issue #1676 auto-closed.

## Resolution

The merged fix touches eight files:

- **`src/praisonai/praisonai/persistence/knowledge/surrealdb_vector.py`** (+44/-5) — `username` and `password` defaults removed; the constructor now raises `ValueError` if either isn't provided, with a docstring pointing at the rationale. Marked as a documented breaking change.
- **`src/praisonai/praisonai/persistence/knowledge/clickhouse.py`** (+8/-3) — *not in the original issue.* The bot's deeper analysis surfaced a parallel identifier-interpolation site in the ClickHouse vector store and applied the same `validate_identifier` defense used elsewhere in the codebase.
- **`src/praisonai/tests/unit/persistence/test_knowledge_identifier_safety.py`** (+21) — *new test module* covering both vector-store identifier-safety paths.
- **`src/praisonai/praisonai/cli/commands/port.py`** (+37/-34) — `shell=True` removed from both netstat invocations; the broken `|` pipe at `:79` replaced with a Python-side filter on netstat's output; the Windows-port-detection code-path rewritten as part of the same refactor.
- **`.github/workflows/praisonai-issue-triage.yml`** and **`praisonai-pr-review.yml`** — `${{ inputs.issue_number }}` and `${{ github.event.issue.number }}` moved to `env:` blocks instead of inline `run:` interpolation.
- **`src/praisonai/scripts/install.sh`** (+10/-1) and **`src/praisonai/scripts/docker/install-smoke/run.sh`** (+13/-3) — `curl | bash` replaced with download-then-run, with the install script gaining basic validation steps before execution.

Two notable details:

- **The PR author is a bot built with PraisonAI itself** (`praisonai-triage-agent`, running their multi-agent framework). The fix loop ran the same framework being audited, fed by the AI PatchLab scan output, with a human reviewer (MervinPraison) approving the change before merge. The recursion is intentional dogfooding — they ship the triage agent as part of the project.
- **The bot's deeper analysis surfaced a finding the scan missed.** The original courtesy issue called out the SurrealDB identifier-interpolation site explicitly; the bot generalized the same pattern to ClickHouse without being prompted to. That's a meaningful gain over a purely-mechanical fix.

Three days from issue filed to PR merged, all five flagged patterns addressed plus one bonus generalization, with new test coverage and full attribution. Combined with the [gptme #2399 outcome](gptme-gptme.html) (12h, human contributor, all three items), this is the second confirmation of the scan-and-disclose workflow producing real maintainer action.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/MervinPraison/PraisonAI" \
  --reports-dir reports/mervinpraison-praisonai \
  --min-severity medium \
  --ignore-file reports/mervinpraison-praisonai/.aipatchlabignore
```

A sample `.aipatchlabignore` for this target (`examples/**`, `**/tests/**`, `**/test_*.py`, vendored `static/`) is in the report's directory; absent it, the raw scan reports 489 findings, mostly in pedagogic example code.

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
