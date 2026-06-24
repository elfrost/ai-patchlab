---
layout: default
title: "maziyarpanahi/openmed: security scan"
date: 2026-06-24
---

# maziyarpanahi/openmed - security scan

**Repository:** [maziyarpanahi/openmed](https://github.com/maziyarpanahi/openmed)
**Commit scanned:** `f495e4e97ae8e92a3689941de8d0c7bbb825f704`
**Scan date:** 2026-06-24
**Disclosure status:** public — clean scan, post-only (no upstream issue filed)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 23 |
| Medium | 21 |
| Low | 0 (filtered at `--min-severity medium`) |
| Info | 0 |

**Total findings:** 44 (0 real, reachable, undefended after curation)

OpenMed is a local-first healthcare AI library: clinical NER and HIPAA PII
de-identification that runs 100% on-device, no cloud, no patient data leaving
the network. It loads from a catalogue of 1,000+ HuggingFace medical models.
That model-loading surface is exactly where a security review of this project
should focus — and it is exactly where the maintainer got there first.

This is the **9th clean scan** in the series. The 44 findings split into one
genuinely scary *class* (arbitrary code execution while loading a model) that
is already defended down to a named-CVE regression test, a 24-CVE dependency
tail that is real but transitive and reachability-gated (and already wired to
Dependabot), and the usual lint noise.

## Top findings

### 1. `transformers` arbitrary code execution via malicious model — already defended

- **File:** `uv.lock` (`transformers` 4.57.1, CVE-2026-1839) → surfaces in `openmed/core/pii.py`, `openmed/torch/privacy_filter.py`, `openmed/core/backends.py`
- **Tool:** trivy (dep) + reachability review
- **Confidence:** high that it is **by-design defended**
- **Why it matters:** For a tool that loads arbitrary HuggingFace repos to
  de-identify patient data, the worst case is `trust_remote_code=True` against
  an attacker-named model — Transformers will then import and execute Python
  shipped in the model repo's `auto_map`. This is a real RCE shape, and it is
  *the* finding to chase on this codebase.
- **Recommendation:** None. The maintainer already shipped a three-layer
  defense (see below). The remaining advice — bump `transformers` past the
  fixed line when a stable release exists (the CVE is only patched in a
  `5.0.0rc` at scan time) — is on Dependabot's plate.

The defense is worth quoting because it is textbook. `trust_remote_code`
defaults to `False` everywhere. The privacy-filter loader gates it behind an
allowlist (`is_trusted_for_remote_code`) and the pipeline constructor
*refuses* to pass `trust_remote_code=True` for any model outside the
first-party `openai/privacy-filter` / `OpenMed/privacy-filter-*` prefix set:

```python
if trust_remote_code and not is_trusted_for_remote_code(model_name):
    raise ValueError(
        f"Refusing to load {model_name!r} with trust_remote_code=True: "
        "model is not in the OpenMed trusted-remote-code allowlist."
    )
```

And there is a dedicated regression test — `tests/unit/test_privacy_filter_security.py`,
headed with **CVE-2026-47117** — that asserts the substring-bypass class is
closed: `attacker/foo-privacy-filter-bar`, `evil-org/my-privacy-filter`, and
`username/privacy-filter` are all rejected by the identifier matcher, while the
legitimate `openai/privacy-filter` and case-variant `OpenAI/Privacy-Filter`
pass. The scanner can flag the dependency CVE; it cannot see that the exact
attack it implies was already modelled, fixed, and pinned with a test.

### 2. GitHub Actions shell-injection in `convert-models.yml` (6 sites) — privileged-trigger only

- **File:** `.github/workflows/convert-models.yml:47,85,120,192,224,249`
- **Tool:** semgrep (`run-shell-injection`)
- **Confidence:** real pattern, low risk
- **Why it matters:** The workflow interpolates `${{ github.event.inputs.model_id }}`,
  `inputs.quantize`, and `inputs.formats` directly into `run:` shell blocks.
  Under a `pull_request_target` or `issue_comment` trigger this would be a
  classic attacker-controlled injection. Here the trigger is
  `workflow_dispatch` **only** — the inputs come from someone who already has
  permission to run the workflow from the Actions UI. An actor who can inject
  here can already edit the workflow.
- **Recommendation:** Defense-in-depth: pass the inputs through an `env:` block
  and reference `"$MODEL_ID"` inside the script rather than interpolating
  `${{ }}` into the shell line. Cheap hardening, not an exploitable hole.

### 3. Dependency tail: 24 lockfile CVEs, real but reachability-gated

- **File:** `uv.lock`
- **Tool:** trivy
- **Confidence:** high on version-match, low on reachable-and-undefended
- **Why it matters / why it doesn't:** The headline "23 high" is almost
  entirely transitive and gated on a surface this tool doesn't expose by
  default:
  - `starlette` (5 CVEs incl. SSRF/NTLM via UNC paths, Host-header bypass) —
    arrives via the **optional** `fastapi`/`uvicorn` `service` extra. The
    core library and the on-device path never start an ASGI server.
  - `gitpython` 3.1.45 (5 CVEs, incl. the `clone_from`-kwargs command-exec
    CVE-2026-42215) — transitive, and the kwargs-injection CVE requires the
    *application* to forward attacker-controlled kwargs into GitPython, which
    OpenMed does not do.
  - `urllib3` 2.5.0 (4 decompression-bomb / cross-origin-redirect CVEs) —
    transitive via `requests`/`huggingface-hub`; the model-download peer is
    HuggingFace, a trusted origin.
  - `protobuf`, `idna`, `requests`, `python-dotenv`, `pytest`,
    `pymdown-extensions` — transitive, dev/docs/test-tooling, or DoS-class.
- **Recommendation:** None to file. **Dependabot is already configured**
  (`.github/dependabot.yml`), so this drift is on a lane that resolves itself.

### 4. Dockerfile runs as root — scoped to the opt-in service container

- **File:** `Dockerfile`
- **Tool:** trivy (misconfiguration, HIGH)
- **Confidence:** real hardening item
- **Why it matters:** The image installs `.[hf,service]` and runs
  `uvicorn openmed.service.app:app` as root on port 8080. This is the optional
  server deployment, not the local-first library use that the README leads
  with, so blast radius is limited to whoever opts into the container.
- **Recommendation:** Add a non-root `USER` before `CMD`. Standard container
  hardening.

## Patterns observed

**The review converges on the model-loading path, and the maintainer was
already there.** Almost every interesting security project in this series has
one surface that *is* the threat model — for an MCP server it's the credential
keychain, for a multi-tenant harness it's the tenant boundary. For a tool
whose entire job is loading 1,000+ third-party models to touch PHI, it's
`trust_remote_code`. OpenMed doesn't just default it off; it ships an
allowlist, a constructor that hard-refuses out-of-allowlist remote code, and a
regression test that names its own CVE and enumerates the substring-bypass
attacker would try. That is the most security-literate handling of this exact
class I've scanned.

**This is a reachability scan, not a count scan.** Trivy returns 24 lockfile
CVEs; the honest number of reachable, undefended ones is zero. `starlette`
needs the opt-in service extra; `gitpython`'s scariest CVE needs a calling
pattern OpenMed doesn't use; `urllib3`'s decompression bombs need an untrusted
download peer where the peer is HuggingFace. This is the same lesson the
Ouroboros and mistral-vibe scans taught — a version-match is a hypothesis, and
the affected *surface* plus "is it reachable here?" is the test. The raw count
overstates risk by the full count.

**The security posture is baked into the dev loop, not bolted on.** Pre-commit
runs `bandit` (high-severity), `gitleaks` (custom `.gitleaks.toml`), and
`ruff`; Dependabot is wired; there are CI `release-gates`. A solo academic
maintainer (the project ships an arXiv paper and 1,000+ HF checkpoints) is
running a tighter security pipeline than several commercially-backed repos in
this series. The clean result isn't an absence of attack surface — a
PHI-touching model loader has plenty — it's a maintainer who closed the surface
first.

## Notes on the tool

- **`trust_remote_code` is invisible to the scanner as a *defended* control.**
  AI PatchLab surfaces the `transformers` CVE from the lockfile but has no way
  to connect it to the allowlist + refuse + regression-test defense in the
  source. A future enrichment: when a dependency CVE maps to a known
  application-level control (e.g. `trust_remote_code` allowlisting,
  `tarfile filter='data'`), check for the mitigation pattern and downgrade the
  finding's effective severity. This is the same "rules can't see the
  mitigation" gap that the fast-agent and zotero-mcp scans surfaced — worth a
  backlog item for a mitigation-aware reachability pass.
- **`run-shell-injection` should carry the trigger context.** A
  `workflow_dispatch`-only injection and a `pull_request_target` injection are
  the same rule hit but orders of magnitude apart in risk. The finding should
  note the workflow's `on:` triggers so curation doesn't have to re-derive
  whether the inputs are attacker-controllable. Backlog item.
- **`logger-credential-leak` went 6-for-6 FP again** (logs of exception
  objects and model names, never secrets) — consistent with honcho,
  google_workspace_mcp, and linkedin-mcp-server. The rule's precision on this
  codebase class remains low.
- **`python37-compatibility` (4 hits) is pure noise** on a
  `requires-python = ">=3.10"` project. Compatibility lint should not surface
  as a high-severity security finding.

## Disclosure timeline

- 2026-06-24 — scan run
- 2026-06-24 — public post (this page); clean scan, no upstream issue filed

This is a post-only clean-scan write-up. Curation found no real, reachable,
undefended item that would warrant a courtesy issue — the one exploitability-
shaped vector is already defended with a named-CVE regression test, and the
dependency drift is on a configured Dependabot lane.

## Reproduce

```bash
git clone https://github.com/maziyarpanahi/openmed /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/maziyarpanahi-openmed \
  --min-severity medium --ignore-samples
```
