---
layout: default
title: "guardrails-ai/guardrails: security scan"
description: "Security scan of guardrails-ai/guardrails: 17 findings, first dep-scan hits in the series (7 known CVEs on a pinned litellm upper bound) + 2× duplicated"
date: 2026-05-19
---

# guardrails-ai/guardrails — security scan

**Repository:** [guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails) — 6.9k★, Apache-2.0, "adding guardrails to large language models" — schema-driven LLM output validation and safety library.
**Commit scanned:** `28d74af02215` (HEAD of `main` at scan time)
**Scan date:** 2026-05-19
**Disclosure status:** Public courtesy issue filed on the guardrails repo with the publishable items below. No findings required private coordination.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 13 |
| Medium | 4 |
| Low | 0 |
| Info | 0 (filtered) |

**17 total findings — by far the smallest scan in the series. After curation: 3 distinct real items worth flagging (one with substantial impact: 7 known-CVE entries against a pinned `litellm` upper-bound) and ~4 false positives.**

This is the first scan in the series where **dependency-scan (pip-audit)** produces findings — every prior scan came back clean on the dep-vulnerability side. It also includes our first sustained pass at a *security-adjacent tool*'s own code (after [msoedov/agentic_security](msoedov-agentic-security.html)) — meta-relevant since Guardrails AI ships a safety layer for LLM apps.

## Top findings (curated)

### 1. 7× known CVE/GHSA advisories against the pinned `litellm` upper bound (`<1.82.6`)

**Tool:** pip-audit via dependency-scan (high confidence — named advisories)
**Verdict:** **Real — pinned upper bound excludes the patched versions.**

`pyproject.toml` pins:

```toml
"litellm>=1.37.14,<1.82.6",
```

pip-audit surfaces seven published advisories on litellm versions in that range:

- CVE-2026-35029
- CVE-2026-35030
- GHSA-69x8-hrgq-fjj8
- CVE-2026-42203
- CVE-2026-42208
- CVE-2026-42271
- CVE-2026-40217

The upper bound (`<1.82.6`) explicitly excludes the patched versions, so any environment installing Guardrails today resolves to a litellm release with all seven advisories applicable. The fix is mechanical: bump the upper bound past `1.82.6` (or remove it). Whether the bound exists because of a known incompatibility with a newer litellm or because nobody has revisited it is worth checking; if the latter, this is a one-line change.

This is the first dependency-scan finding in the series and a clean example of why the dep layer matters: scanning the source code alone would have missed all seven advisories. Recommended path: upgrade the pin, then re-run `pip-audit -r requirements.txt` (or the equivalent against the resolved environment) and re-scan.

### 2. 2× `jwt.decode(token, options={"verify_signature": False, ...})`

**Files:** `guardrails/cli/server/hub_client.py:97`, `guardrails/hub_token/token.py:46`
**Tool:** Semgrep (`unverified-jwt-decode`, medium confidence)
**Verdict:** **Subtle — currently safe but a known-footgun pattern in a security-adjacent codebase.**

Both files contain the *same* function, copy-pasted across modules:

```python
def get_jwt_token(rc: RC) -> Optional[str]:
    token = rc.token

    # check for jwt expiration
    if token:
        try:
            jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
        except ExpiredSignatureError:
            raise ExpiredTokenError(TOKEN_EXPIRED_MESSAGE)
        except DecodeError:
            raise InvalidTokenError(TOKEN_INVALID_MESSAGE)
    return token
```

The intent is clear from the comment: *"check for jwt expiration"* — the function reads the token locally to fail fast on expired credentials before sending the (still server-validated) token to the Guardrails Hub backend. So **the function is safe today**: no authorization decision is made on the unverified-signature payload.

But three things make this worth flagging:

