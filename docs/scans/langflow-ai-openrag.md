---
layout: default
title: "langflow-ai/openrag: security scan"
description: "Security scan of langflow-ai/openrag: 213 findings at medium+, one High privately disclosed (GHSA-xv8v-6c28-v78p, detail withheld), and a default-secret token boundary that no scanner rule can see."
date: 2026-08-25
---

# langflow-ai/openrag — security scan

**Repository:** [langflow-ai/openrag](https://github.com/langflow-ai/openrag) — 4.5k★, Apache-2.0, a single-package Retrieval-Augmented Generation platform built on OpenSearch + Langflow, with commercial backing (langflow-ai / DataStax).
**Commit scanned:** `0d35b2cd7721` (HEAD of `master` at scan time)
**Scan date:** 2026-08-25
**Disclosure status:** **Private.** One High-severity finding was reported through the project's Private Vulnerability Reporting channel (**GHSA-xv8v-6c28-v78p**, state `triage`). Per OpenRAG's SECURITY.md — which asks that vulnerabilities not be disclosed publicly until assessed, resolved, and affected users notified — the technical detail is **withheld from this post**. Only the finding *class* appears below. This page will be expanded once the maintainers resolve and notify, or after a 90-day window.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 1 |
| High | 43 |
| Medium | 166 |
| Low | 0 |
| Info | 3 (filtered) |

**213 findings at `--min-severity medium`. After curation: the scanner output is almost entirely one recurring best-practice class plus well-understood false positives — and the one finding that actually matters is a composite the scanners cannot see.** OpenRAG is a well-built, security-conscious codebase: it ships a `.secrets.baseline`, a real SECURITY.md, DLS-scoped OpenSearch roles, CORS locked to `localhost:3000` with `allow_credentials=False`, and a Kubernetes operator that auto-generates per-deployment secrets. The interesting question here is not "what did the scanner flag" — it is "what did every scanner miss."

## The finding the scanners missed (class only, detail withheld)

**Class:** use of a hard-coded / shipped-default cryptographic secret on a token-signing boundary (CWE-321 / CWE-798), reachable in the default self-hosted deployment.

This is the recurring lesson of the series: **a boundary that composes two individually-reasonable decisions in two different files cannot be seen by any single static rule.** One file makes a sensible-looking fallback choice; another file, elsewhere, hardens a *different* token path; a deployment artifact ties the knot. Each half reads as fine in isolation. The scanners flagged neither half, because neither half is wrong on its own — the defect lives in the seam between them, and only a deployment-default read across the code + the compose file + the frontend proxy surfaces it. The detail is with the maintainers privately.

The differential that confirmed it was run offline against the project's *own* token-validation logic (no live instance needed) — the standard "run the exploit primitive as a differential" discipline — and a concrete fix, written against OpenRAG's own key-generation architecture, was included in the private report.

## What the scanner actually flagged — and why almost none of it is a defect

### 121× GitHub Actions mutable action tags (best-practice, the recurring class)

`actions/checkout@v4`, `setup-python@v5`, `cache@v4` and friends referenced by mutable tag rather than pinned SHA. Real supply-chain best-practice — the single most common class across the whole scan series — but low-priority hardening, not an exploitable defect. Worth one dedicated pinning pass (the repo's own `scorecard-analysis.yml` already demonstrates the SHA-pinned pattern).

### 15× "secret detected" — all false positives (credit the defense)

Every gitleaks hit lands in a place the project already manages:

| Location | Count | What it actually is |
| --- | ---: | --- |
| `.secrets.baseline` | 4 | the detect-secrets baseline file itself — the defense, not a leak |
| `.env.example` | 4 | empty placeholder slots (`KEY=` / `SECRET=` with no value) |
| `Makefile` | 5 | `curl -u admin:$OPENSEARCH_PASSWORD` — a shell variable, not a literal |
| `docs/docusaurus.config.js` | 1 | a documentation config value |
| `tests/…/test_azure_blob_connector.py` | 1 | a test fixture |

OpenRAG ships a `.secrets.baseline`; honouring it is the correct behaviour and zero of these are live credentials.

### 1× "critical" Kubernetes RBAC — by design

Trivy's highest-severity hit is `kubernetes/operator/config/rbac/role.yaml` granting `secrets` management. That is the OpenRAG *operator's own* role, and it manages secrets on purpose — it is the component that generates the per-deployment `JWT_SIGNING_KEY`. Flagging an operator for having the permission it exists to use is exactly backwards.

### 10× logger-credential-leak — the series' most reliable false positive

Semgrep's `python-logger-credential-disclosure` rule again fires on log lines that sit near variables named `token`/`secret`, on code that logs metadata rather than secrets. Across this series that rule has produced essentially zero true positives; a confidence downgrade remains overdue.

### K8s misconfig rules (root, seccomp, read-only FS) on helm/operator manifests

Standard container-hardening defaults missing on the operator's example manifests. Best-practice, not defects in the shipped product.

## Patterns observed

OpenRAG is the kind of target where the scanner's headline number is the *least* informative thing about it. 213 findings sounds alarming; the real content is one privately-disclosed composite and a long tail of best-practice pinning. The codebase is visibly security-aware — it went out of its way to auto-generate one class of signing key per deployment — which is precisely what makes the seam interesting: the hardening was applied to one token path and not to its sibling, and a raw scanner count would never surface that asymmetry. The single most valuable read on this repo was diffing `securityconfig/` against `cloud_securityconfig/` (two near-identical OpenSearch security configs that differ in exactly the fields that matter) and then tracing a token from where it is minted to where it is validated — neither of which any rule performs.

The maintainers do a lot right: a real disclosure policy with a 5-business-day ack SLA, DLS-scoped read roles keyed on `owner`/`allowed_users`, non-wildcard CORS with credentials disabled, and a `.secrets.baseline` that suppresses exactly the noise above. That is a higher baseline than most of the series.

## Notes on the tool

- **The composite-finding blind spot is structural, not a rule gap.** No `semgrep` rule can flag "a default secret in file A signs a token validated in file C, reachable through proxy B" — the three facts live in three files and each is individually benign. This is the fourth or fifth time the series' one real finding was invisible to every scanner. The backlog item is not "write a rule" but "a deployment-default read (code + compose + proxy) is a required manual pass, not an optional one."
- **`logger-credential-leak` fired again on exemplary code** (10×). Its running true-positive rate in this series is ~zero. Downgrade to `low` is overdue.
- **Trivy has no notion of "this RBAC role belongs to an operator."** The one "critical" was a by-design permission. A "manifest under `**/operator/**` / `**/rbac/**`" awareness would retire it.
- **Credit-the-defense continues to pay:** honouring `.secrets.baseline` collapsed the entire secrets cluster to zero true positives in one step.

## Disclosure timeline

- **2026-08-25** — Scan run at commit `0d35b2cd7721`; findings curated; the one real finding verified offline against OpenRAG's own token-validation logic.
- **2026-08-25** — Reported privately via GitHub Private Vulnerability Reporting → **GHSA-xv8v-6c28-v78p** (state `triage`), with a concrete fix written against the repo's own key-generation architecture. Public detail withheld per OpenRAG's SECURITY.md.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/langflow-ai/openrag" \
  --reports-dir reports/langflow-ai-openrag \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) install separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme). The scanner output reproduces the 213 findings above; the one finding that matters is a manual deployment-default read, not a scanner hit, and its detail stays with the maintainers until they resolve and notify.
