---
layout: default
title: "AgentEra/Agently: security scan"
date: 2026-07-03
---

# AgentEra/Agently - security scan

**Repository:** [AgentEra/Agently](https://github.com/AgentEra/Agently)
**Commit scanned:** `9ea830be26f0e37ebf621b054aa91c766d28f70d`
**Scan date:** 2026-07-03
**Disclosure status:** disclosed — one focused issue filed ([#312](https://github.com/AgentEra/Agently/issues/312))

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 15 |
| Medium | 10 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 25 — 14 are one parameterized-SQL false-positive cluster; the real signal is a single sandbox-escape.

Agently is a widely-used GenAI application framework (Apache-2.0, ~1.6k stars,
millions of PyPI downloads). It ships an agent action that runs
**model-generated Python** through a component named `PythonSandbox`. That is
the interesting surface, and it's where the one real finding lives — the rest of
the scan is a clean, well-parameterized persistence layer that the SQL rules
misread.

## Top findings

### 1. `PythonSandbox` restricted-exec is escapable — model code can reach host RCE (filed: #312)

- **File:** `agently/utils/PythonSandbox.py:98`, reached via `agently/builtins/plugins/ActionExecutor/PythonSandboxActionExecutor.py`
- **Tool:** semgrep (`exec-detected`) + manual trust-path review
- **Confidence:** high — real, exploitability-shaped
- **Why it matters:** `PythonSandboxActionExecutor` executes the model's tool
  argument — `raw_code = action_input.get("python_code", "")` → `sandbox.run(python_code)`
  → `exec(code, {"__builtins__": SAFE_BUILTINS}, local_vars)`. The utils guide
  presents this as running snippets *"safely,"* *"in a sandbox,"* with *"safety
  checks."* But the guard is incomplete: `SAFE_BUILTINS` drops
  `__import__`/`open`/`eval`, and `ObjectWrapper.__getattr__` blocks `_`-prefixed
  access — **only on wrapped `preset_objects`**. Literals the executed code
  creates itself (`()`, `""`, `[]`) are never wrapped, so
  `().__class__.__bases__[0].__subclasses__()` walks to `subprocess.Popen`/`os`
  and escapes; `_check_safe_value` only inspects *return* values, not the side
  effects that fire during execution. A model emitting the right snippet through
  the Python-sandbox action gets host command execution.
- **Recommendation (as filed):** either re-label `PythonSandbox` as a
  best-effort convenience for *trusted* expressions (explicitly not an isolation
  boundary for model-generated code), or move untrusted execution to OS-level
  isolation (container / `subprocess` + seccomp / microVM). In-process CPython
  `exec` with a restricted-globals dict is a known-unsecurable pattern.

### 2. The 14 "high" SQL findings are a parameterized-query false positive

- **File:** `agently/core/workspace/LocalBackend.py` (14 × `sqlalchemy-execute-raw-query` / `formatted-sql-query`)
- **Tool:** semgrep
- **Confidence:** high — FP
- **Why it matters / why it doesn't:** This is the workspace SQLite persistence
  layer, and it's written correctly. The `IN`-clause queries build
  `placeholders = ",".join("?" for _ in record_ids)` and pass the values as bound
  parameters (`conn.execute(sql, [*record_ids, ...])`); the only f-string
  interpolation is either those `?` placeholders or **internal schema constants**
  (`ALTER TABLE ... ADD COLUMN {column} {column_type}` where `column`/`column_type`
  come from a hardcoded dict). No user- or model-controlled value is concatenated
  into SQL. The rule flags the f-string SQL text and can't see the parameter
  binding.

### 3. A secondary Windows-only `shell=True` hardening

- **File:** `agently/builtins/actions/Browse.py:939`
- **Tool:** semgrep (`subprocess-shell-true`)
- **Confidence:** low — defense-in-depth
- **Why it matters:** `_activate_browser` runs `subprocess.run(f'start "" "{app}"', shell=True)`
  on Windows to focus a browser. The macOS sibling in the same function already
  uses the safe argv form (`["osascript", "-e", ...]`); only the Windows branch
  interpolates into a shell string. The input (`self.pyautogui_browser_app`) is a
  developer config value, not a model/network input, so this is not a live
  injection — but making the Windows branch consistent with the argv-based macOS
  branch would remove the anti-pattern. Not filed (config-controlled, low
  severity); noted here.

## Patterns observed

**"Sandbox" is a security claim, and this one doesn't hold — which is exactly
why it's the finding.** The AG2 scan the week before had `exec`/`docker-run`
everywhere and none of it was a finding, because AG2's `LocalCommandLineCodeExecutor`
is *documented* as unsandboxed (use the Docker executor for isolation). Agently
is the inverse: a component **named** `PythonSandbox`, described as running code
*"safely,"* wired to execute model output — where the isolation is best-effort
restricted-`exec` that the standard `__subclasses__` walk defeats. A tool that
*advertises* a boundary it doesn't enforce is more dangerous than one that
honestly says "no boundary here," because users route untrusted code through it
on the strength of the name. The fix is usually documentation (call it
best-effort) or real OS-level isolation, not a bigger builtins denylist.

**The rest of the code is clean, and the SQL cluster shows why the count lies.**
14 of the 15 "highs" are one file's SQLite layer, all correctly parameterized
(bound values, internal-only identifier interpolation) — the same
`sqlalchemy-execute-raw-query` false-positive shape seen on codex-lb and
inspect_ai. Strip that cluster and the examples/tests, and the scan is one real
item. Dependencies are clean (trivy and pip-audit both empty), and there are no
secrets (gitleaks clean).

**One focused issue, not a review dump.** The SQL cluster, the plugin
`non-literal-import`s (the lazy-import mechanism), the non-crypto SHA-1
(blueprint IDs), and the `eval`/`exec` hits in `examples/` are all noise or
by-design. Filing all of it would bury the one thing that matters. The issue
(#312) leads with the code path — model input → `python_code` → `exec` — and the
concrete escape, and credits the existing `_`-attr guard.

## Notes on the tool

- **`exec-detected` needs a trust-source signal, not just a location.** The two
  `exec` hits were `PythonSandbox.py` (real, runs model code) and an
  `examples/` file (noise). What distinguished them was tracing the argument
  back to `action_input["python_code"]`. A dataflow hint — "is the exec'd string
  reachable from a tool/handler argument?" — would rank the real one first.
- **The `sqlalchemy-execute-raw-query` / `formatted-sql-query` false-positive
  cluster keeps recurring** (codex-lb, inspect_ai, now Agently). A check for
  whether the `execute()` call passes a parameter tuple, and whether the only
  interpolated tokens are `?` placeholders or constants, would collapse these.
  Highest-value backlog item across the last several scans.
- **`subprocess-shell-true` could note the sibling-call inconsistency.** Here the
  same function had a safe argv call (macOS) and a `shell=True` call (Windows);
  surfacing "a nearby call does this safely" would sharpen the hardening advice.

## Disclosure timeline

- 2026-07-03 — scan run
- 2026-07-03 — issue [#312](https://github.com/AgentEra/Agently/issues/312)
  filed (PythonSandbox escape); public post (this page)
- 2026-07-07 — **maintainer confirmed and fixed** (in dev). Maplemx: *"We
  confirmed the issue: the in-process restricted `exec` path should not be
  treated as an isolation boundary for model-supplied or otherwise untrusted
  Python code."* The fix is comprehensive rather than a denylist patch:
  `agent.enable_python/​shell/​nodejs` now default to `sandbox="auto"`, which uses
  **Docker-backed execution and fails closed** (structured diagnostics) when
  Docker is unavailable; the old in-process runner is retained only behind an
  explicit `sandbox="trusted_local"` opt-in. A new
  `agent.enable_code_runtime(language=...)` adds Docker-backed runtimes for
  ~15 languages, with `provisioning_profile` (strict/developer/ci) and image-pull
  controls. Validation: pyright clean, 145-test sandbox regression suite green,
  a real Docker Node smoke test. Merged to their dev line (`39a2e75c`); the
  maintainer is holding the issue open until the public branch/release ships.
  *(This page will move to ✅ resolved once the fix is public.)*

## Reproduce

```bash
git clone https://github.com/AgentEra/Agently /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/agentera-agently \
  --min-severity medium --ignore-samples
```
