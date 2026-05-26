---
layout: default
title: "pydantic/logfire: security scan"
date: 2026-05-26
---

# pydantic/logfire — security scan

**Repository:** [pydantic/logfire](https://github.com/pydantic/logfire) — 4.3k★, MIT, an AI observability platform for production LLM and agent systems. Backed by the Pydantic team.
**Commit scanned:** `bd08c7e0b9d7` (HEAD of `main` at scan time)
**Scan date:** 2026-05-26
**Disclosure status:** **No issue filed — there was nothing to action.** Every finding is either documentation/test scaffolding or a deliberate language feature use that logfire structurally needs to do its job. This is the third clean scan in the series.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 16 |
| Medium | 11 |
| Low | 0 |
| Info | 0 (filtered) |

**27 total findings. After curation: 0 real items.** The post is short because the codebase is, but the angle here is the most interesting in the three clean-scan series so far: **every Semgrep-flagged pattern in `logfire/_internal/` is a deliberate language feature use that logfire fundamentally requires to function as an observability tool.**

This is the third clean scan, after [Giskard-AI/giskard-oss](giskard-ai-giskard-oss.html) (where 27 FPs were explained by Giskard's own use of `detect-secrets` and `zizmor`) and [MinishLab/semble](minishlab-semble.html) (where the cleanness was structural — tiny focused library, two responsive maintainers). logfire's clean-scan mechanism is different from both.

## What an observability tool looks like to a security scanner

The findings in `logfire/_internal/` are textbook examples of patterns that *look* dangerous to a generic static analyzer but are the entire reason the library exists:

### 1. `logfire/_internal/formatter.py:141,145` — `eval()` ×2

```python
value = eval(value_code, global_vars, local_vars)
# ...
formatted = eval(formatted_code, global_vars, {**local_vars, '@fvalue': value})
```

**Verdict:** **By design — this is logfire's f-string parser.**

When you write `logfire.info(f"user {user.email} accessed {resource.id}")`, logfire parses the f-string's AST in the caller's frame, then re-evaluates each interpolated expression to capture it as a structured log attribute (`extra_attrs[source] = value`). The `value_code` argument comes from the user's own f-string, evaluated in their own scope — this is the same code the Python interpreter would have run anyway, just inspected for telemetry. The scanner sees `eval()` and panics; the feature is *the entire reason logfire is more useful than `print()` for structured logging*.

### 2. `logfire/_internal/auto_trace/rewrite_ast.py:48` — `exec()`

```python
code = compile(tree, filename, 'exec', dont_inherit=True)

def execute(globs: dict[str, Any]):
    globs[logfire_name] = context_factories
    exec(code, globs, globs)
```

**Verdict:** **By design — this is logfire's auto-trace feature.**

`auto_trace` compiles the user's AST with logfire instrumentation calls woven in, then `exec()`s it. The `tree` is the user's own module AST, with logfire's spans inserted at function boundaries. Without the `exec()`, the auto-tracing feature does not exist. The scanner sees `exec()` and panics; the feature is documented at [logfire.pydantic.dev](https://logfire.pydantic.dev/) under "Automatic tracing".

### 3. `logfire/_internal/integrations/executors.py:78` — `pickle.dumps()`

```python
config_dict = asdict(GLOBAL_CONFIG)
# Verify that the config can be pickled before ProcessPoolExecutor tries to pickle it.
pickle.dumps(config_dict)
return config_dict
```

**Verdict:** **False positive — `pickle.dumps`, not `loads`. And the result is thrown away.**

This is `pickle.dumps()` used as a *pickleability check* — the result is immediately discarded, the function only cares whether the `dumps()` call raised. `pickle.dumps` does not execute code (only `pickle.loads` does, on attacker-controlled input). This is the same shape as Upsonic's `cache.py:50` we documented previously: the rule fires on any `pickle` reference regardless of direction.

### 4. `logfire/_internal/integrations/psycopg.py:80,122` — `non-literal-import` ×2

**Verdict:** **By design — psycopg integration version detection.**

The integration imports either `psycopg` or `psycopg2` dynamically at runtime based on what's installed. Plugin-discovery pattern, the same FP class flagged on every prior scan in the series.

### 5. `logfire/variables/__init__.py:121` — `dangerous-globals-use`

```python
def __getattr__(name: str):
    from logfire.variables.variable import (
        ResolveFunction, Variable, targeting_context,
    )
    return locals()[name]
```

**Verdict:** **By design — lazy import idiom.** A `__getattr__` that defers an import until the attribute is actually requested, returning the imported name via `locals()`. The pattern is in PEP 562 and used widely in libraries that want to avoid import-time cost. Standard, not dangerous.

## And the false positives outside `logfire/_internal/`

| Finding | File | Verdict |
|---|---|---|
| 15× "secret detected" | `docs/javascripts/algolia-search.js:2` (Algolia public search key — public by design, same FP class as PostHog `phc_` keys), `docs/reference/advanced/use-api-keys.md:100,107` (documentation showing example API-key headers), `tests/cassettes/test_query_client/*.yaml` (VCR cassette test fixtures) | **FP** — public-by-design key + doc placeholders + test fixtures |
| `app-run-security-config` ×1 | `examples/python/flask-sqlalchemy/main.py:18` | **FP** — example code, `app.run()` is fine in an example |
| `path-join-resolve-traversal` ×2 | `pyodide_test/test.mjs:52` | **FP** — test scaffolding |

## Patterns observed

**The three clean scans in the series each demonstrate a different shape of "clean."** [Giskard's clean scan](giskard-ai-giskard-oss.html) was explained by Giskard's own use of `detect-secrets` and `zizmor` — the company runs scanners on themselves and triages the output. [semble's clean scan](minishlab-semble.html) was structural — a 1.9 MB focused library has so little surface that there's nothing for the rules to fire on. logfire's clean scan is yet another mechanism: **a 76 MB Python library whose `_internal/` package is built entirely around language features (`eval`, `exec`, AST manipulation, dynamic imports, pickle for IPC) that are dangerous in user code but are the literal reason a tracing library exists.** Three projects, three reasons "scan produced nothing actionable" — useful reference points for understanding what a scanner can and can't see.

**The `eval()` and `exec()` findings on formatter.py and rewrite_ast.py are the cleanest example yet of the "scanner doesn't know what this code is for" failure mode.** Every prior scan had at least one finding to act on; logfire has none, *and* the patterns the scanner flagged are precisely the patterns that make the library useful. An f-string parser must `eval()` the user's expressions in the user's scope to extract them as structured attributes. An auto-tracer must `exec()` instrumented AST. Without those, you don't have an observability library — you have a `print()` wrapper. The static analyzer cannot tell the difference between a library that uses `eval()` for its core feature and an application that uses `eval()` on untrusted input.

**Pydantic's team is one of the most disciplined maintainer cohorts in the Python ecosystem**, and the codebase reflects that. The two false positives outside `logfire/_internal/` are documentation API-key placeholders and an Algolia public search key — both explicitly intentional. There's nothing slipping through.

## Notes on the tool

- **A "library-internal-feature" recognition heuristic** would be useful but is genuinely hard. Knowing that `eval()` inside a function called `compile_formatted_value()` in a file named `formatter.py` is part of a logging library's f-string parser requires the kind of code-context understanding static analyzers don't have. The half-step is curation; this scan just has nothing for the curation to *do*.
- **The `pickle.dumps`-for-pickleability-check idiom** has now appeared twice ([Upsonic's `cache.py:50`](upsonic-upsonic.html), here in `executors.py:78`). The Semgrep rule could distinguish "dumps that hashes/discards the result" from "loads of attacker-controlled blob"; the AST shape is clear.

## Disclosure timeline

- **2026-05-26** — Scan run at commit `bd08c7e0b9d7`. All findings curated to false-positive, public-by-design, or library-internal-feature.
- **2026-05-26** — No issue filed. There is nothing to action. This clean-scan write-up is published as the only artifact.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/pydantic/logfire" \
  --reports-dir reports/pydantic-logfire \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
