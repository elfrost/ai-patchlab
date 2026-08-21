---
layout: default
title: "zilliztech/memsearch: security scan"
description: "Security scan of zilliztech/memsearch: 90 findings (90 above the medium floor), 1 real — Zilliz's semantic-memory layer for AI coding agents (2.5k★, MIT"
date: 2026-08-17
---

# zilliztech/memsearch — security scan

**Repository:** [zilliztech/memsearch](https://github.com/zilliztech/memsearch)
**Commit scanned:** `36216d63` (main at scan time)
**Scan date:** 2026-08-17
**Disclosure status:** disclosed — one real, exploitability-shaped finding filed
as a single focused issue (no working private channel: private vulnerability
reporting is disabled and there is no `SECURITY.md` at the repo, `.github`, or org
level). A fix PR accompanies the issue.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 38 |
| Medium | 52 |
| Low | — |
| Info | — |

**Total findings:** 90 above the medium floor · **1 real** (shell-injection in one
of four sibling plugins), the rest lockfile-only dependency CVEs and workflow /
FP classes covered below.

memsearch is Zilliz's cross-platform semantic-memory layer for AI coding agents
(2.5k★, MIT, Python core + one TypeScript/JS plugin per host: Claude Code, Codex,
DeepSeek Harness, OpenClaw, OpenCode). It indexes a project's markdown memory into
Milvus and exposes search to the agent. I picked it because it ships **five
near-parallel implementations of the same host-integration logic** — the single
best differential surface a scan can ask for — and because it is *not* a code
executor, so an unintended `bash` call is a defect, not product surface.

## Top finding

### 1. Shell injection in the OpenCode plugin's collection-name derivation

- **File:** `plugins/opencode/index.ts:71` (`deriveCollectionName`)
- **Tool:** found by the manual sibling-differential sweep, not the scanner
  (Semgrep's JS `detect-child-process` fired on this file but on the *other*
  three `exec` sites, not this one — see Notes)
- **Confidence:** high — verified with a differential repro
- **Why it matters:** the function runs

  ```ts
  execSync(`bash "${script}" "${projectDir}"`, { encoding: "utf-8", timeout: 5000 })
  ```

  `projectDir` is interpolated into a shell string with only double quotes and no
  escaping. On POSIX, Node's `execSync` runs the assembled string through
  `/bin/sh -c`, so a `$(…)` or backtick sequence anywhere in the path is
  command-substituted **before** `bash` ever sees it. `projectDir` is the
  directory OpenCode is opened in (`worktree`/`directory`, falling back to
  `process.cwd()`), and the same path flows in per-tool-call as
  `context.directory`. The call fires automatically on session start and on every
  `memory_search` / `memory_get` / `memory_transcript` in a directory that differs
  from the init directory.

  **Threat model:** a victim who opens (or whose session directory becomes) a
  directory whose *name* contains shell metacharacters — the classic
  "extract a hostile archive, open your agent in it" vector — gets arbitrary
  command execution at session start. Directory names on Linux/macOS may contain
  `$`, `(`, `)`, backticks and spaces; only `/` and NUL are forbidden. It is a
  local, precondition-gated defect, not a remote RCE — but it is real code
  execution and the precondition is one a user would not think of as dangerous.

- **The differential is what makes it unambiguous.** Three of the four other
  plugins run the *identical operation* safely, with an argv array and no shell:

  | Plugin | How it runs `derive-collection.sh` | Shell? |
  | --- | --- | --- |
  | `plugins/opencode/index.ts:71` | `execSync(\`bash "${script}" "${projectDir}"\`)` | **yes — vulnerable** |
  | `plugins/dsh/index.js:167` | `execFileSync('bash', [script, projectDir])` | no — safe |
  | `plugins/openclaw/index.ts:393` | `runCmd(["bash", script, scopeDir])` | no — safe |
  | `plugins/claude-code`, `plugins/codex` (hooks) | `"$…/derive-collection.sh" "$MEMSEARCH_DIR"` (quoted, inside bash) | n/a — safe |

  OpenCode is the sole outlier, and the exact fix idiom — `execFileSync('bash',
  [script, projectDir], …)` — already lives in the sibling `dsh` plugin.

- **Recommendation:** switch line 71 to `execFileSync("bash", [script,
  projectDir], { encoding: "utf-8", timeout: 5000 })` (add `execFileSync` to the
  `node:child_process` import). No shell, path passed as a literal argv element —
  identical behaviour, matches `dsh`.

## What was checked and cleared

The interesting part of this scan is how much of the surface is *correctly*
built. Each of these was a candidate finding that a read closed out:

- **`_filter_project_config` (config.py) is a strict recursive default-deny
  allowlist.** A repo-supplied `.memsearch.toml` can only set seven keys
  (`milvus.collection`, `embedding.batch_size`, two `chunking.*`, two
  `indexing.*`, `watch.debounce_ms`); everything else — `milvus.uri`,
  `milvus.token`, every `api_key`, every provider `base_url` — is dropped before
  the merge. This is the one real trust boundary in the product and it is
  enforced on both the load path and the `config set` path. Credit where due.
- **`_slugify` (skills.py) is an allowlist too** (`[^a-z0-9-]+ → -`, fallback
  `"skill"`). Every path-traversal primitive I threw at it — `../`, absolute
  paths, `..`, `.`, URL-encoded separators — collapses to a harmless slug, so the
  LLM-authored skill *name* can't escape the store directory.
- **The candidate → installed skill boundary is explicit.** Distillation writes
  *candidates*; `install()` (documented as "a deliberate, human-driven step") is
  the only thing that copies a SKILL.md into an agent's skill dir, and it is only
  reachable via `memsearch skills install`. The background maintenance runner
  distills but never installs.
- **The OpenCode capture daemon has no listener** — it polls a local SQLite DB;
  there is no socket, bind, or port. Its `sha1` is a turn-change fingerprint, and
  `ensure_isolated_config` actively unlinks symlinks before writing, which is a
  small defense in its own right.
- **The `_git_blob_hash` SHA-1 is mandated by git's object format** — an interop
  requirement, not a security hash. Flagging it would have been an active-harm FP.

## Patterns observed

**A five-way clone is a gift to a reviewer, and a liability to a maintainer.**
The same `deriveCollectionName` exists in five plugins. Four converged on the safe
argv form; one kept a shell string. This is the "Nth implementation that differs"
shape — the bug isn't that anyone wrote unsafe code from scratch, it's that a
shared behaviour drifted in exactly one copy and no single-file review would ever
see the other four to notice. The `scripts/sync-prompts.sh` in the repo keeps the
*prompt* files in lockstep across plugins; there is no equivalent guard keeping the
*invocation form* in lockstep, and that's precisely where the one defect lives.

**Almost every scanner "High" here is lockfile noise.** 36 of the 38 highs are
Trivy/pip-audit CVEs read out of `uv.lock` (pillow, aiohttp, langchain-core,
transformers, urllib3, pyasn1, cryptography). But the runtime dependency set in
`pyproject.toml` is nine packages — `pymilvus`, `milvus-lite`, `click`,
`watchdog`, `pathspec`, `setuptools`, `tomli_w`, `tomli`, `openai` — and none of
pillow/aiohttp/langchain/transformers is among them; they arrive transitively via
optional `[local]`/`[onnx]` extras or the dev/docs groups and the resolved lock.
The one runtime dep that *is* flagged, `setuptools` (pinned `>=78.1.1,<81`, CVE
fixed in 83.0.0), carries a real "bound excludes the fix" shape — but the CVE is a
`MANIFEST.in`-bypass at **sdist build time**, and memsearch builds with
`hatchling`, not setuptools. So the honest count of reachable dependency risk is
zero, and the honest count of real findings is one.

**"Not a code executor" is the curation lever.** For a memory tool, spawning
`bash derive-collection.sh <path>` is internal plumbing, not an advertised
capability — so the advertised-boundary test says command substitution triggered
by a *directory name* is unintended, and therefore a finding. On a code-executor
project the same `exec` would be product surface. Same construct, opposite verdict,
decided entirely by what the tool claims to do.

## Notes on the tool

- **Semgrep parse error swallowed the one workflow file worth reading.** The
  `errors` array (not `paths.skipped`, which was 0) held two `PartialParsing`
  entries on `.github/workflows/release.yml:98` — an `npm view "${{ … }}"` line.
  I read the file by hand: the workflow is `push`-tag + `workflow_dispatch` only,
  no `pull_request_target`, so the interpolation is maintainer-controlled and not
  a finding. But the coverage lesson repeats: a parser error means a file rendered
  as "clean" without a single rule running on it. This is the 16th coverage-row
  vote and the second on a workflow file specifically.
- **Semgrep's `detect-child-process` found the right file for the wrong reason.**
  It fired four times on `plugins/opencode/index.ts` — at lines 71, 158, 158, 204
  — but its signal is "a child process is spawned here", which is equally true of
  the two *safe* `shellEscape`'d sites (158, 204) as of the vulnerable one (71).
  The rule can't distinguish an escaped argv-ish call from an unescaped shell
  string, so the real finding was indistinguishable from three FPs in the raw
  output and only the manual sibling-differential separated them. A "same function
  implemented N ways, one differs" detector would have gone straight to it — this
  is now the strongest case in the series for cross-file same-shape diffing.
- **The dependency layer needs a "runtime vs transitive vs dev" column.** 36 of 38
  highs would have been correctly de-prioritised by reading `pyproject.toml`'s
  nine-package runtime set against the lock. The scanner reports the lock verbatim
  with no reachability tier, so "38 High" massively overstates the real exposure —
  the recurring SCA-reachability backlog item, biting again.

## Disclosure timeline

- **2026-08-17** — Scan run at commit `36216d63`; curated; differential repro
  confirming the injection built and run locally.
- **2026-08-17** — Single focused issue filed on zilliztech/memsearch with the
  code path, the sibling differential, and the one-line fix. Fix PR opened
  referencing it. No working private channel exists (PVR disabled, no `SECURITY.md`
  anywhere), so a single de-branded public issue is the only courtesy channel — one
  finding, not a grouped review.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/zilliztech/memsearch" \
  --reports-dir reports/zilliztech-memsearch \
  --min-severity medium
```

The one real finding was not produced by the scanner — it came from diffing the
five plugins' `derive-collection.sh` invocations by hand. The differential that
proves it (POSIX `/bin/sh -c` command-substitution on the OpenCode form vs. the
argv form the other plugins use) is a ten-line Node/bash script; the shape is
described in the Top finding above.

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed
separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
