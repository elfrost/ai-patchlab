---
layout: default
title: "dstackai/dstack: security scan"
date: 2026-05-26
---

# dstackai/dstack — security scan

**Repository:** [dstackai/dstack](https://github.com/dstackai/dstack) — 2.1k★, MPL-2.0, vendor-agnostic orchestration for AI training, inference, and agentic workloads. Python control plane + Go runner agent.
**Commit scanned:** `39d34533748d` (HEAD of `master` at scan time)
**Scan date:** 2026-05-26
**Disclosure status:** ❌ **Issue declined by maintainer.** [Issue #3908](https://github.com/dstackai/dstack/issues/3908) was closed on 2026-05-27 by dstack maintainer [@peterschmidt85](https://github.com/peterschmidt85) as not meeting the project's disclosure-format requirements (paraphrased: one vulnerability per issue, explicit exploitability description against dstack users, no third-party repo links, no "shallow runs of security tools"). Honest record kept here in lieu of removing the post; the technical content — three published CVEs in `runner/go.mod`, plus the workflow-injection class — remains independently verifiable from the lockfile. The published-CVE recommendation stands regardless of whether the maintainer accepts it through the issue channel. See the [Maintainer response](#maintainer-response-and-lessons) section below.

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
- **2026-05-26** — Public courtesy issue [#3908](https://github.com/dstackai/dstack/issues/3908) filed on dstackai/dstack.
- **2026-05-27** — Issue closed by maintainer [@peterschmidt85](https://github.com/peterschmidt85) as not meeting the project's disclosure format. See below.

## Maintainer response and lessons

The closure comment, quoted in full:

> Dear @elfrost, we're deleting this issue since its description contains direct advertising of another repo and is considered spam. If you care to submit security reports to dstack repo, do not include any third-party repo links, plus do submit security issues separately (one vulnerability per issue) and ensure to describe how the vulnerability can be exploited by dstack users. Shallow runs of security tools on a repo are not accepted. Really appreciate your good will to improve security of other [projects].

This is the first declined issue in fifteen scans, and the feedback is worth taking seriously on its own terms — separate from whether the "advertising" framing is fair to the report's actual content (the technical items are real published CVEs, not a tool pitch). Four specific requirements the maintainer flagged, three of which are reasonable enough to fold into the methodology going forward:

1. **One vulnerability per issue.** dstack is the first scan target with this explicit norm. Across the series so far, the "grouped courtesy issue" pattern has worked on every repo that accepted reports (gptme, PraisonAI, airweave, guardrails, Klavis, HolmesGPT, honcho, dograh — eight projects, two resolved, none rejected on grouping). dstack is the outlier, and a reasonable one given a security team's need to track resolution per-CVE. **Lesson applied:** for repos with formal SECURITY.md or explicit per-vulnerability norms, file separate issues going forward.
2. **Describe how the vulnerability can be exploited by users of *this* project.** Also fair. The original issue cited the SSH `PublicKeyCallback` CVE and noted dstack's runner SSH's into remote VMs — but didn't say "here's the specific code path on the runner that uses the affected API." For a Go advisory in a Go binary, a maintainer reasonably wants to know whether the misuse pattern is actually present in the codebase, not just whether the library is present in the lockfile. **Lesson applied:** for high-severity dep CVEs, include a `grep` for the affected API in the codebase as part of the report.
3. **No third-party repo links.** The original issue linked to the AI PatchLab repo and the public write-up of this scan. For a security team that doesn't recognize the tool, those links read as promotion. **Lesson applied:** for repos where the maintainer culture is unknown, scope the issue to dstack-only content and mention the source tool minimally if at all (footer line, no link).
4. **"Shallow runs of security tools on a repo are not accepted."** This one's the harder push-back to fully absorb. The dep-scan findings here aren't from a "shallow run" — they're three published Go CVEs sitting in the runner's `go.mod` at versions older than the advisory fix versions. Bumping the deps would clear them regardless of whose tool surfaced them. But the framing is the maintainer's prerogative; a different repo's norm doesn't override their own intake policy.

The technical content of this write-up — the three Go criticals, the workflow-injection count, the FP analysis — remains independently verifiable from the lockfile and the workflow files at the scanned commit. The post is kept up as an honest record of what happened (both the findings and the maintainer's response) rather than removed; pretending the rejection didn't happen would be worse than the rejection itself.

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
