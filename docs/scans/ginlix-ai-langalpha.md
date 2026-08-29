---
layout: default
title: "ginlix-ai/LangAlpha: security scan"
date: 2026-08-29
---

# ginlix-ai/LangAlpha - security scan

**Repository:** [ginlix-ai/LangAlpha](https://github.com/ginlix-ai/LangAlpha)
**Commit scanned:** `f5232fa2` (main at scan time)
**Scan date:** 2026-08-29
**Disclosure status:** disclosed — one real finding filed as a single focused
public issue. No `SECURITY.md` at the repository root, in `.github/`, in
`docs/`, or at the organisation level, and private vulnerability reporting is
disabled (confirmed with an empty-payload control request, which returned
`403 Repository does not have private vulnerability reporting enabled` — it
files nothing). A public issue is the only channel the project offers.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 209 |
| Medium | 160 |
| Low | 0 |
| Info | 3 |

**Total findings:** 372 (1 real after curation)

This is a financial-market agent platform: a FastAPI backend, a React frontend,
a Daytona-or-Docker sandbox in which the agent runs code, MCP server plumbing,
and a per-workspace secret vault. It is one of the most carefully defended
codebases this series has scanned, and most of this write-up is about why 371
findings did not survive.

## Top findings

### 1. The unauthenticated preview redirect can start a stopped sandbox — the one thing its own docstring says it will not do

- **File:** `src/server/app/workspace_sandbox.py:783-810`
- **Tool:** none — no scanner produced this
- **Confidence:** high on the code path, moderate on how often the precondition holds
- **Severity:** low-to-medium (denial-of-wallet; no data exposure)

`GET /api/v1/preview/{workspace_id}/{port}` is deliberately unauthenticated.
The workspace UUID is the bearer credential, and the route is meant to be
embedded in shared reports. Its docstring is explicit about the risk:

> Unlike the authenticated POST endpoint, the unauthenticated redirect does NOT
> start stopped sandboxes (to prevent denial-of-wallet via cheap GET requests).

The implementation enforces that with a single check against the database row:

```python
if not workspace or workspace.get("status") != "running":
    raise HTTPException(status_code=404, detail="Preview not available")
```

and then, having passed it, calls the *acquisition* path:

```python
session = await manager.get_session_for_workspace(
    workspace_id, user_id=workspace.get("user_id")
)
```

`get_session_for_workspace` is documented as "Get or **restart** a session for a
workspace". On the `status == "running"` branch it reaches
`_attach_running_session` → `Session.initialize(sandbox_id=...)` →
`PTCSandbox.reconnect(...)`, whose own docstring reads: *"Reconnect to a stopped
sandbox. This is a fast path for session persistence — it **starts a stopped
sandbox**."* If the sandbox is positively absent rather than stopped, the
`SandboxGoneError` branch calls `_recover_sandbox`, which provisions a **new
billed sandbox**.

So the guarantee holds only as long as the database row is never `running` while
the sandbox is not. The reason to think that gap is real is that this repository
says so itself, in three other places. Four sibling call sites — the
unauthenticated `wsfiles` serve route and three shared-thread file routes —
solve exactly this problem and refuse exactly this call:

```python
# src/server/app/public.py:414-419
# never call get_session_for_workspace(), which would do a Daytona
# attach/restart and let an unauthenticated UUID-only request wake a sandbox
# (denial-of-wallet). A stale 'running' DB row with no warm session -> DB-only.
session = manager.get_session_if_ready(
    workspace_id, expected_sandbox_id=workspace.get("sandbox_id")
)
```

`get_session_if_ready` exists for this purpose — "Still no I/O and no wake — the
unauthenticated routes must never let a UUID-only request start a sandbox" — and
its `expected_sandbox_id` parameter was made keyword-only and mandatory
specifically "so a new caller cannot omit the fence." The preview redirect is
the one unauthenticated route that never adopted it.

The majority sibling is the contract here. Four call sites treat a stale
`running` row as a real state that must not be trusted; one treats it as
sufficient proof that no wake can happen.

**Recommendation:** mirror the siblings — resolve the session with
`get_session_if_ready(workspace_id, expected_sandbox_id=workspace.get("sandbox_id"))`
and return the same uniform 404 when it is `None`. That is not a behaviour
change against the documented intent: `test_returns_404_for_stopped` already
pins "stopped → 404, no wake", and the agent's own `GetPreviewUrl` tool restarts
a preview *server* inside a running sandbox, which is a different operation. It
only closes the case the tests never cover.

## Patterns observed

**The interesting result here is a negative one, and it took the most work.**
Semgrep's single highest-severity finding was `pull_request_target` with a
checkout of untrusted fork code in `.github/workflows/fork-integration.yml` —
normally a live repository-compromise path, and not something the repository
tree alone can settle. Querying the GitHub environments API settles it: a
`fork-ci` environment exists with `required_reviewers` set to the maintainer and
`prevent_self_review: true`. The workflow pins `ref` to the immutable head SHA
so a post-approval force-push cannot swap in unreviewed code, sets
`persist-credentials: false`, and drops the token to `contents: read`. The
author also wrote down the part almost everyone misses — that `uv sync` runs
fork-controlled build hooks *before* pytest, so the reviewer must audit build
config and the lockfile, not just the test files. That is a better threat model
than the rule that flagged it.

**The defenses are unusually specific.** The unauthenticated file-serving route
redacts vault secrets from any UTF-8-decodable body rather than from declared
text MIME types, with a comment explaining that otherwise a secret written to a
mis-named `secret.png` would slip through. Its CSP uses `connect-src 'none'` as
the load-bearing control so a prompt-injected agent report cannot exfiltrate its
own contents. `_is_serve_blocked_path` turns out to be *stricter* than the
authenticated read and download endpoints it claims to mirror, which is the
correct direction for the asymmetry. All 30 Gitleaks hits are fixtures inside
the project's own secret-redaction and leak-detection test suites.

**Which is exactly why the one finding is the shape it is.** On a codebase this
careful, the bug that survives is not a missing check — it is two individually
correct decisions in different files that stop composing. The preview redirect's
DB-status check is correct. The session acquisition path is correct. The
guarantee only fails at the seam, and only because a fifth route did not inherit
a fence the other four were given. No pattern rule can see that; it is visible
only by tabulating every unauthenticated route against the accessor it uses.

**The 102-finding SQL cluster was noise again, for the ninth time in this
series.** Every hit in `src/server/database/` binds its values with `%s`
placeholders; the only f-string interpolation is `{_WS_COLS}`, a module-level
constant column list. Two reads settle the whole cluster.

## Notes on the tool

**The coverage warning was the lead.** AI PatchLab reported that Semgrep failed
to parse three workflow files — `claude.yml`, `release.yml`, and
`sandbox-integration.yml` — and timed out two rules. Those three were precisely
the workflows most likely to carry injection, so "no findings there" meant
"nothing looked." Reading them by hand is what mapped the CI surface, and it is
what turned up that `claude.yml` deliberately passes `REVIEW_BODY` through the
environment rather than interpolating it into a `run:` block. A scanner that had
silently reported zero on those files would have been actively misleading.

**The lockfile gap fired correctly and mattered.** pip-audit resolved
dependencies from `pyproject.toml` — declared version floors — while the project
ships and installs from `uv.lock`. The dependency result therefore describes an
install path the project does not use. The meta finding said so rather than
letting an empty `[]` read as "clean."

**Backlog item:** the two remaining `run-shell-injection` hits
(`release.yml:29`, `sandbox-integration.yml:288`) are both reachable only via
`workflow_dispatch` or a same-repo `pull_request`, where the actor already holds
write access. Severity for that rule is a function of the workflow trigger, and
the tool does not yet read the trigger. That would have collapsed two
high-severity findings automatically instead of by hand.

## Disclosure timeline

- **2026-08-29** — scan run at commit `f5232fa2`; curated.
- **2026-08-29** — channel probed: PVR disabled (empty-payload control returned
  403), no `SECURITY.md` at root, `.github/`, `docs/`, or organisation level.
- **2026-08-29** — single focused public issue filed with the code path, the
  four-sibling differential, and the fix —
  [issue #378](https://github.com/ginlix-ai/LangAlpha/issues/378). One finding,
  not a grouped review. No PR opened: the fix is one file, but choosing 404 vs
  503 for a sleeping sandbox is a product decision the maintainer should make.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/ginlix-ai/LangAlpha" \
  --reports-dir reports/ginlix-ai-langalpha \
  --min-severity medium --ignore-samples
```

The one real finding was not produced by the scanner. It came from listing every
router registered in `src/server/app/setup.py`, keeping the four the comments
mark as unauthenticated, and tabulating which session accessor each one calls.
Four call `get_session_if_ready`. One calls `get_session_for_workspace`.
