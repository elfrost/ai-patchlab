---
layout: default
title: "dstackai/dstack: security scan"
date: 2026-05-26
---

# dstackai/dstack — security scan

**Repository:** [dstackai/dstack](https://github.com/dstackai/dstack) — 2.1k★, MPL-2.0, vendor-agnostic orchestration for AI training, inference, and agentic workloads. Python control plane + Go runner agent.
**Commit scanned:** `39d34533748d` (HEAD of `master` at scan time)
**Scan date:** 2026-05-26
**Disclosure status:** Public courtesy issue filed on the dstack repo. Every finding traces to a published CVE or a best-practice pattern — no private coordination required.

## Summary

| Severity | Count (raw) | Count (after ignore-file) |
| --- | ---: | ---: |
| Critical | 5 | 3 |
| High | 107 | 67 |
| Medium | 51 | 38 |
| Low | 0 | 0 |
| Info | 0 (filtered) | 0 (filtered) |

**163 raw findings → 108 after suppressing `examples/**`, `mkdocs/**`, `testing/**`, `migrations/**`. After curation: 3 real critical Go dependency CVEs (one of them SSH auth-bypass-shaped, directly relevant to dstack's threat model), 21 workflow-injection patterns (series-high), and a handful of best-practice items.**

dstack is the first scan in the series to **lead with three real Critical CVEs in a Go runtime** — and one of them is specifically the SSH-auth-bypass class. dstack's runner agent SSH's into remote machines to manage workloads, so the SSH-related CVE is directly in the threat path rather than incidental.

## Top findings (curated)

### 1. Three critical Go dependency CVEs in `runner/go.mod`

**Tool:** Trivy (high confidence — named advisories)
**Verdict:** **Real — all three are single-line `go.mod` bumps with public fix versions.**

#### CVE-2024-45337 — `golang.org/x/crypto` SSH `PublicKeyCallback` misuse → authorization bypass

> Applications and libraries which misuse `connection.serverAuthenticate` (via callback field `ServerConfig.PublicKeyCallback`) may be susceptible to an authorization bypass.

This is the one that matters most given dstack's architecture. The `golang.org/x/crypto` SSH library has a documentation/API trap where `ServerConfig.PublicKeyCallback` is called multiple times during a single authentication attempt, and an application that takes "the callback returned `nil` error once" as authorization can be tricked into accepting an attacker who briefly held a valid key. dstack's runner SSH's into remote VMs to launch and manage workloads — if any code path on the runner side uses `PublicKeyCallback` in the documented-but-misleading pattern, this CVE applies directly.

**Fix:** `golang.org/x/crypto >= 0.31.0`.

#### CVE-2024-41110 — Moby (Docker) authorization plugin bypass

> A security vulnerability has been detected in certain versions of Docker Engine, which could allow an attacker to bypass authorization plugins (AuthZ) under specific circumstances.

The `github.com/docker/docker` Moby library is used by the dstack runner for container orchestration. The advisory applies when the runner is deployed in environments using Docker's authorization-plugin layer for access control on the Docker socket.

**Fix:** `github.com/docker/docker >= 23.0.15 / 26.1.5 / 27.1.1 / 25.0.6` (multiple patched branches available).

#### CVE-2025-21613 — go-git argument injection

> An argument injection vulnerability was discovered in go-git versions prior to v5.13. Successful exploitation could allow an attacker to set arbitrary command-line arguments.

`github.com/go-git/go-git/v5` is used by dstack's runner to fetch user repositories for workloads. If a user-controlled remote URL ever reaches the affected go-git APIs, this is an argument-injection vector.

**Fix:** `github.com/go-git/go-git/v5 >= 5.13.0`.

All three are mechanical `go.mod` bumps. The order to prioritize them in: **`golang.org/x/crypto` first** (architecture-relevant), then go-git, then docker.

### 2. 21× workflow shell-injection / github-script-injection

**Files:** `.github/workflows/{build-artifacts,docker-amd-smi,...}.yml` (8 files affected)
**Tool:** Semgrep (`run-shell-injection`, medium confidence)
**Verdict:** **Real best-practice — series-high count for this class** (previous high was 17 on HolmesGPT).

`${{ ... }}` values interpolated into `run:` shell blocks at workflow-parse time, before shell quoting applies. Same template fix as upstream PRs [gptme #2399](https://github.com/gptme/gptme/pull/2399) and [PraisonAI #1677](https://github.com/MervinPraison/PraisonAI/pull/1677) — pass through `env:`, reference `$VAR` from the shell. 21 occurrences across 8 workflow files — large enough to warrant one dedicated cleanup pass rather than per-file fixes.

### 3. The Go runner's `exec.Command` sites — by design

**Files:** `runner/internal/runner/executor/executor.go:512`, `runner/internal/runner/ssh/sshd.go:126`, `runner/internal/shim/components/utils.go:101`, `runner/internal/shim/dcgm/exporter.go:126`
**Tool:** Semgrep (`dangerous-exec-command`, medium confidence)
**Verdict:** **By design — the runner *is* a job-execution agent.**

dstack's runner exists to execute user-defined workloads (containers, SSH sessions, GPU monitoring agents). `exec.Command` calls in `executor.go`, `sshd.go`, `utils.go`, and `exporter.go` are the runner's job-execution and process-management primitives. The trust model is the same as every agent in this series: the user authors the workload spec, the user runs the runner under their own identity. A one-line code comment on each call site documenting the trust boundary would just stop scanners from re-flagging — no behavioral change needed.

### 4. ~9 Dockerfiles run as root

**Files:** `docker/{amd-smi,base/Dockerfile.common,dind,server/Dockerfile.nebius,server/release,...}/Dockerfile`
**Tool:** Trivy (`missing-user`, medium confidence)
**Verdict:** **Real best-practice.** Same shape as on multiple prior scans. A `USER` directive added to each container image; ideally a shared base image bakes it in once. Four of these images also omit `--no-install-recommends` on `apt-get install`, which compounds the package surface.

### 5. The false positives, briefly

| Finding | Verdict |
|---|---|
| 4× `logger-credential-leak` in `src/dstack/_internal/...` | **FP** — same rule class that has now produced 6/6 false positives across the series. Already actioned in the [honcho write-up](plastic-labs-honcho.html) (downgrade to `low` confidence). |
| 11× "secret detected" in `src/tests/_internal/...`, `frontend/.../constants.tsx`, `scripts/packer/README.md` | **FP** — encryption-test fixtures, frontend-form placeholder labels, README scripts |
| 4× `python37-compatibility-importlib2` | **Not security** — Python 3.7 compat hint |
| 2× `direct-use-of-jinja2` in `scripts/add_backend.py` | **By design** — internal script rendering template files, no HTML |
| 4× `sqlalchemy-execute-raw-query` in `migrations/**` | **Suppressed via `--ignore-file`** — Alembic migration script identifier interpolation, same class as Upsonic / PraisonAI / honcho |

## Patterns observed

**dstack is the first scan with a real critical in the Go ecosystem on the main binary's lockfile.** Prior scans surfaced criticals in npm lockfiles ([Klavis](klavis-ai-klavis.html), [honcho](plastic-labs-honcho.html)) and a single Python dep ([guardrails](guardrails-ai-guardrails.html)). The runner being a Go binary that does SSH and Docker orchestration means its `go.mod` is fully in scope, and three real public CVEs sat there waiting for a routine bump. This is what the dep-scan layer is for — none of these three findings was visible to the SAST passes (Semgrep, the `dangerous-exec-command` rule). Trivy did the work.

**The SSH `PublicKeyCallback` advisory is the cleanest "scanner caught something architecturally relevant" example in the series.** CVE-2024-45337 is *exactly* the class of vulnerability a vendor-agnostic orchestrator that SSH's into remote machines cares about. Whether or not dstack's specific use of the API trips the documented misuse pattern, the runner upgrading past 0.31.0 is the safe default. The same advisory shipped against many Go projects this year; bumping is mechanical.

**Workflow-injection count keeps climbing.** Six consecutive scans of mid-popularity Python projects, each with the same `${{ ... }}` → `run:` shell interpolation pattern across multiple workflow files: gptme (8, resolved), PraisonAI (2, resolved), airweave (8, open), guardrails (4, open), honcho (4, open), HolmesGPT (17, open), now dstack (21, open). The class is the single most universal finding in the series. A standalone "fix-workflow-inputs.py" tool that mechanically rewrites `run:`-level interpolations to `env:` blocks would clear it across every codebase scanned. Worth thinking about as a follow-on tool.

**`logger-credential-leak` is now 6/6 false positives.** The downgrade-to-low promotion stands; this scan adds another four FP data points in `src/dstack/_internal/core/services/repos.py` and `users.py`.

## Notes on the tool

- **A standalone workflow-injection auto-fixer** is the highest-leverage tool extension this series has surfaced. Seven consecutive scans of the same pattern, mechanical fix, no judgment call needed. Worth a separate project (or a `scripts/` helper in ai-patchlab).
- **Trivy `go.mod` findings carry their full advisory metadata** — fix version, advisory URL, package name — which makes the curation easier than for the Python `pip-audit` findings where the JSON output is sparser. Worth normalizing across the dep-scan layer.

## Disclosure timeline

- **2026-05-26** — Scan run at commit `39d34533748d`; `examples/**`, `mkdocs/**`, `testing/**`, `migrations/**` suppressed; findings curated.
- **2026-05-26** — Public courtesy issue filed on dstackai/dstack. All findings trace to published CVEs or best-practice patterns; no private coordination required.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/dstackai/dstack" \
  --reports-dir reports/dstackai-dstack \
  --min-severity medium \
  --ignore-file reports/dstackai-dstack/.aipatchlabignore
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
