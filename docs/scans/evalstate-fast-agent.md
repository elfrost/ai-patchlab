---
layout: default
title: "evalstate/fast-agent: security scan"
description: "Security scan of evalstate/fast-agent: 36 findings, near-clean scan where the maintainer already hand-rolled the hard mitigations (a tar-traversal guard"
date: 2026-05-28
---

# evalstate/fast-agent — security scan

**Repository:** [evalstate/fast-agent](https://github.com/evalstate/fast-agent) — 3.8k★, Apache-2.0, a Python framework to build, run, and evaluate agents with first-class MCP / Skills / ACP support.
**Commit scanned:** `3a1c4696ca3a` (HEAD of `main` at scan time)
**Scan date:** 2026-05-28
**Disclosure status:** ✅ **Resolved.** Public courtesy issue ([#811](https://github.com/evalstate/fast-agent/issues/811)) filed with two defense-in-depth hardenings; the maintainer adopted **both** in release **v0.7.13** the same day (~8 hours later). The post covers the broader scan as usual.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 28 |
| Medium | 8 |
| Low | 0 |
| Info | 0 (filtered) |

**36 total findings. After curation: a near-clean scan whose defining feature is that the maintainer has already hand-rolled mitigations for the two scariest patterns — a tar-extraction traversal guard and a filename sanitizer in front of a shell call. The actionable surface is two defense-in-depth hardenings that strengthen those existing guards, plus a `requests` dependency-CVE pair that the repo's Dependabot is already positioned to clear.**

fast-agent is the kind of scan the refined target-selection criteria are meant to surface: a responsive solo maintainer (the merged-PR history is almost entirely `@evalstate` + Dependabot), a focused codebase, and — notably — a maintainer who already engages with security reports (issue [#746](https://github.com/evalstate/fast-agent/issues/746) was a "tool description injection" audit). The scan reflects that posture: the dangerous-looking findings are, on inspection, already defended.

## Top findings (curated)

### 1. `src/fast_agent/plugins/operations.py` — tar extraction has a hand-rolled traversal guard; prefer `filter='data'` to also cover symlinks

**Tool:** Semgrep (`tarfile-extractall-traversal`, medium confidence)
**Verdict:** **Already mitigated against the `..` vector — the residual gap is link members.**

The plugin-install path extracts a `git archive` tarball through a dedicated helper:

```python
def _extract_tar_safely(archive_file: BinaryIO, destination_dir: Path) -> None:
    destination_root = destination_dir.resolve()
    with tarfile.open(fileobj=archive_file, mode="r:") as archive:
        for member in archive.getmembers():
            target = (destination_root / member.name).resolve()
            target.relative_to(destination_root)   # raises ValueError if escaping
        archive.extractall(destination_root)
```

This is meaningfully better than the [CVE-2007-4559](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2007-4559) baseline: the `relative_to()` check rejects any member whose path escapes the destination via `..`, so the classic path-traversal vector is closed. The residual gap is that the check validates member *names*, not link semantics — a symlink or hardlink member whose own name is in-bounds but whose target points outside isn't caught, and `extractall` will create it. Python's `filter='data'` ([PEP 706](https://peps.python.org/pep-0706/)) rejects exactly that class (unsafe symlinks/hardlinks, absolute targets, special files) on top of the `..` rejection the code already does.

The realistic exploit window is narrow: the tar comes from `git archive` of a plugin repository the user has chosen to install (semi-trusted, the same trust you extend to any package you install). So this is a defense-in-depth hardening, not an open hole — `extractall(destination_root, filter='data')` generalizes the existing guard for free.

### 2. `src/fast_agent/ui/mcp_ui_utils.py` — Windows file-open uses `shell=True`; the other platforms don't

**Tool:** Semgrep (`subprocess-shell-true`, medium confidence)
**Verdict:** **Mitigated by an upstream filename sanitizer — but inconsistent with the macOS/Linux branches.**

`open_links_in_browser()` opens a locally-written HTML file per platform. macOS and Linux pass an argv list with no shell; only the Windows branch uses `shell=True`:

```python
elif system == "Windows":
    subprocess.run(["start", "", file_path], shell=True, check=False, capture_output=True)
```

`file_path` is not free-form attacker input: it's built by `_write_html_file()` as `<output_dir>/<safe>_<i>.html`, where the title is passed through `_safe_filename()`:

```python
def _safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return name[:120] if len(name) > 120 else name
```

That sanitizer collapses every shell metacharacter to `_`, and the extension is a fixed `.html` in a controlled directory — so even though the MCP server controls the title, the resulting path can't carry an injection. The finding is real as a *consistency / defense-in-depth* item: the Windows branch doesn't need `shell=True` (e.g. `os.startfile(file_path)`), and matching the safe pattern the other two branches already use removes the one place a future refactor of `_safe_filename` could turn into a problem.

### 3. `requests` — CVE-2024-47081 + CVE-2026-25645 (Trivy/pip-audit)

**Verdict:** **Real, but Dependabot's lane.** Two named advisories against the pinned `requests`. A single version bump clears both, and the repo already runs Dependabot (a Dependabot PR is in the recent merge history), so this is most useful as a "make sure the bot's PR isn't sitting unreviewed" note rather than a separate ask.

### 4-N. By-design / out of scope

| Finding | Verdict |
|---|---|
| 2× `subprocess shell=True` in `ui/interactive_shell.py` | **By-design** — this *is* the interactive-shell feature; the user runs their own shell |
| 1× `subprocess shell=True`, 1× `exec`, 1× `tarfile` in `scripts/` | **Dev tooling** — `cpd.py`, `docs_terminal_capture.py`, `gen_schema.py` aren't shipped runtime |
| 3× `non-literal-import` in `src/fast_agent/{cli/main,llm/structured_schema,privacy/privacy_filter_onnx}.py` | **By-design** — plugin / backend discovery |
| 2× `dynamic-urllib-use-detected` | URL-building patterns; typically the safe case |
| 10× gitleaks `generic-api-key` | **FP** — all in `tests/fixtures/.../sanitized/` LLM-trace recordings, `AGENTS.md`, and test files |
| 10× `python37/python36-compatibility-*` | **Noise** — Semgrep compatibility rules, not security findings |

## Patterns observed

**This is the first scan where the headline is "the maintainer already did the hard part."** On [pixeltable](pixeltable-pixeltable.html) the same `tarfile-extractall` rule fired on a call with *no* guard at all — a clean one-kwarg fix. Here it fired on a path that already has a hand-rolled `relative_to()` traversal check, and the `shell=True` finding sits behind a real filename sanitizer. The curated output isn't "you have a hole," it's "your guards are good; here's how to make them cover the last 10% for free." That's a more pleasant — and more credible — note to send a security-conscious solo maintainer.

**Compatibility-rule noise (20 of 36 findings once you include the gitleaks fixtures) is the dominant non-signal here.** The `python37`/`python36-compatibility-*` rules are pure version-targeting lint, not security, and the gitleaks hits are all sanitized trace fixtures. A scan that's ~55% explainable-as-noise but with a clean residual is exactly the shape the `--ignore-samples` default (shipped in this scan) and a future `tests/fixtures/**` default suppression are meant to keep quiet.

**A solo maintainer with Dependabot turns the dependency tail into a non-ask.** The `requests` CVEs are real, but filing a manual issue for them would duplicate the bot. The unique value of a scan-plus-human-curation pass here is precisely the two code-level items Dependabot can't see — so the courtesy issue is scoped to those.

## Notes on the tool

- This is the first scan run with the **`logger-credential-leak` confidence downgrade** and the **`--ignore-samples`** default-suppression flag shipped from the cross-scan curation data (6/6 false positives on the former across the series; demo/sample subtrees being the most common out-of-scope source for the latter). Neither changed the curation outcome here — fast-agent has no `samples/` tree and no logger-leak hits — but they're now in the default pipeline.
- The `tarfile-extractall-traversal` rule keeps earning its place: it fired on a genuinely different shape than [pixeltable](pixeltable-pixeltable.html) (guarded vs unguarded), and distinguishing the two is exactly the judgment a static rule can't make on its own.

## Disclosure timeline

- **2026-05-28** — Scan run at commit `3a1c4696ca3a`; findings curated. Sample/demo suppression on by default; no path-ignore file needed.
- **2026-05-28** — Public courtesy issue filed on evalstate/fast-agent with the two defense-in-depth hardenings (tar `filter='data'`, Windows `shell=True` removal), offering to open a PR if welcome.
- **2026-05-28 (same day, ~8h later)** — ✅ Maintainer closed [#811](https://github.com/evalstate/fast-agent/issues/811) as completed: *"Thanks for the report, both addressed in 0.7.13."* Verified in [v0.7.13](https://github.com/evalstate/fast-agent/releases/tag/v0.7.13): `_extract_tar_safely` now calls `extractall(..., filter="data")` and the Windows branch of `open_links_in_browser` now uses `os.startfile(file_path)` (no `shell=True`). Both hardenings adopted exactly as suggested.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/evalstate/fast-agent" \
  --reports-dir reports/evalstate-fast-agent \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