1. **The same code lives in two places.** The function is duplicated across `cli/server/hub_client.py` and `hub_token/token.py`, line-for-line. Whatever defensive intent lives in one file has to be maintained in two. Best practice: extract one shared `client_check_token_expiry(token)` utility.
2. **`jwt.decode(..., verify_signature=False)` is the canonical footgun shape.** Any static scanner will flag it on every scan, every contributor's first reading of the file will pause on it, and any future maintainer who adds a `payload = jwt.decode(...)` line for any other purpose has already crossed the safety boundary. The safer pattern is to manually base64-decode the second JWT segment and inspect the `exp` claim directly — no `jwt.decode` call, no `verify_signature=False` to maintain:
   ```python
   import base64, json, time
   header, payload_b64, _signature = token.split('.')
   payload = json.loads(base64.urlsafe_b64decode(payload_b64 + '==='))
   if payload.get('exp', 0) < time.time():
       raise ExpiredTokenError(TOKEN_EXPIRED_MESSAGE)
   ```
3. **Guardrails is a security-adjacent project.** Users come for the safety story; an `unverified-jwt-decode` flagged on their own client library is awkward optics even when it's defensible. Worth refactoring on aesthetic grounds alone.

None of this is an active vulnerability. It is a code-review observation in a place where the optics of *appearing* to bypass signature verification matter.

### 3. 4× workflow `${{ inputs.* }}` interpolation in `.github/actions/validator_pypi_publish/action.yml`

**Tool:** Semgrep (`run-shell-injection`, medium confidence)
**Verdict:** **Real best-practice — same class as prior scans, *plus a secret is interpolated*.**

```yaml
- name: Create .pypirc
  shell: bash
  run: |
    ...
    echo "repository = ${{ inputs.pypi_repository_url }}" >> ~/.pypirc
    echo "username = __token__" >> ~/.pypirc
    echo "password = ${{ inputs.guardrails_token }}" >> ~/.pypirc
```

Three of the four sites are the standard "input interpolated into shell at workflow-parse time" pattern documented on [gptme](gptme-gptme.html), [PraisonAI](mervinpraison-praisonai.html), and [airweave](airweave-ai-airweave.html). The fourth (the `password = ${{ inputs.guardrails_token }}` line) is **interpolating a secret value directly into an echo command** — which compounds the class:

- Shell-quoting protection is unavailable at the parse-time interpolation layer (same as the other instances).
- The shell `echo` line writes the secret to `~/.pypirc` on the runner. If anything in this step ever leaks stdout/stderr (a verbose `set -x`, a debug log, a different action being chained downstream), the secret leaks too.
- GitHub Actions masks secrets in normal log output, but the masking is content-based — if the secret undergoes any transformation (`tr`, `sed`, base64), it's no longer masked.

The standard fix is to pipe the secret through `env:` and reference it from the shell environment, never inline-interpolating into a `run:` script:

```yaml
- name: Create .pypirc
  shell: bash
  env:
    PYPI_URL: ${{ inputs.pypi_repository_url }}
    GUARDRAILS_TOKEN: ${{ inputs.guardrails_token }}
  run: |
    {
      echo "[distutils]"
      echo "index-servers ="
      echo "    private-repository"
      echo ""
      echo "[private-repository]"
      echo "repository = $PYPI_URL"
      echo "username = __token__"
      echo "password = $GUARDRAILS_TOKEN"
    } > ~/.pypirc
```

(Other sites in the same action.yml — `:62`, `:67`, `:77` — have the simpler "input string in shell command" shape and use the same fix.)

### 4. 4× `non-literal-import` in the validator hub

| File | Verdict |
|---|---|
| `guardrails/hub/__init__.py:43` | **By design** — the Guardrails Hub discovers validators dynamically by name |
| `guardrails/hub/validator_package_service.py:99, 246` | **By design** — same pattern, deeper in the package-service implementation |
| `guardrails/validator_base.py:575` | **By design** — base validator dynamic resolution |

Plugin/discovery imports. Standard FP class for this rule on plugin-architecture codebases — same observation we made on [PraisonAI](mervinpraison-praisonai.html) and [Upsonic](upsonic-upsonic.html).

## Patterns observed

