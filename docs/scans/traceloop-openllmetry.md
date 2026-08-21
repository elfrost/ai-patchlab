---
layout: default
title: "traceloop/openllmetry: security scan"
description: "Security scan of traceloop/openllmetry: 33 findings, 25 false-positive secrets in test cassettes, 1 best-practice item filed with the maintainer"
date: 2026-05-14
---

# traceloop/openllmetry — security scan

**Repository:** [traceloop/openllmetry](https://github.com/traceloop/openllmetry) — 7.1k★, Apache-2.0, observability layer for LLM applications based on OpenTelemetry.
**Commit scanned:** approx `72fc45e` (HEAD of `main` at scan time)
**Scan date:** 2026-05-14
**Disclosure status:** One best-practice item (test cassette anonymization) filed as a public courtesy issue on the openllmetry repo. No findings required private coordination.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 26 |
| Medium | 7 |
| Low | 0 |
| Info | 0 (filtered) |

**33 total findings. After curation: 0 critical confirmed, ~2 best-practice improvements, ~31 false positives or by-design patterns.**

The headline this time: **25 of 26 high-severity findings come from a single source — Gitleaks matching strings inside test cassettes — and all 25 are either public-by-design identifiers, placeholders, or not actually credentials.** This scan is essentially a tour of how FP analysis on a "secrets" finding works.

## Top findings (curated)

### 1. 11× AWS access tokens detected in test cassettes

**Files:** `packages/opentelemetry-instrumentation-anthropic/tests/cassettes/test_bedrock_*/*.yaml`
**Tool:** Gitleaks (named rule `aws-access-token`, high confidence)
**Verdict:** **Real-format AWS access key IDs — but not a credential leak.**

The cassettes contain replayed HTTP requests to AWS Bedrock with an `Authorization: AWS4-HMAC-SHA256 Credential=AKIAQEMAC2MSQDTITCKK/...` header. That `AKIA…` value is an AWS **access key ID** — the public identifier portion of an AWS Sigv4 signature. The corresponding **secret access key** does not appear in the cassette, and the captured `Signature=...` value is only valid for that specific already-replayed request.

So the finding is real (it is in fact an AWS access key ID, and the format is real, not a placeholder), but the realistic impact is metadata exposure (which key was used to call which Bedrock model when) rather than credential compromise. Best practice is still to anonymize these via VCR's `filter_headers` / `before_record_request` before committing.

### 2. 8× JWT tokens detected in test cassettes

**Files:** `packages/opentelemetry-instrumentation-watsonx/tests/{traces,metrics}/cassettes/test_generate*/...yaml`
**Tool:** Gitleaks (named rule `jwt`, high confidence)
**Verdict:** **False positive — clearly test placeholders.**

Decoding the second segment of any of these JWTs yields:
```json
{"name":"none","sub":"noone@ibm.com","iam_id":"IBMid-100000PW00","account":{"bss":"abc123"},"iat":1708593737,"exp":2023953737}
```

`sub: noone@ibm.com`, `account.bss: abc123` — these are obvious placeholder claims. The JWT format is real (the rule wouldn't have matched otherwise) but the contents have been carefully zeroed.

### 3. 6× "generic-api-key" matches in test cassettes (incl. PostHog public key)

**Files:** `packages/opentelemetry-instrumentation-haystack/tests/cassettes/test_simple_pipeline/test_haystack.yaml`, watsonx cassettes, plus one in `sample-app/data/`
**Tool:** Gitleaks (named rule `generic-api-key`, high confidence)
**Verdict:** **Mostly public-by-design** (PostHog `phc_…` write-only event-ingestion keys) or placeholders.

The PostHog `phc_` prefix denotes a **public, write-only project API key** that PostHog explicitly designs to be shipped to clients (browsers, telemetry SDKs). It identifies the project for event ingestion and has no read or admin scope. Leaking one of these to a repo is the *intended* deployment surface for the key — not a credential exposure.

### 4. 2× `logger-credential-leak` in `anthropic/streaming.py`

**Files:** `packages/opentelemetry-instrumentation-anthropic/opentelemetry/instrumentation/anthropic/streaming.py:293,437`
**Tool:** Semgrep (`python-logger-credential-disclosure`, medium confidence)
**Verdict:** **False positive — "token" here means LLM token count, not auth token.**

The flagged code is `logger.warning("Failed to set token usage, error: %s", str(e))`. The Semgrep rule heuristically matches on logger calls in proximity to variables named `*token*`. In the instrumentation context, "token" means **prompt/completion token counts for billing telemetry**, not authentication tokens. No credentials are involved.

### 5. `prompts/client.py:44` — `Environment()` without autoescape

**File:** `packages/traceloop-sdk/traceloop/sdk/prompts/client.py:44`
**Tool:** Semgrep (`direct-use-of-jinja2`, medium confidence)
**Verdict:** **By design — output is rendered into LLM prompts, not HTML.**

The `Environment()` is used by the prompt registry to render templated LLM prompts. `autoescape=True` would HTML-escape special characters (`<`, `>`, `&`, etc.) — useful when rendering to HTML, harmful when rendering to an LLM prompt where those characters are part of the expected output. The current code is correct for its use case. A one-line code comment ("autoescape disabled because output goes to an LLM, not HTML") would help reviewers and scanners alike.

## Patterns observed

**The "scanner found 25 secrets, panic!" → "actually zero credentials" gap is exactly what makes security tooling without curation worse than useless.** This scan is a textbook case: every Gitleaks match has a real-looking shape, every one fires high-confidence, and exactly zero of them are credentials a defender should rotate. A consultant who copy-pastes the scanner output and tells Traceloop "you have 25 leaked secrets, please rotate immediately" is wasting everyone's time and burning trust. A consultant who reads each match in context and reports "you have one cassette-anonymization best-practice item plus 24 false positives" is doing the actual job.

**Test cassettes are a recurring blind spot in static secret scanning.** VCR-style recorded HTTP fixtures contain whatever was on the wire — including auth headers, JWTs, public API keys. They are also the most common source of "secret detected" findings on Python projects with proper integration tests. The fix is consistent: configure VCR to scrub via `filter_headers`, `filter_query_parameters`, and `before_record_response`. Even if every real test value is a placeholder today, an unfiltered cassette is one rotation away from accidentally landing a real secret on the next re-record. This is the single best-practice item worth flagging in this scan.

**Cassettes preserve metadata.** Even with no credential leak, cassettes leak operational data: which AWS account, which model, which day, which API surface. For an observability SDK that ships to enterprises, anonymization is also a privacy-of-recording-engineers concern, not just a credentials concern.

**The application code is defensive.** The two findings in actual SDK code (`logger-credential-leak`, `direct-use-of-jinja2`) are both context-dependent false positives — exactly the kind of finding where a confidence value of `medium` (which AI PatchLab assigned to all Semgrep matches per its rules engine) is appropriate. The three `non-literal-import` matches in instrumentation packages are textbook plugin discovery and likewise expected.

## Notes on the tool

Recurring with [the gptme scan](gptme-gptme.html):

- **No deduplication across files.** 11 separate AWS-token findings on cassettes in the same directory tree would read much better collapsed into one entry.
- **No way to suppress at the path level.** A `--exclude packages/*/tests/cassettes/**` flag (or a project-level `.aipatchlabignore`) would have removed 25 of the 33 findings on this scan and made the signal-to-noise ratio dramatically better.
- **No file-context awareness.** Gitleaks fires the same `aws-access-token` rule with the same `confidence: high` on a YAML cassette of a recorded request as on a `.env` file — but those are very different threats. A "rule + file-class" weighting (`secrets in test cassettes get medium, secrets in source-of-truth config get high`) would push real signal to the top.

These all now live in the project backlog.

## Disclosure timeline

- **2026-05-14** — Scan run, top findings curated.
- **2026-05-14** — Public courtesy issue filed on [traceloop/openllmetry](https://github.com/traceloop/openllmetry/issues) recommending cassette-anonymization (VCR filter configuration). One additional best-practice note (a comment on the SDK's `jinja2.Environment()` use) is mentioned inline in the issue.

No findings rose to the level of critical vulnerability requiring private coordination before publication.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/traceloop/openllmetry" \
  --reports-dir reports/traceloop-openllmetry \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
