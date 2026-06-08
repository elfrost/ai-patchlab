---
layout: default
title: "pixeltable/pixeltable: security scan"
date: 2026-05-27
---

# pixeltable/pixeltable — security scan

**Repository:** [pixeltable/pixeltable](https://github.com/pixeltable/pixeltable) — 1.6k★, Apache-2.0, a declarative and incremental data backend for multimodal AI (images, video, audio, documents) with first-class table-sharing.
**Commit scanned:** `d83a4c29fb0d` (HEAD of `main` at scan time)
**Scan date:** 2026-05-27
**Disclosure status:** ✅ **Resolved.** Public courtesy issue ([#1376](https://github.com/pixeltable/pixeltable/issues/1376)) filed on the pixeltable repo with one specific real finding (a tarfile extraction without the safety filter on a code path that imports user-shared bundles). Contributor @aaron-siegel asked for a PR; PR [#1378](https://github.com/pixeltable/pixeltable/pull/1378) opened the same day with the single-line `filter='data'` change and was merged into `main` on **2026-06-07** by @sergey-mkhitaryan (silent merge — issue #1376 auto-closed in the same second). The post covers the broader scan as usual.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 41 |
| Medium | 26 |
| Low | 0 |
| Info | 0 (filtered) |

**67 total findings. After curation: one specific finding worth flagging (a Python tarfile extraction without the `filter='data'` safety filter on a code path that imports cross-user shared bundles), the recurring SQL-identifier-interpolation class at modest scale in the catalog layer, and a familiar tail of false positives.**

This scan is the first in the series to surface a **CVE-2007-4559-shape tarfile extraction** finding, which makes it worth dwelling on. The rest of the scan is structurally clean — 26 SQL-text findings of the now-well-documented identifier-interpolation class, one workflow shell-interpolation, two `urllib3` dep advisories, and otherwise nothing.

## Top findings (curated)

### 1. `pixeltable/share/packager.py:418` — `tarfile.extractall()` without the `filter='data'` safety filter

**Tool:** Semgrep (`tarfile-extractall-traversal`, medium confidence)
**Verdict:** **Real, and on a code path that explicitly handles user-supplied data.**

```python
def restore(self, bundle_path: Path, pxt_uri: str | None = None, ...) -> pxt.Table:
    # Extract tarball
    print(f'Extracting table data into: {self.tmp_dir}')
    with tarfile.open(bundle_path, 'r:bz2') as tf:
        tf.extractall(path=self.tmp_dir)
```

The `restore()` function is on the `Restorer` class in `pixeltable/share/` — the subsystem that imports pixeltable tables packaged as tar bundles. If a user calls `restore()` on a bundle they received from another user (and pixeltable's whole `share/` directory implies that's the supported workflow), a malicious bundle with paths like `../../../etc/something` or symlinks pointing outside `tmp_dir` will be extracted there.

This is [CVE-2007-4559](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2007-4559) — Python's `tarfile.extractall` has been known to be vulnerable to path-traversal for nearly two decades, and `filter='data'` was added in Python 3.12 specifically to fix this class. Pixeltable's `requires-python` floor is 3.10, but for the `filter` kwarg the 3.12 minimum is acceptable since `tarfile.extractall` started warning-deprecating no-filter calls in 3.12 anyway. The fix is a single kwarg:

```python
with tarfile.open(bundle_path, 'r:bz2') as tf:
    tf.extractall(path=self.tmp_dir, filter='data')
```

The `'data'` filter rejects absolute paths, `..` traversal, and unsafe symlinks/devices — exactly the set of attack vectors that make tar bundles dangerous to extract from external sources. The Python docs ([PEP 706](https://peps.python.org/pep-0706/)) recommend it as the default for any extraction from untrusted bundles.

**Realistic exploit window:** if pixeltable's sharing model lets one user publish a bundle that another user fetches and `restore()`s without inspecting, a malicious publisher can write arbitrary files (limited by the running user's permissions) on the receiver's machine. The fix is mechanical and removes the class.

### 2. 26× `text(f"...")` identifier interpolation across `pixeltable/catalog/*`

**Files:** `pixeltable/catalog/{catalog,dir,table,table_version,tbl_ops}.py` and others
**Tool:** Semgrep (`avoid-sqlalchemy-text`, medium confidence)
**Verdict:** **Same class as on five prior scans — gated by Pydantic-validated identifiers today, brittle to future input-source changes.**

Pixeltable's catalog layer maintains its own versioned table schema, and the catalog operations build SQL with `text(f"... {identifier} ...")` where the identifier comes from internal config (table names, schema names, version numbers). At 26 sites it's the largest cluster of this class in core source code in any scan so far — but the realistic exploit window is the same as on [Upsonic](upsonic-upsonic.html), [PraisonAI](mervinpraison-praisonai.html), [airweave](airweave-ai-airweave.html), [honcho](plastic-labs-honcho.html), and [dstack](dstackai-dstack.html): the identifier is config-controlled, so SQL injection is gated until/unless a future change lets it come from somewhere less constrained.

The defensible fix is the same SQLAlchemy `quoted_name()` / `Identifier()` pattern. With 26 call sites in a single subsystem, a shared helper (`def _quoted_table_ref(...)`) generalizes the fix without changing every site.

### 3. 1× workflow `${{ ... }}` shell interpolation

**File:** `.github/workflows/pytest.yml:118`
**Tool:** Semgrep (`run-shell-injection`)
**Verdict:** **Real best-practice — the recurring class. Lowest count of the class in any scan in this series so far** (single occurrence).

Same fix template as the seven prior scans where this class fired: pass through `env:` and reference `$VAR` from the shell.

### 4. 2× `urllib3` advisories in `uv.lock`

**Verdict:** **Real — single bump clears both.**

Two published `urllib3` advisories against the pinned version. Update the `urllib3` pin (or its parent dep) to a release past the advisory fix versions.

### 5-N. Suppressed-by-context items

| Finding | Files | Verdict |
|---|---|---|
| 7+ Next.js advisories | `docs/sample-apps/text-and-image-similarity-search-nextjs-fastapi/frontend/package-lock.json` | **Out of scope — sample app**, not the deployed product. Same pattern as the `examples/**` suppressions on Klavis / honcho / dograh write-ups. |
| 2× `wildcard-cors` | `docs/sample-apps/{ai-based-trading-insight-chrome-extension/server,multimodal-chat/backend}/main.py` | Sample apps |
| 2× `Image user should not be 'root'` | `docs/sample-apps/{jfk-files-mcp-server,multimodal-chat/backend}/Dockerfile` | Sample apps |
| 1× "secret detected" | `tests/data/documents/Section 10_ Financial Responsibility, Insurance Requirements, and Collisions - California DMV.html:976` | **FP** — test fixture, an HTML document from California DMV used to exercise document-parsing |
| 9× `non-literal-import` | `pixeltable/{env,exprs/expr,func/function,func/function_registry,func/globals,...}.py` | **By design** — function registry / plugin discovery |
| 3× `dynamic-urllib-use-detected` | `pixeltable/dashboard/harness.py:41`, `type_system.py:1640`, `utils/object_stores.py:621` | URL building patterns; need per-line context but typically the safe case |
| 2× `dangerous-globals-use` | `pixeltable/functions/whisperx.py:107`, `type_system.py:126` | Plugin / dispatch pattern |
| 2× `ifs-tampering` | `scripts/{prepare-nb-tests,run-isolated-nb-tests}.sh` | Build-script shell hardening — minor |

## Patterns observed

**The tarfile finding is the cleanest "actually exploitable, mechanical fix" item the series has surfaced in source code (vs. dependency advisories).** Every prior real finding was either a dep CVE (single bump), a workflow shell-injection (single `env:` indirection), or a Dockerfile USER directive. The tarfile case is the first time a single line of Python code in a real codebase, on a code path explicitly designed to handle externally-sourced data, has a recognized CVE-class fix. The fix is also single-line (`, filter='data'`), so the "real impact / mechanical change" ratio is unusually favorable.

**26 SQL-text sites in `pixeltable/catalog/*` is the largest core-source cluster of this class in the series so far.** Most prior occurrences (Upsonic, PraisonAI, honcho) had the bulk of `text(f"...")` calls in migration scripts, with only a handful in runtime source. Pixeltable has them in the live catalog subsystem — built up incrementally for an incremental-data-backend's table-versioning system. The architectural defense remains the same (`quoted_name()`/`Identifier()`), but at 26 sites in one subsystem, a shared helper makes more sense than per-site fixes.

**A scan with one real finding and 65 to explain is exactly the shape "right-sized" means.** This is the second scan picked under the refined target-selection criteria (after [dograh](dograh-hq-dograh.html)) — responsive maintainer team, mid-popularity, focused codebase. The result is what we hope for: a curation pass that takes 30 minutes, surfaces one specific actionable item, and contextualizes the rest cleanly. Compare to [Klavis' 1,556-finding monorepo curation marathon](klavis-ai-klavis.html) or [HolmesGPT's 2,143 K8s-fixture deluge](holmesgpt-holmesgpt.html).

## Notes on the tool

- **The `tarfile-extractall-traversal` Semgrep rule is a useful one to highlight.** It's specific (the AST shape is unambiguous), it has a single-kwarg fix, and the CVE class behind it has nearly two decades of history. Worth keeping `confidence: medium` (which AI PatchLab does for all Semgrep findings per the [confidence rules](https://github.com/elfrost/ai-patchlab/blob/main/scanner/confidence.py)) rather than elevating, but worth noting as a rule that punches above its weight.
- The "sample apps under `docs/sample-apps/**`" suppression pattern keeps appearing. After honcho's `examples/**` and Klavis' `examples/**` ignores, this is the third scan where path-suppression of demo/sample subtrees was load-bearing for keeping the report focused. A shipped default ignore pattern for common sample-app directory names (`samples/`, `sample-apps/`, `examples/`, `demos/`) is overdue.

## Disclosure timeline

- **2026-05-27** — Scan run at commit `d83a4c29fb0d`; findings curated. Sample-app subtrees flagged but not suppressed via ignore-file (small scan size).
- **2026-05-27** — Public courtesy issue [#1376](https://github.com/pixeltable/pixeltable/issues/1376) filed on pixeltable/pixeltable focusing on the `share/packager.py` tarfile finding (the one specific, exploit-shaped item). The 26-site SQL class and the workflow-input pattern mentioned more briefly given the issue-format lessons from the [dstack rejection](dstackai-dstack.html#maintainer-response-and-lessons).
- **2026-05-27** — Contributor [@aaron-siegel](https://github.com/aaron-siegel) replied within hours: *"Thanks for reporting this. Yes, please do open a PR for the tarfile fix — thanks for catching that!"* PR [#1378](https://github.com/pixeltable/pixeltable/pull/1378) opened the same day with the single-line `tf.extractall(path=self.tmp_dir, filter='data')` change.
- **2026-06-07 (~11 days later)** — ✅ Maintainer [@sergey-mkhitaryan](https://github.com/sergey-mkhitaryan) merged PR [#1378](https://github.com/pixeltable/pixeltable/pull/1378) into `main` (merge commit `8c52f50be1`); issue [#1376](https://github.com/pixeltable/pixeltable/issues/1376) auto-closed as completed in the same second. Silent merge after PR sat through standard review; all CI checks had been green since the day the PR was opened.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/pixeltable/pixeltable" \
  --reports-dir reports/pixeltable-pixeltable \
  --min-severity medium
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