**The dep-scan layer just earned its keep.** Five prior scans across this series produced zero pip-audit findings. Guardrails is the first project whose pinned-but-narrowed dependency range opens a sustained CVE window — and crucially, the seven advisories were entirely invisible to the SAST layer (Semgrep) because the *source code is fine*. Without the dep-scan layer in AI PatchLab, this entire class of finding would have escaped curation. The takeaway isn't that Guardrails is uniquely vulnerable — pinned upper bounds on fast-moving deps are common — it's that the dep-scan layer is non-optional for any reputable security scan and that the pattern of "scan reports zero dep findings → looks clean" is a structural blind spot until you've validated which versions resolve in the lockfile.

**Smallest curated scan, highest signal density.** 17 raw findings on a 43 MB Python codebase, ~4 FP, ~13 worth comment, and a single-line dependency upgrade clearing the largest category. Guardrails' core codebase is unusually tight relative to its scope — the `non-literal-import` finds in the hub validator system are essentially the only real false-positive shape, and they're all the same plugin-discovery pattern.

**The duplicated-`get_jwt_token` function is exactly the maintenance smell static scanners are supposed to surface.** Two files, same lines, same trust-model assumption baked into both. The `unverified-jwt-decode` rule doesn't know they're identical — it fires twice, gets a "FP" tag in 90% of triage workflows, and the duplication continues to outlive the function's intent. The refactor (one shared utility, clear comment, base64-only path) makes the static scanner happy AND removes the future-regression risk.

**Confirmation that the workflow-shell-interpolation class is universal.** This is now the **fourth consecutive Python AI project** with the same `${{ inputs.* }}` / `${{ github.event.* }}` issue, including the post-scan automated fix path in two of them ([gptme PR #2399](https://github.com/gptme/gptme/pull/2399), [PraisonAI PR #1677](https://github.com/MervinPraison/PraisonAI/pull/1677)). The class is no longer "discovered each time"; it's an industry-wide expectation that we can lead with rather than explain from first principles each post.

## Notes on the tool

Recurring backlog items confirmed on this scan:

- **The dep-scan output's `file` field shows `.` rather than `requirements.txt` / `pyproject.toml`.** Worth surfacing which file produced the resolution — useful when a project ships both for different deployment paths.
- **Cross-rule deduplication is still on the backlog.** The two `unverified-jwt-decode` sites are the same code duplicated; a "same-AST-shape" detector could collapse them into one finding with two `file:line` references.

## Disclosure timeline

- **2026-05-19** — Scan run at commit `28d74af02215`, findings curated.
- **2026-05-19** — Public courtesy issue filed on guardrails-ai/guardrails with the three publishable items. No finding rose to the level requiring private coordination.
- **2026-06-19** — **Item 1 fixed.** `cac65a45` bumped litellm to 1.89.2 and `42d7ab44` adopted the published `guardrails-api` 0.4.3 ("resolves litellm vulns"), following [#1484](https://github.com/guardrails-ai/guardrails/pull/1484). The pin now reads `litellm>=1.82.5,<2.0.0` — the upper bound no longer excludes the patched releases.
- **2026-07-27** — **Item 3 fixed.** [#1585](https://github.com/guardrails-ai/guardrails/pull/1585) routed `package_directory` and `validator_id` through `env:` and quoted them as shell variables, closing the template-injection path. The maintainers' own PR describes it as CWE-78 / CWE-74 and rates it critical.
- **2026-08-17** — **Item 2 still open.** Both `get_jwt_token` copies remain byte-identical at `hub_client.py:97` and `token.py:46`. A stale bot moved to auto-close the issue; [commented](https://github.com/guardrails-ai/guardrails/issues/1485#issuecomment-5316413918) with the state above so the close would not read as "all three addressed". Two community PRs ([#1494](https://github.com/guardrails-ai/guardrails/pull/1494), [#1451](https://github.com/guardrails-ai/guardrails/pull/1451)) remain open.

**Outcome: partial (2 of 3).** Both fixed items were resolved by maintainer work on their own schedule rather than by a PR from this series — the filing's contribution was naming them, not fixing them. The third is the one this scan wrote the most about, and it is the one still standing.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/guardrails-ai/guardrails" \
  --reports-dir reports/guardrails-ai-guardrails \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
