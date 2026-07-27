---
layout: default
title: "dimensionalOS/dimos: security scan"
date: 2026-07-27
---

# dimensionalOS/dimos - security scan

**Repository:** [dimensionalOS/dimos](https://github.com/dimensionalOS/dimos)
**Commit scanned:** `abf5152582f3e6d22d4e8cf3a91eb9bc25d795ce`
**Scan date:** 2026-07-27
**Disclosure status:** public — post-only (commercial-backed, secure-by-default, quality gate false)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 75 |
| Medium | 204 |
| Low | 0 |
| Info | 0 |

**Total findings:** 280 (`--min-severity medium`) — **0 real after curation**

This is the **25th clean scan** in the series, and the first to look at an
**agentic OS for physical robots**: dimOS (~3.8k★, Apache-2.0, *Dimensional
Inc.*) lets you command humanoids, quadrupeds, drones, and manipulators in
natural language, and build multi-agent systems wired to real cameras, lidar,
and actuators. When the thing your code drives is a two-legged robot in a
room with people, the question stops being "can an attacker read a file?" and
becomes "can an attacker **move the arm?**" — so that is the question this
scan chased.

## Top findings

### 1. The natural-language robot-command server is unauthenticated — but binds loopback by default

- **File:** `dimos/web/dimos_interface/api/server.py:77` (+ `dimos/agents/mcp/mcp_server.py:439`)
- **Tool:** semgrep (`wildcard-cors`) + manual
- **Confidence:** high (verdict: secure-by-default)
- **Why it matters:** `FastAPIServer` exposes `POST /submit_query` and
  `POST /unitree/command`, and both push the request text straight onto
  `query_subject` — the reactive stream that drives the robot. There is no
  auth dependency on those routes. This is the **same class** as the resolved
  [code-graph-rag #808](vitali87-code-graph-rag.html) unauth-control-endpoint
  finding — except the mitigation is already in place: `self.host` falls
  through to `global_config.listen_host`, whose **default is `127.0.0.1`**.
  The MCP server's Streamable-HTTP transport takes the same default. The
  loopback bind *is* the guard, so the command surface is not remotely
  reachable out of the box.
- **Recommendation:** The one genuinely not-well-built bit is the CORS block:
  `allow_origins=["*"]` **with** `allow_credentials=True` (Starlette reflects
  the Origin here) — the inverse of the
  [credit-the-defense](codegraphcontext-codegraphcontext.html) pattern seen
  elsewhere. Impact is bounded (loopback default; no session/cookie auth
  actually exists for credentials to leak), but it should be an explicit
  origin allowlist, and the robot-command routes deserve at least a shared
  token before anyone flips the host to `0.0.0.0`.

### 2. The lone Critical (chromadb pre-auth RCE) is not reachable — chromadb is embedded, not served

- **File:** `dimos/perception/spatial_vector_db.py:63`
- **Tool:** trivy (CVE-2026-45829, `uv.lock`)
- **Confidence:** high (verdict: version-match, not reachable)
- **Why it matters:** CVE-2026-45829 is a **pre-authentication** RCE in the
  ChromaDB **server's** `/api/v2/tenants/{tenant}/databases/{db}/collections`
  HTTP endpoint (via a malicious model repo + `trust_remote_code`). dimOS
  never stands that server up: it calls **`chromadb.Client()`** — the
  in-process embedded client — for spatial-perception vector storage. The
  vulnerable network endpoint does not exist in this deployment.
- **Recommendation:** Bump `chromadb` on the next dependency refresh for
  hygiene, but this is [version-match ≠ reachable](maziyarpanahi-openmed.html),
  not an exploitable path.

### 3. Seven XML parsers flagged for XXE are DoS-only — they read local robot descriptions

- **File:** `dimos/robot/model_parser.py:172` (+ 6 more: MJCF, Drake/roboplan world, discovery)
- **Tool:** semgrep (`use-defused-xml-parse`)
- **Confidence:** high (verdict: DoS-only, one concrete fix)
- **Why it matters:** every hit is stdlib `xml.etree.ElementTree.parse()` over
  a **robot-description file** — URDF, MuJoCo MJCF, Drake/roboplan world
  models. CPython's `etree` **does not resolve external entities**, so this is
  billion-laughs entity-expansion (local, self-inflicted on loading a crafted
  model file) — **not** XXE file-read/SSRF. Same
  [KiCAD-MCP](mixelpixx-kicad-mcp-server.html) /
  [CodeGraphContext](codegraphcontext-codegraphcontext.html) class.
- **Recommendation:** Swap `ElementTree` for `defusedxml` in the model
  parsers. This is the single concrete code change the scan surfaced.

### 4. The exec/eval/shell hits are operator-local tools and developer build config

- **Files:** `dimos/robot/cli/topic.py:156` (`eval`), `dimos/core/native_module.py:425`
  and `bin/build-cmu-nav-natives:131` (`shell=True`)
- **Tool:** semgrep (`eval-detected`, `subprocess-shell-true`)
- **Confidence:** high (verdict: by-design)
- **Why it matters:** the `eval` lives in `topic_send()` — a **CLI** helper
  where the operator types a message expression to publish to a ROS topic on
  their own machine. The two `shell=True` calls run a **developer-set**
  `NativeModuleConfig.build_command` (native robotics-module compilation, à la
  `make`) and a build script — neither takes network/user input. These are
  the [code-executor product surface](ag2ai-ag2.html), not injection sinks.

### 5. The 21-finding SQL cluster is the #1 identifier FP — with a guard

- **Files:** `dimos/memory2/{store,vectorstore,blobstore}/sqlite.py`, `pcap_to_db.py` ×2
- **Tool:** semgrep (`sqlalchemy-execute-raw-query` ×14 + `formatted-sql-query` ×7)
- **Confidence:** high (verdict: FP)
- **Why it matters:** every query **binds its data as `?` parameters**
  (embeddings, keys, blobs) and only interpolates an **internal table-name
  identifier** (`"{stream_name}_vec"`). The vector store even calls
  **`validate_identifier(stream_name)`** before use, and `stream_name` is an
  internal registry name, not user input. Textbook
  [#1 recurring parameterized-identifier FP](mnemosyne-oss-mnemosyne.html).

## Patterns observed

**Secure-by-default is the whole story on the control plane.** The scariest
thing a robot OS can ship is an unauthenticated way to make hardware move, and
dimOS technically ships one — `POST /unitree/command` has no auth. But the
web server, the MCP transport, and the visualizer all resolve their bind
address through one config field, `global_config.listen_host`, which defaults
to `127.0.0.1`. The scattered `0.0.0.0` literals elsewhere are exactly the
surfaces that *need* LAN reach — teleop from a phone or a Quest headset,
drone MAVLink, gstreamer video. The dangerous default is the safe one, and the
opt-in-to-expose surfaces are the device-connectivity ones. That is the right
shape, and it is the reason a 280-finding report curates to zero.

**Reachability, again, does more work than any scanner rank.** The single
Critical looked alarming — "pre-authentication code execution" on a robot
platform — and evaporated the moment you read line 63 of the vector DB:
`chromadb.Client()`, embedded, no server, no endpoint. The same lens flattens
the rest of the dependency wall. The `transformers` RCE is
[mitigation-shaped](maziyarpanahi-openmed.html): `trust_remote_code=True` is a
default, but the *models* default to pinned, trusted IDs
(`microsoft/Florence-2-base`, `vikhyatk/moondream2`) that require it to load
their own modeling code. The 11 Pillow CVEs are reachable through the vision
stack but are memory-safety DoS on crafted images. The LangSmith SDK CVEs sit
behind a transitive dep with no direct import site. None of it is a free kill.

**A safety-mature project reads differently.** dimOS ships an
[`AI_POLICY.md`](https://github.com/dimensionalOS/dimos/blob/main/AI_POLICY.md)
that opens with "the code here moves real hardware and is operating in
production in safety-critical real-world environments," requires that
contributors *understand every line* of a PR, and mandates simulation/replay
testing for anything that produces motion. That posture shows up in the code:
data values are bound, identifiers are validated, the risky default is
loopback. When the physical-world blast radius is this real, "the maintainers
take safety seriously" is not a platitude — it is visible in the diff. The
one honest hardening note is the wildcard-CORS-with-credentials pairing on the
loopback dev interface; the one honest code change is swapping in `defusedxml`.

## Notes on the tool

- **pip-audit ran without a timeout and hung.** `run_pip_audit`
  (`scanner/tools/pip_audit_runner.py`) calls `subprocess.run(...)` with **no
  `timeout=`**, unlike every other runner. On dimOS's heavy `pyproject.toml`
  (torch, transformers, ROS-adjacent deps) pip-audit tried to resolve the full
  tree and hung indefinitely; the scan only completed after the process was
  killed. Trivy already covered the dependency CVEs via `uv.lock`, so coverage
  survived — but the runner needs a bounded timeout + `TimeoutExpired` handling
  that writes `[]` and emits a `pip-audit-timeout` meta finding, matching the
  other runners. **→ backlog: pip-audit runner timeout.**
- **Git LFS blocked the clone.** dimOS pins large binary assets (robot meshes,
  gifs, data archives) via Git LFS; the default shallow clone tried to smudge
  them and stalled. Scanning source only needs `GIT_LFS_SKIP_SMUDGE=1`.
  **→ backlog: set `GIT_LFS_SKIP_SMUDGE=1` in `git_source.cloned_repo`** so
  LFS-heavy repos clone fast and never download irrelevant binaries.
- **Second lockfile went to Trivy, not pip-audit.** The Rust CVEs
  (`lz4_flex`, PyO3) live in `native/rust/Cargo.lock`. Trivy caught them;
  pip-audit is Python-only. Grouping dep findings **by lockfile**
  (`uv.lock` + `Cargo.lock`) keeps the reachability story straight — the
  [Kiln lockfile-coverage lesson](kiln-ai-kiln.html) generalizes to
  multi-language repos.
- The `defusedxml` recommendation and the identifier-FP collapse both landed
  correctly by hand; a rule that carries "etree = DoS-only, not XXE" context
  would save the manual step each time (recurring since KiCAD-MCP).

## Disclosure timeline

- 2026-07-27 - scan run (commit `abf5152`)
- 2026-07-27 - public post (this page). **Post-only**: commercial-backed
  (Dimensional Inc., CLA, dimensionalos.com), secure-by-default, and no real,
  exploitability-shaped, unmitigated finding — the quality gate is false, so
  nothing is filed upstream. The CORS-hardening and `defusedxml` notes are
  published as methodology commentary, not a disclosure.

## Reproduce

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/dimensionalOS/dimos /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/dimensionalos-dimos --min-severity medium
```
