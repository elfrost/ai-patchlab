---
layout: default
title: "Upsonic/Upsonic: security scan"
date: 2026-05-15
---

# Upsonic/Upsonic — security scan

**Repository:** [Upsonic/Upsonic](https://github.com/Upsonic/Upsonic) — 7.8k★, MIT, an autonomous-AI-agent framework written in Python.
**Commit scanned:** `1c61f94c5720` (HEAD of `master` at scan time)
**Scan date:** 2026-05-15
**Disclosure status:** Public courtesy issue filed on the Upsonic repo with the four publishable items. No findings required private coordination.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 21 |
| Medium | 19 |
| Low | 0 |
| Info | 0 (filtered) |

**40 total findings. After curation: 4 real items worth flagging, ~36 false positives or by-design patterns.**

The headline: **Upsonic's surface is much wider than the agentic_security or gptme codebases we scanned previously** — Upsonic ships a vector-DB integration, an OCR layer, a graph-checkpoint cache, a backpressure system, and agent shell-execution tools — so the scanner has more places to fire. After curation, the real signal is concentrated in four patterns: a `text()`-with-f-string usage in the PostgreSQL adapter, a global SSL-verification disable during EasyOCR model download, two `shell=True` agent tools (by design), and pickled persistence in the graph cache.

## Top findings (curated)

### 1. `agentic_security/ocr/layer_1/engines/easyocr.py:119` — global SSL verification disabled during model download

**Tool:** Semgrep (`unverified-ssl-context`, medium confidence)
**Verdict:** **Real concern, worth fixing.**

```python
import ssl
original_context = ssl._create_default_https_context
try:
    # Temporarily disable SSL verification for model download
    ssl._create_default_https_context = ssl._create_unverified_context
    # ... EasyOCR Reader init that downloads models ...
finally:
    ssl._create_default_https_context = original_context
```

Two interlocking problems:

- **Global side effect**: assigning `ssl._create_default_https_context` changes SSL behavior for the *entire Python process*, not just the EasyOCR client. Any other HTTPS call that runs concurrently — telemetry, LLM API, vector-DB sync — inherits the unverified context for the duration.
- **Exception safety**: if any exception inside the `try` block happens between the assignment and the `finally`, the original context restoration *will* run, but during the window between the two, any threaded HTTPS call uses the unverified context. In an async/threaded server, that's a real window.

The standard fix is to scope SSL disablement to the specific download, not the global module attribute. Easier still: pin EasyOCR's models locally (the `model_storage_directory` kwarg already exists in this code path) and pre-download them in a controlled way during deployment, rather than letting EasyOCR fetch on first use.

### 2. 8× `text(f"...")` interpolation in `src/upsonic/vectordb/providers/pgvector.py`

**Tool:** Semgrep (`avoid-sqlalchemy-text`, medium confidence)
**Verdict:** **Mixed — one site is a real best-practice concern, the rest are gated by Pydantic type validation.**

Examples:

```python
# Line 444 — static SQL, fine
session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

# Line 1242 — schema name interpolation
text(f'CREATE SCHEMA IF NOT EXISTS "{self.schema_name}";')

# Line 1247 (and similar at 1364, 1378, 1417, 1442, 1494) — numeric tuning
text(f"SET LOCAL ivfflat.probes = {nprobe}")
```

- The static-string call on line 444 is a false positive (no interpolation).
- The seven `SET LOCAL ...` calls interpolate Pydantic-validated integers (`nprobe`, `ef_search`, etc.); SQL injection is gated by the fact that the values are typed-and-bounded by `IVFIndexConfig` / `HNSWIndexConfig`. Low realistic risk, but the *shape* is still `text(f"... {value}")` which makes the code one Pydantic-relaxation away from a real issue.
- The `CREATE SCHEMA` call on line 1242 interpolates `self.schema_name` — a string. Schema names are validated against PostgreSQL identifier rules at the database level, but the application doesn't enforce a stricter allowlist before interpolation.

The defensible fix across all of these is to use SQLAlchemy's `bindparams()` or `quoted_name()` rather than f-strings, even for "obviously safe" config values. The benefit isn't avoiding today's exploit — it's keeping the static-analysis surface clean and future-proofing against schema-name sources that could change.

### 3. `subprocess.run(command, shell=True)` in `ralph/backpressure/gate.py:268` and `ralph/tools/filesystem.py:434`

**Tool:** Semgrep (`subprocess-shell-true`, medium confidence)
**Verdict:** **By design — the agent's shell-execution tools.**

```python
result = subprocess.run(
    command,
    shell=True,
    cwd=self.workspace,
    capture_output=True,
    text=True,
    timeout=timeout,
)
```

Both sites are part of Upsonic's agent tool layer — `filesystem.py` is literally the shell-tool the agent uses to run commands, and `gate.py` runs validation/test commands. The trust boundary here is "the user controls the agent; the agent runs shell as the user." That's the same pattern as gptme's `context_cmd.py` (which we [scanned previously](gptme-gptme.html)).

Suggestion: a one-line code comment above each `subprocess.run` documenting the intentional `shell=True` — "shell=True is intentional: this is the agent's shell-execution tool, invoked with a command the agent built". The same reasoning applies as on gptme: it doesn't change behavior, but it stops static analysis from re-flagging this on every scan, and it tells future contributors that the trust model has already been considered.

### 4. 5× `pickle.loads` / `pickle.dumps` for persisted cache and checkpoint state

**Files:** `src/upsonic/graphv2/cache.py:50, 255, 268`, `src/upsonic/graphv2/checkpoint.py:262, 345`
**Tool:** Semgrep (`pickle.avoid-pickle`, medium confidence)
**Verdict:** **Real best-practice concern; risk depends on filesystem trust.**

The graph cache and checkpoint subsystems pickle state objects to a local SQLite database. As written, the security posture is "if an attacker can write to the SQLite file, they can achieve arbitrary code execution at the next `pickle.loads`." For most deployments this is acceptable (local filesystem trust boundary), but two things make it worth flagging:

- One of the five flagged sites (`cache.py:50`) is actually `pickle.dumps` used purely to compute a *content hash* (then SHA-256'd). The `dumps` direction doesn't execute code on the side that calls it — only `loads` does. So that finding is a false positive; the rule fires on any `pickle` reference.
- The other four sites do `pickle.loads(blob)` where `blob` comes from the local DB. The realistic threat model is multi-tenant or shared-host: if more than one user can write to that SQLite file, the first to put a malicious blob in gets code execution on the next load by any other user.

Standard hardening options, in order of effort:

1. **Replace pickle with `cloudpickle` and add an HMAC signature** over the blob, verifying on load. Detects tampering of the local DB.
2. **Migrate the schema to JSON** for everything that doesn't *need* pickled Python objects. Most checkpoint state is dict-shaped.
3. **Document the threat model**: a comment that says "pickle is used for local cache; do not deploy this code path in multi-tenant configurations without HMAC or migration."

### 5-N. False positives and by-design patterns

| Finding | Files | Verdict |
|---|---|---|
| `non-literal-import` ×13 | All across `src/upsonic/*/__init__.py` and plugin discovery paths | **By design** — plugin/discovery imports are dynamic by definition |
| `Potential secret detected: generic-api-key` ×4 | `tests/unit_tests/safety_engine/test_skill_policies.py`, `test_storage_agentsession_comprehensive.py`, `test_langfuse_integration.py` | **By design — test data for Upsonic's *own* safety/policy engine.** These are crafted-to-trigger fixtures, exactly the same shape we saw on agentic_security's PII detector tests |
| `Potential secret detected: private-key` ×2 | `safety_engine/test_*.py` | Same as above |
| `Potential secret detected: github-pat` / `gitlab-pat` ×2 | Same | Same |
| `insecure-websocket` ×1 | `src/upsonic/interfaces/manager.py:312` | Needs context, but likely local development WS endpoint |
| `insecure-hash-algorithms-sha1` ×1 | `messages.py:166` | **FP** — SHA-1 used as a non-crypto stable identifier (truncated to 6 hex chars), not for integrity |
| `python37-compatibility-importlib2` ×1 | Compatibility hint, not security |

## Patterns observed

**Upsonic shows the cost-and-benefit of a wide-surface agent framework.** Where gptme's findings clustered in one place (CI/CD inputs) and agentic_security's clustered in another (the global CORS + an icons proxy), Upsonic spreads findings across the subsystems it owns: a vector-DB adapter, an OCR layer, agent shell tools, graph state persistence. None of the four real findings is critical on its own, but the pattern — "every subsystem ships its own minor papercut" — is what to expect from a framework of this scope. The maintainers have built a lot, and the security review has to scale with the surface.

**The four real items have related, mundane fixes:** scope the SSL disablement (don't touch the global), use `bindparams()` instead of f-strings for SQL identifiers and tuning values, comment the agent's `shell=True` (or migrate to argv list when a use-case allows), and either sign-or-migrate the pickled state. None of these are exotic; all are documented patterns. The kind of review a careful engineer does on their second pass through the codebase.

**The safety-engine test fixtures are a microcosm of the FP problem.** Upsonic ships a *safety policy engine* — code whose job is to detect crafted secrets, suspicious patterns, prompt-injection attempts. To test it, they hard-code crafted secrets, suspicious patterns, prompt-injection attempts. Any static-analysis pass that doesn't understand "this file is *testing* a detector for those patterns" will fire a ton. Six of our 21 high-severity findings on this scan are in this category. This is now the third scan (after agentic_security's PII tests and openllmetry's VCR cassettes) where the same pattern dominates the FP count — the case for a `.aipatchlabignore` or path-aware confidence weighting in our own tool is getting hard to ignore.

## Notes on the tool

Recurring backlog items from prior scans:

- **Path-based suppression / `.aipatchlabignore`** — `tests/unit_tests/safety_engine/**`, `tests/**/cassettes/**`, vendored library paths should be excludable.
- **Deduplication across files** — 8 separate `avoid-sqlalchemy-text` findings on the same module would read better as one grouped entry. 13 `non-literal-import` findings likewise.
- **The `Repository:` header in `security_report.md` still shows the temp clone path** even though finding-level `file` fields are rebased.

New from this scan:

- **Semgrep's `pickle.avoid-pickle` rule fires on `pickle.dumps` calls used only for hashing.** Our `enrich_findings` layer could downgrade these to `low` confidence when no `pickle.loads` is reachable in the surrounding code — or better, when the `dumps` result is passed directly into `hashlib`.
- **The `text(f"...")` rule fires regardless of whether the interpolated value comes from a Pydantic-validated config.** A future enhancement: type-aware suppression for known-validated numeric configs.

## Disclosure timeline

- **2026-05-15** — Scan run, top findings curated.
- **2026-05-15** — Public courtesy issue filed on Upsonic/Upsonic with the four publishable items (SSL disable, SQLAlchemy text f-string, agent shell=True comment, pickle persistence). No finding rose to the level requiring private coordination.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/Upsonic/Upsonic" \
  --reports-dir reports/upsonic-upsonic \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
