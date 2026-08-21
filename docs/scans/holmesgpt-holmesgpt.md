---
layout: default
title: "HolmesGPT/holmesgpt: security scan"
description: "Security scan of HolmesGPT/holmesgpt: 2,143 findings, 93% are an SRE agent's deliberately-broken Kubernetes test fixtures"
date: 2026-05-21
---

# HolmesGPT/holmesgpt — security scan

**Repository:** [HolmesGPT/holmesgpt](https://github.com/HolmesGPT/holmesgpt) — 2.5k★, Apache-2.0, an SRE agent that diagnoses Kubernetes / cloud incidents. CNCF Sandbox project.
**Commit scanned:** `46b0a93a6dfe` (HEAD of `master` at scan time)
**Scan date:** 2026-05-21
**Disclosure status:** Public courtesy issue filed on the holmesgpt repo. Every finding traces to a published CVE or a best-practice pattern — no private coordination required.

## Summary

| Severity | Count (raw) | Count (after ignore-file) |
| --- | ---: | ---: |
| Critical | 0 | 0 |
| High | 934 | 77 |
| Medium | 1,209 | 67 |
| Low | 0 | 0 |
| Info | 0 (filtered) | 0 (filtered) |

**2,143 raw findings → 144 after suppressing `tests/**/fixtures/**` and `docs/**`. After curation: one recurring real cluster (17 workflow-injection patterns), a drifted experimental front-end (~45 dependency CVEs), and a handful of best-practice items. ~2,000 of the raw findings — 93% — are a single false-positive class.**

This is the second-largest raw count in the series after [Klavis](klavis-ai-klavis.html), and like Klavis the headline number is misleading — but for a much more specific reason, and one worth dwelling on.

## The 93% false positive: an SRE agent's test fixtures are broken Kubernetes by design

HolmesGPT is an **SRE agent** — its job is to look at a misconfigured, failing, or compromised Kubernetes cluster and explain what's wrong. To test that, its `tests/llm/fixtures/**` directory contains ~2,000 deliberately-imperfect Kubernetes manifests: Grafana/Loki/Prometheus/Tempo deployments and demo apps (the `sock-shop` microservices demo, Kafka apps) configured with exactly the problems an SRE agent must learn to spot.

Trivy, scanning those manifests, dutifully reports every one:

| Trivy rule | Count | What it's flagging |
| --- | ---: | --- |
| Default security context configured | 545 | fixture pods without a hardened `securityContext` |
| Can elevate its own privileges | 306 | fixture pods missing `allowPrivilegeEscalation: false` |
| Seccomp policies disabled | 306 | fixture pods without a seccomp profile |
| Runs as root user | 290 | fixture pods without `runAsNonRoot` |
| Root file system is not read-only | 283 | fixture pods without `readOnlyRootFilesystem` |
| (8 more K8s-misconfig rules) | ~270 | image tags, registries, privileged ports, capabilities |

Every one of these is in `tests/llm/fixtures/**`. None describes HolmesGPT's own deployed infrastructure. They describe **the broken clusters HolmesGPT exists to diagnose**. Flagging them as security findings against the HolmesGPT repo is exactly backwards — they are the *input* to the product, not a defect in it.

This is the same meta-pattern surfaced on [agentic_security's PII-detector test fixtures](msoedov-agentic-security.html), [PraisonAI's secret-redaction regex](mervinpraison-praisonai.html), and [Giskard's `detect-secrets` baseline](giskard-ai-giskard-oss.html) — but it's the largest and clearest specimen yet. A scanner with no awareness of "this directory holds the deliberately-imperfect inputs to a diagnostic tool" will always produce this. Path-suppression (`tests/**/fixtures/**`) handles it cleanly; the 2,000 findings vanish and the real 144 become triageable.

## Top findings (curated, after ignore-file)

### 1. 17× workflow shell-injection / github-script-injection

**Files:** `.github/workflows/{build-and-test,build-binaries-and-brew,eval-regression}.yaml`, `.github/actions/{setup-kind-cluster,post-eval-comment}/action.yml`
**Tool:** Semgrep (`run-shell-injection` ×15, `github-script-injection` ×2, medium confidence)
**Verdict:** **Real best-practice — the recurring class, now seen on six consecutive scans.**

`${{ ... }}` values interpolated into `run:` shell blocks (and one `actions/github-script` JS literal) at workflow-parse time. The fix is the standard `env:` indirection, with the same template as [gptme PR #2399](https://github.com/gptme/gptme/pull/2399) and [PraisonAI PR #1677](https://github.com/MervinPraison/PraisonAI/pull/1677). 17 occurrences is the highest count of this class in the series so far — worth a single dedicated cleanup pass.

### 2. ~45 dependency CVEs in `experimental/ag-ui/front-end/yarn.lock`

**Tool:** Trivy (high/medium confidence — named advisories)
**Verdict:** **Real, but scoped to an `experimental/` subtree.**

A long advisory tail — `minimatch` (9), `node-forge` (7), `lodash` (3), `webpack-dev-server` (3), plus `ajv`, `postcss`, `js-yaml`, `serialize-javascript`, `follow-redirects` (custom-auth-header leak on cross-domain redirect), a `@babel/plugin-transform-modules-systemjs` arbitrary-code-generation advisory, and more. All in one `yarn.lock`, under `experimental/ag-ui/front-end/`.

The `experimental/` prefix matters: this is explicitly not the supported product. But "experimental" and "in the public default branch" together still mean a contributor can `yarn install` it and run the dev server. Two clean options: either bring the lockfile under the same dependency-update cadence as the rest of the repo, or move `experimental/` out of the default branch (a branch or a separate repo) so its drift isn't part of the shipped surface. Same subtree also has the one `wildcard-cors` finding (`server-agui.py:89`).

### 3. 1× LiteLLM advisory in `poetry.lock`

**Verdict:** **Real — main-project dependency.** Unlike the experimental front-end, this is HolmesGPT's actual Python dependency tree. A `litellm` bump (plus the minor `idna` / `python-dotenv` advisories Trivy also flags in `poetry.lock`) clears it. Same finding class as [the guardrails scan](guardrails-ai-guardrails.html).

### 4. 6× `subprocess.run(..., shell=True)` in the agent's command core

**Files:** `holmes/core/tools.py:677,951`, `holmes/interactive.py`, `holmes/plugins/toolsets/bash/common/bash.py`
**Verdict:** **By design — the SRE agent's command-execution primitive.**

```python
def __execute_subprocess(self, cmd: str) -> Tuple[str, int]:
    protected_cmd = get_ulimit_prefix() + cmd
    result = subprocess.run(
        protected_cmd, shell=True, executable="/bin/bash",
        check=False, stdin=subprocess.DEVNULL, ...
    )
```

HolmesGPT runs diagnostic commands (`kubectl`, log greps, etc.) constructed by its toolsets — `shell=True` is needed for the pipe/redirect features those commands use, and the code already wraps each invocation with a `get_ulimit_prefix()` resource guard. The trust model is the same as every agent in this series ([gptme](gptme-gptme.html), [Upsonic](upsonic-upsonic.html)): the agent builds the command, the operator runs the agent. Worth a one-line comment documenting that, so scanners and contributors both get the signal — but not a defect.

### 5. Dockerfile hardening

`Dockerfile` runs as root (no `USER`), three `apt-get install` lines omit `--no-install-recommends`, and one `RUN <package-manager> update` stands alone (should be combined with the matching `install` in one layer to avoid stale cache). All mechanical.

## The other notable false positive: 27 "logger-credential-leak" in exemplary OAuth code

After the K8s fixtures, the second-biggest FP class is 27 `logger-credential-leak` findings in `holmes/core/oauth_*.py`. Worth calling out because the code is the opposite of the problem:

```python
logger.info(
    "OAuth token stored (idp=%s, expires_in=%s, has_refresh=%s)",
    pending.oauth_config.token_url, token_data.get("expires_in"),
    "refresh_token" in token_data,        # ← a boolean, not the token
)
```

Every flagged line logs **metadata** — `token_url`, `client_id` (the public OAuth identifier, not the secret), `expires_in` (a number), `has_refresh` (a boolean). The actual tokens and `client_secret` are never logged. This is *exemplary* OAuth logging — they deliberately log `"refresh_token" in token_data` rather than the refresh token. Semgrep's `python-logger-credential-disclosure` rule fires on `logger.*` calls in proximity to variables named `token` / `secret` / `client_secret`; in an OAuth module every log line is near such a variable, so the rule fires 27 times on code that is doing exactly the right thing. Proximity, not data-flow.

## Patterns observed

**Two false-positive classes, 93% of the findings, and both are "the scanner doesn't know what this code is for."** The K8s fixtures are broken on purpose because the product diagnoses broken clusters; the OAuth log lines look dangerous because they are *in an OAuth module*. Neither is fixable by the scanner alone — both need the half-step of context that is the entire job of curation. After six prior scans establishing this pattern, HolmesGPT is the cleanest demonstration: the raw number is 2,143 and the honest number is closer to 60 real items, and the gap is entirely "what is this code".

**The real signal is small, recurring, and well-understood.** Strip the two FP classes and HolmesGPT's actual security posture is good: 17 workflow-injection patterns (mechanical fix, well-documented), an experimental subtree with drifted deps (scope decision, not a vuln), one main-tree dep bump, and an agent command-runner that is `shell=True` by necessity. For a CNCF Sandbox project this is roughly what you'd hope to find — nothing exploitable, a CI-hygiene cleanup, and a dependency-cadence decision about the `experimental/` tree.

**`--ignore-file` is now clearly a monorepo/large-repo necessity, not a nicety.** Third large scan ([after PraisonAI](mervinpraison-praisonai.html) and [Klavis](klavis-ai-klavis.html)) where path suppression was the difference between a triageable report and an unusable one. 2,143 → 144 is a 93% noise reduction from two glob patterns.

## Notes on the tool

- **A "fixture / test-data directory" heuristic** would help: when a finding's path matches `**/fixtures/**`, `**/testdata/**`, etc., AND the finding is an infrastructure-misconfig rule (Trivy K8s rules especially), it should default to `low` confidence. The K8s-fixture FP class has now appeared at scale and is mechanically detectable.
- **`logger-credential-leak` continues to over-fire** — flagged again here, 27 times, on exemplary code. Across openllmetry, Upsonic, airweave, and now HolmesGPT, this rule has produced ~zero true positives in the series. A confidence downgrade to `low` is overdue.
- **Cross-lockfile dependency dedup** — still the top backlog item.

## Disclosure timeline

- **2026-05-21** — Scan run at commit `46b0a93a6dfe`; `tests/**/fixtures/**` + `docs/**` suppressed; findings curated.
- **2026-05-21** — Public courtesy issue filed on HolmesGPT/holmesgpt. All findings trace to published CVEs or best-practice patterns; no private coordination required.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/HolmesGPT/holmesgpt" \
  --reports-dir reports/holmesgpt-holmesgpt \
  --min-severity medium \
  --ignore-file reports/holmesgpt-holmesgpt/.aipatchlabignore
```

The `.aipatchlabignore` used (`tests/**/fixtures/**`, `docs/**`) is in the report directory; without it the raw scan reports 2,143 findings, ~2,000 of them deliberately-broken Kubernetes test fixtures.

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
