---
layout: default
title: "SwanHubX/SwanLab: security scan"
date: 2026-06-28
---

# SwanHubX/SwanLab - security scan

**Repository:** [SwanHubX/SwanLab](https://github.com/SwanHubX/SwanLab)
**Commit scanned:** `2ed6af76e57da90a2a1ad417d69c63efd361224d`
**Scan date:** 2026-06-28
**Disclosure status:** public — post-only (strict-norm: real SECURITY.md + commercial backing; no upstream issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 19 |
| Medium | 13 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 32 (0 code-level; all are a dependency tail + 2 test-fixture FPs)

SwanLab is an open-source, self-hostable AI training tracker and visualization
tool — a W&B-style experiment dashboard with a Python SDK, image/3D/audio media
logging, webhooks, and a private-deployment edition. It's a 4k-star, Apache,
commercially-backed project (swanlab.cn cloud) with a real security policy.

This is the **10th clean scan** in the series, and a slightly unusual one: the
interesting result is the *absence* of code-level findings. Semgrep scanned 361
files under `swanlab/` and returned **zero** results — no SQL injection, no
`shell=True`, no `eval`, no SSRF pattern, nothing — on a web platform with auth,
file upload, and webhooks. The entire finding list is a dependency refresh (no
Dependabot is wired) plus two test-fixture secret false positives.

## Top findings

### 1. Code is clean — semgrep 0/361, gitleaks 2/2 false positives

- **Tool:** semgrep (0 results, 0 errors across 361 `swanlab/` source files) + gitleaks
- **Confidence:** high
- **Why it matters:** For a self-hosted dashboard that ingests user data, the
  scanner's usual web-app rules (injection, traversal, SSRF, unsafe
  deserialization) found nothing. The two gitleaks hits are both in
  `tests/unit/.../test_pkg_builder.py:44,49` — test fixtures, not real
  credentials. The codebase runs `pre-commit` and the hygiene shows: this is a
  genuinely clean code result, not a 0-byte scanner failure (the semgrep report
  is a healthy 56 KB with `errors: 0`).

### 2. The one reachable dependency item: pillow image-parsing CVEs

- **File:** `uv.lock` (`pillow` 11.3.0 → 12.x; CVE-2026-25990 OOB write via PSD, CVE-2026-40192 / -42311, plus three medium decompression-bomb / FITS issues)
- **Tool:** trivy
- **Confidence:** reachable on the image-logging path, version-match
- **Why it matters:** SwanLab's media logging (`swanlab.Image`) decodes
  user-supplied images via Pillow — there are ~50 `PIL` import/usage sites. An
  out-of-bounds-write on a crafted image is the kind of dependency CVE that a
  media-ingesting platform should treat as reachable, not transitive: a user who
  can upload an image to an experiment can hand a malicious file to the decoder.
- **Caveat:** `pillow` is an *optional* dependency (`[project.optional-dependencies]`),
  so only deployments that enable image logging pull it. Still, that's the
  advertised feature, so in practice it's installed.
- **Recommendation:** Bump `pillow` to 12.2.0+. This is the one dep in the tail
  where "is it reachable here?" answers yes.

### 3. The rest of the tail is transitive version-match

- **File:** `uv.lock`
- **Tool:** trivy
- **Confidence:** high on version-match, low on direct reachability
- **Why it matters / why it doesn't:** `starlette` (5 CVEs incl. SSRF/NTLM via
  UNC), `ujson` (3 CVEs), `urllib3` (1.26.20 is notably old — 4 CVEs), `orjson`,
  `requests`, `idna`, `python-dotenv`, `pydantic-settings`, `pygments`. The
  reachability check is decisive here: `starlette`, `ujson`, and `fastapi` have
  **zero direct import sites** in the repo — the heavy multi-user server backend
  isn't in this open-source SDK/dashboard repo, so those server-framework CVEs
  are transitive, not a starlette server this code stands up. The rest are
  DoS/decompression-class transitives behind `requests`/`huggingface-hub`-style
  call paths.
- **Recommendation:** A lockfile refresh clears most of these at once. The
  `urllib3` 1.26.20 pin is the oldest and worth pulling forward.

## Patterns observed

**Clean code, drifting lockfile, no Dependabot.** SwanLab inverts the usual
shape: most scans in this series have a clean-ish dependency story and a few
code-level patterns to triage. Here it's the opposite — the code is spotless and
the only signal is that `uv.lock` carries 30 advisories with no
`.github/dependabot.yml` to keep it current. That's a process gap, not a
vulnerability, and on a commercially-backed project with a security team it's
the kind of thing they very likely already track on the cloud side.

**Reachability is what separates the one real item from the noise.** The
`starlette` SSRF and `ujson` parser CVEs *sound* server-reachable on a dashboard
platform, but a 30-second import check shows neither framework is directly used
in this repo — they're transitive. The `pillow` CVEs sound like generic
image-library noise, but SwanLab's whole media-logging feature funnels
user-supplied images through Pillow, so that's the row that actually matters.
Same lockfile, opposite verdicts, decided by "is the affected surface reached
from this code."

**Strict-norm handling.** SwanLab ships a real `SECURITY.md` with a dedicated
maintainer-alias triage address, and is backed by a commercial cloud. That puts
it firmly in post-only territory: no grouped public "review" issue. The dep tail
is entirely public CVEs with mechanical fixes (bump + wire Dependabot), so there
was nothing here that warranted a private security report either — the honest,
proportionate action is this write-up.

## Notes on the tool

- **Optional vs. core dependency tier.** AI PatchLab reported `pillow` at the
  same severity as the transitive tail, but `pillow` is the one with a
  feature-reachable call path *and* it's an optional extra — two annotations that
  change how a maintainer should prioritize it. Tagging deps as
  core / optional-extra / transitive (and cross-referencing import sites) would
  put the one reachable row at the top. Same backlog item the Kiln scan raised.
- **A 0-result semgrep run should be stated as coverage, not silence.** The
  report shows "0 high from semgrep" but the *useful* fact is "361 source files
  scanned, 0 results, 0 errors." After the Clawith 0-byte incident, a clean
  semgrep run should surface its scanned-file count so a reader can tell a real
  clean from a silent skip. Backlog item.
- **`tests/` secret hits stayed in the high bucket.** Both gitleaks findings are
  test fixtures; the candidate-FP flagging for `tests/` should have demoted them
  out of the headline severity.

## Disclosure timeline

- 2026-06-28 — scan run
- 2026-06-28 — public post (this page); post-only, no upstream issue filed

This is a post-only clean-scan write-up. The code scanned clean, the two secret
hits are test fixtures, and the dependency tail is public CVEs with mechanical
fixes — mostly transitive, one (pillow) feature-reachable. On a strict-norm,
commercially-backed project with its own security channel, the proportionate
action is to document rather than file.

## Reproduce

```bash
git clone https://github.com/SwanHubX/SwanLab /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/swanhubx-swanlab \
  --min-severity medium --ignore-samples
```
