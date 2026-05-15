---
name: "Web Template Fingerprinting (v0.1)"
description: |
  Index open-source SaaS/website repositories into deterministic fingerprints, then
  probe a single live URL and report which seeded repo (if any) the site was likely
  built from. Local-first, single-target, no crawling, probabilistic signal.
---

# PRP: Web Template Fingerprinting (v0.1)

## Overview
Add a new top-level module `fingerprint/` that does two things:

1. **Index** a curated list of open-source website / SaaS template repositories into
   deterministic `RepoFingerprint` records (favicon SHA-256, hashes of distinctive
   static assets, HTML signature regexes, string markers).
2. **Match** one live target URL against the local fingerprint database, fetching the
   page and a small allowlist of asset paths over HTTPS, and emit a JSON + Markdown
   report ranking each candidate repo by a transparent match score.

v0.1 is intentionally minimalist:

- Single target per invocation (`fingerprint/run_match.py --target https://example.com`).
- Curated seed list committed in the repo (`fingerprint/seeds/repos.json`) — no GitHub
  search, no automated discovery.
- Indexing is also single-shot: `fingerprint/run_index.py --rebuild` or
  `--repo-url <url>` for one entry. No background jobs, no DB.
- Matching is **probabilistic** and labelled as such in the report. The output is a
  ranked list of candidates with a score and the matched signals; it is never an
  attribution claim.
- All HTTP I/O via `httpx` with a short timeout, an explicit `User-Agent`
  (`ai-patchlab-fingerprint/0.1`), `follow_redirects=True`, a hard cap on bytes
  fetched per asset, and **no recursion / no link following beyond the seeded asset
  paths**.

This PRP does not introduce a database, a web UI, JS rendering, scheduling, or any
form of mass crawling. Those are out of scope and will require their own ADRs.

## Dependencies
- Requires: Phase 1 scanner foundation — reuse `scanner/git_source.py:cloned_repo` for
  shallow-cloning seed repos into temp dirs with cleanup-on-exit.
- Requires: Phase 2 runner pattern — frozen `*Result` dataclasses, `OSError` /
  `subprocess.TimeoutExpired` catch-and-normalize behavior.
- Requires: ADR-010 boundary discipline — fingerprinting must not call any paid API,
  any AI provider, or any service besides the user-supplied target URL and the public
  git remotes of the seeded repos.
- Blocks: future Pages-published "Detected templates" log under `docs/scans/`, and any
  future cross-correlation between PatchLab vulnerability scans and template
  detection (e.g. "this site is built from repo X, and repo X has these CVEs").

## Context & References

### MUST READ — Load these into your context
- file: `CLAUDE.md` — why: project rules, scanner adapter contract, subprocess and
  network conventions, automatic housekeeping requirements.
- file: `AGENTS.md` — why: Codex parity; any new module section added to CLAUDE.md
  must be mirrored here.
- file: `ROADMAP.md` — why: where to add a new "Phase 4 — Template Fingerprinting"
  block once the PRP is accepted.
- file: `DECISIONS.md` — why: ADR-002 (data stack), ADR-003 (placeholder-then-real
  pattern), ADR-010 (no-default-remote-call boundary) — this PRP must respect all
  three. A new ADR-012 is added by this PRP.
- file: `INITIAL.md` — why: confirm scope alignment with the MVP framing.
- file: `scanner/run_scan.py` — why: CLI entry-point pattern (argparse, prints final
  report paths via `print()`, returns 0 on partial success).
- file: `scanner/git_source.py` — why: `cloned_repo` context manager — REUSE
  verbatim, do not duplicate. Already validates URL, uses `shell=False`, cleans up.
- file: `scanner/models.py` — why: pattern for frozen dataclass + `__post_init__`
  validation + `to_dict()`. `RepoFingerprint` and `MatchResult` follow the same
  conventions; do NOT shoehorn fingerprints into `Finding`.
- file: `scanner/report.py` — why: pattern for severity-grouped JSON + MD report.
  `fingerprint/report.py` follows the same writer style (no Jinja, plain f-strings).
- file: `scanner/tools/pip_audit_runner.py` — why: reference runner shape (frozen
  `*Result`, raw JSON path, `subprocess.run(..., shell=False, check=False)`,
  `OSError` / `TimeoutExpired` catch).
- file: `scanner/scanners/dependency_scan.py` — why: reference for the
  parse → enrich → normalize → fallback-to-info-finding flow.
- file: `examples/api_client_pattern.py` — why: `httpx.AsyncClient` pattern with
  retries and timeouts. v0.1 may stay synchronous (`httpx.Client`) — call this out
  in the implementation section.
- file: `examples/config_pattern.py` — why: pydantic-settings model with
  `AI_PATCHLAB_` env prefix; `FingerprintConfig` follows the same shape.
- file: `pyproject.toml` — why: `httpx` is already a runtime dependency; **no new
  runtime deps** should be added in this PRP.
- doc: https://www.python-httpx.org/advanced/clients/ — section: timeouts,
  `follow_redirects`, `User-Agent`. We use a short total timeout (5s) and read
  timeout (10s).
- doc: https://docs.python.org/3/library/hashlib.html — section: `hashlib.sha256` for
  asset content hashes.

### Critical Gotchas
- CRITICAL: This module fetches a user-supplied URL. Validate the scheme (only
  `http` / `https`), reject `file://`, `gopher://`, etc. Do NOT pass user input into
  any subprocess. The HTML/JS we fetch is **never executed** — only parsed as bytes
  and matched with `re` / hashing.
- CRITICAL: The match score is a **signal, not an attribution**. The report MUST
  prefix candidate sections with the wording "Probable template match — manual
  verification required" and MUST NOT use words like "confirmed", "proven",
  "stolen", "copied". Tested explicitly in `tests/test_fingerprint_report.py`.
- CRITICAL: Respect `robots.txt`. Before fetching anything beyond the homepage, call
  `urllib.robotparser.RobotFileParser` for the target host. If the homepage itself
  is disallowed for our `User-Agent`, abort with a normalized "robots-disallowed"
  result (no findings, score=0, reason recorded). No flag bypasses this in v0.1.
- CRITICAL: Hard cap on fetched bytes per asset (default 512 KiB) and on total
  assets fetched per target (default 16, including the homepage). Anything larger
  is truncated and that asset's hash is marked `truncated=True` instead of being
  silently mis-hashed.
- CRITICAL: No mass crawl. The CLI accepts one `--target` URL per invocation. Do
  NOT add a `--targets-file` flag in this PRP. If a user wants to scan many URLs,
  they invoke the CLI repeatedly — that's a deliberate friction.
- CRITICAL: Subprocess discipline (from `cloned_repo`): `shell=False`, explicit
  argv list, `check=False`. The git clone is the only subprocess this module
  executes.
- CRITICAL: Never publish a fingerprint match result to `docs/scans/` automatically.
  Publishing is a manual step. The CLI writes only to `reports/fingerprint/`.
- CRITICAL: Do not add `beautifulsoup4`, `lxml`, `playwright`, `selenium`, or any
  scraping framework. v0.1 uses `re` + `hashlib` + `httpx` only. If a future
  version needs DOM parsing, that's a new ADR.
- CRITICAL: Seed list is **curated and committed**. Indexing a new repo requires a
  human PR adding its URL to `fingerprint/seeds/repos.json`. Do not add a "discover
  repos by topic" feature that hits the GitHub API in v0.1.
- CRITICAL: Each fingerprint run against a real target hits a third-party server.
  Tests MUST mock `httpx` (use `respx` only if it's already in dev deps; otherwise
  use `httpx.MockTransport`, which is built-in). Never let the test suite make a
  live HTTP call.

## Architecture

### New Files
| File | Purpose |
|------|---------|
| `fingerprint/__init__.py` | Module marker; empty or re-exports `RepoFingerprint`, `MatchResult`. |
| `fingerprint/models.py` | Frozen dataclasses: `AssetFingerprint`, `HtmlSignature`, `RepoFingerprint`, `MatchResult`, `MatchSignal`. Validation in `__post_init__` mirroring `scanner/models.py`. |
| `fingerprint/config.py` | Pydantic settings (`FingerprintConfig`) — fetch timeout, max bytes per asset, max assets per target, user agent string, fingerprint DB path. Defaults shipped. |
| `fingerprint/git_seeds.py` | Load and validate `fingerprint/seeds/repos.json`; small helpers to iterate seed entries with name + URL + optional `notable_paths` hint. |
| `fingerprint/seeds/repos.json` | Curated JSON list of seeded open-source template repos. v0.1 ships with 3–5 entries (e.g. a Next.js SaaS starter, a Jekyll theme, an Astro starter — pick public, well-known repos). |
| `fingerprint/extractors/__init__.py` | Registry tuple `EXTRACTORS` analogous to `scanner/scanners/__init__.py:SCANNERS`. |
| `fingerprint/extractors/favicon.py` | `extract_favicon(repo_root: Path) -> AssetFingerprint \| None` — finds `favicon.ico` / `favicon.png` / `public/favicon.*`, returns SHA-256 + relative path. |
| `fingerprint/extractors/static_assets.py` | Walks repo for distinctive static asset paths (CSS/JS files in conventional folders: `public/`, `static/`, `assets/`, `dist/`). Returns up to N hashes per repo (capped, deterministic order). |
| `fingerprint/extractors/html_signatures.py` | Greps the repo for HTML/JSX/Vue/Astro template files and extracts unique class names, IDs, `data-*` attributes, meta-generator strings, and comment markers. Returns `list[HtmlSignature]`. |
| `fingerprint/repo_index.py` | Indexer: clones a seed repo (via `scanner.git_source.cloned_repo`), runs every extractor, assembles a `RepoFingerprint`, persists it to `fingerprint/db/<slug>.json`. |
| `fingerprint/web_probe.py` | `fetch_target(url, config) -> TargetSnapshot` — sync `httpx.Client`, robots.txt check, homepage fetch, then fetch a small allowlist of likely asset paths (favicon, common css/js bundle names from the seeded fingerprints' `notable_paths`). Caps bytes & count. |
| `fingerprint/matchers/__init__.py` | Registry of matcher callables. |
| `fingerprint/matchers/asset_hash.py` | Compares each `RepoFingerprint.assets[*].sha256` against `TargetSnapshot.fetched_assets[*].sha256`. Each match emits a `MatchSignal` with weight (favicon=high, distinctive static asset=medium). |
| `fingerprint/matchers/html_regex.py` | For each `HtmlSignature`, checks the homepage HTML bytes for the marker. Emits `MatchSignal` with weight depending on signature uniqueness (meta-generator=high, distinctive class=medium, comment marker=high). |
| `fingerprint/scoring.py` | `score_signals(signals: list[MatchSignal]) -> float` — bounded weighted sum, 0.0 to 1.0. Documented thresholds: <0.3 weak, 0.3–0.6 plausible, ≥0.6 strong. Single source of truth, tested directly. |
| `fingerprint/run_index.py` | CLI entry: `python fingerprint/run_index.py --rebuild` rebuilds all seeds; `--repo-url <url>` indexes one. Writes to `fingerprint/db/`. |
| `fingerprint/run_match.py` | CLI entry: `python fingerprint/run_match.py --target <url>` produces `reports/fingerprint/match_<host>_<timestamp>.json` + `.md`. Returns 0 always (partial-result discipline). |
| `fingerprint/report.py` | JSON + Markdown writer for match results. Markdown is grouped by score band, prefixed with the "probable match — manual verification required" disclaimer, and lists every matched signal with its weight. |
| `tests/test_fingerprint_models.py` | Validation rules on the dataclasses (bad sha length, empty url, etc.). |
| `tests/test_fingerprint_extractors.py` | Each extractor against tiny temp repos built in fixtures. |
| `tests/test_fingerprint_web_probe.py` | `httpx.MockTransport` fixtures for: 200 OK + assets, 404 homepage, robots.txt disallowing root, redirect chain, oversize asset, scheme rejection (`file://`). |
| `tests/test_fingerprint_matchers.py` | Each matcher in isolation: matched signal, no-match, partial match (homepage hashes differ but favicon matches). |
| `tests/test_fingerprint_scoring.py` | Threshold boundaries and weighted sum behavior. |
| `tests/test_fingerprint_report.py` | JSON + MD output shape; disclaimer wording check; band grouping; empty-match still produces a valid report. |

### Modified Files
| File | Changes |
|------|---------|
| `CLAUDE.md` | Add `fingerprint/` to **Key Directories**; add a new **Fingerprint adapter contract** subsection mirroring the **Scanner adapter contract**; add gotchas: robots.txt respect, single-target rule, no scraping framework, score-is-signal discipline. |
| `AGENTS.md` | Mirror the same additions for Codex runtime parity. |
| `ROADMAP.md` | Add a new section `## Phase 4 — Template Fingerprinting` with the v0.1 items: seed list committed, indexer working, single-target matcher working, JSON+MD report generated, ADR-012 logged. Mark each `[ ]` until the PRP completes. |
| `DECISIONS.md` | Add `ADR-012: Probabilistic web template fingerprinting boundary` (Lite format) at the top of the Decisions list. Decision: single-target probe, curated seed list, no crawl, no DOM parser, no AI, score is a signal. |
| `pyproject.toml` | **No changes expected.** `httpx`, `pydantic`, `pydantic-settings`, `pytest`, `pytest-mock` are already declared. If a runtime dep would be needed, stop and reconsider — a new dep needs an ADR. |
| `README.md` | Add a `## Web Template Fingerprinting (experimental)` section explaining: what it does, what it does NOT do (single-target, probabilistic, manual review required), how to run the indexer, how to run a match, where the report goes, and the robots.txt + bytes caps. |
| `scanner/run_scan.py` | **No changes.** Fingerprinting is a separate CLI; it does not run as part of `run_scan`. Cross-correlation is future work. |

### Database Changes
None. Fingerprints are persisted as one JSON file per seeded repo under
`fingerprint/db/<slug>.json` (gitignored except for a `.gitkeep`). Match reports go
under `reports/fingerprint/` (also gitignored except `.gitkeep`).

### Data Contracts

**`RepoFingerprint` (frozen dataclass)**
```python
@dataclass(frozen=True)
class RepoFingerprint:
    slug: str                           # stable kebab-case id derived from repo URL
    repo_url: str                       # canonical https URL
    indexed_at: str                     # ISO-8601 UTC
    assets: tuple[AssetFingerprint, ...]
    html_signatures: tuple[HtmlSignature, ...]
    notable_paths: tuple[str, ...]      # asset paths the matcher should try fetching
```

**`AssetFingerprint`**
```python
@dataclass(frozen=True)
class AssetFingerprint:
    relative_path: str                  # repo-relative POSIX
    sha256: str                         # 64 hex chars
    byte_size: int
    kind: str                           # "favicon" | "css" | "js" | "image" | "other"
```

**`HtmlSignature`**
```python
@dataclass(frozen=True)
class HtmlSignature:
    kind: str                           # "meta-generator" | "class" | "id" | "data-attr" | "comment"
    pattern: str                        # plain string OR a constrained regex (validated)
    weight: str                         # "high" | "medium" | "low"
```

**`MatchResult`**
```python
@dataclass(frozen=True)
class MatchResult:
    target_url: str
    fetched_at: str
    repo_slug: str
    score: float                        # 0.0–1.0
    band: str                           # "weak" | "plausible" | "strong"
    signals: tuple[MatchSignal, ...]
    notes: str = ""                     # e.g. "robots-disallowed", "homepage-truncated"
```

**Match report Markdown skeleton**
```markdown
# Fingerprint match report

**Target:** https://example.com
**Fetched:** 2026-05-14T12:34:56Z
**Disclaimer:** Probable template match — manual verification required.
This report is a probabilistic signal, not an attribution.

## Strong matches (score ≥ 0.6)
### nextjs-saas-starter — score 0.78
- favicon SHA-256 match (weight: high)
- meta-generator "Next.js" (weight: high)
- class `.hero-cta-primary` present (weight: medium)

## Plausible matches (0.3 ≤ score < 0.6)
...

## Weak matches (score < 0.3)
...

## Notes
- robots.txt: allowed
- 8 of 16 asset slots used
```

## Implementation Plan

### Task 1: Models, config, seed loader
**Goal:** Lock the data contracts and configuration before any I/O code is written.
**Files:** `fingerprint/models.py`, `fingerprint/config.py`, `fingerprint/git_seeds.py`,
`fingerprint/seeds/repos.json`, `fingerprint/__init__.py`,
`tests/test_fingerprint_models.py`.
**Pattern:** `scanner/models.py` for dataclasses; `scanner/config.py` for pydantic
settings with the `AI_PATCHLAB_` env prefix.
**Details:**
- All five dataclasses are `@dataclass(frozen=True)`. `__post_init__` validates:
  - `sha256` is 64 lowercase hex chars (regex `^[a-f0-9]{64}$`).
  - `repo_url` and `target_url` start with `https://` (or `http://` for the target,
    but log a warning-level note in the report).
  - `score` is in `[0.0, 1.0]`.
  - `band` matches the score (single source of truth: `band_for_score()` helper).
  - `weight` ∈ `{"high", "medium", "low"}`.
  - `kind` (asset) ∈ `{"favicon", "css", "js", "image", "other"}`.
  - `kind` (signature) ∈ `{"meta-generator", "class", "id", "data-attr", "comment"}`.
- `FingerprintConfig` defaults:
  - `fetch_timeout_seconds: float = 10.0`
  - `fetch_total_timeout_seconds: float = 5.0`  # connect + write
  - `max_bytes_per_asset: int = 512 * 1024`
  - `max_assets_per_target: int = 16`
  - `user_agent: str = "ai-patchlab-fingerprint/0.1"`
  - `db_dir: Path = Path("fingerprint/db")`
  - `report_dir: Path = Path("reports/fingerprint")`
  - Env prefix `AI_PATCHLAB_FINGERPRINT_`.
- `repos.json` ships with 3 conservative entries (pick public, popular templates;
  favor variety: 1 Next.js, 1 static-site generator, 1 Astro/Vite). Each entry:
  `{ "slug": "...", "repo_url": "...", "notable_paths": ["public/favicon.ico", "public/og.png"] }`.
- `git_seeds.load_seeds() -> tuple[SeedEntry, ...]` validates the JSON shape and
  rejects entries with non-https URLs or empty slugs.

**Validation:**
```bash
python -m pytest tests/test_fingerprint_models.py -v
python -c "from fingerprint.git_seeds import load_seeds; print(len(load_seeds()))"
```

### Task 2: Extractors
**Goal:** Convert a cloned repo into a `RepoFingerprint`.
**Files:** `fingerprint/extractors/*.py`, `tests/test_fingerprint_extractors.py`.
**Pattern:** Pure functions that take `repo_root: Path` and return data. No I/O
beyond reading repo files. No subprocess.
**Details:**
- `extract_favicon` looks at, in order: `public/favicon.ico`, `public/favicon.png`,
  `static/favicon.ico`, `assets/favicon.ico`, `favicon.ico`. First hit wins. If
  none exists, returns `None`.
- `extract_static_assets` walks `public/`, `static/`, `assets/`, `dist/` (whichever
  exist), collects files with extensions `.css`, `.js`, `.png`, `.svg`, `.woff2`.
  Sorts by relative path (deterministic), keeps the first 12 distinct hashes.
  Skips files larger than `max_bytes_per_asset` (also caps the indexer for
  consistency with the matcher).
- `extract_html_signatures` greps `*.html`, `*.htm`, `*.jsx`, `*.tsx`, `*.vue`,
  `*.astro`, `*.svelte` for:
  - `<meta name="generator" content="...">` → `meta-generator` signature, weight
    `high`.
  - HTML comments containing capitalized words ≥ 3 chars repeated across files
    (likely template boilerplate) → `comment` signature, weight `high`.
  - Class names matching `^[a-z][a-z0-9-]{6,}$` that appear in ≥ 2 files →
    `class` signature, weight `medium`.
  - `data-*` attributes with values → weight `medium`.
- All extractors must be deterministic — same input → same fingerprint bytes.
- Tests build tiny temp repos (`tmp_path` fixture) with crafted files and assert
  the extracted fingerprints match expected hashes / signatures.

**Validation:**
```bash
python -m pytest tests/test_fingerprint_extractors.py -v
```

### Task 3: Indexer CLI
**Goal:** Persist fingerprints for every seeded repo to `fingerprint/db/`.
**Files:** `fingerprint/repo_index.py`, `fingerprint/run_index.py`,
`tests/test_fingerprint_indexer.py`.
**Pattern:** `scanner/run_scan.py` for the CLI shape; `scanner/git_source.py` for
cloning.
**Details:**
- `repo_index.index_seed(seed: SeedEntry, config: FingerprintConfig) -> RepoFingerprint`:
  uses `cloned_repo(seed.repo_url)` (reused verbatim), runs every extractor, builds
  a `RepoFingerprint`, writes it to `config.db_dir / f"{seed.slug}.json"`.
- `run_index.py` argparse:
  - `--rebuild` (no arg): re-index every seed.
  - `--repo-url <url>`: index one ad-hoc repo (slug derived from URL).
  - `--db-dir <path>`: override default.
- On clone failure, write a stub `RepoFingerprint` with `assets=()` and
  `html_signatures=()` and a `notes` field marking `clone-failed`. Do NOT raise.
- The indexer is the ONLY place that performs git clones in this module.

**Validation:**
```bash
python -m pytest tests/test_fingerprint_indexer.py -v
```
(integration smoke against the real seeds is not run in CI; document it as a manual
step in README).

### Task 4: Web probe
**Goal:** Fetch a single target safely.
**Files:** `fingerprint/web_probe.py`, `tests/test_fingerprint_web_probe.py`.
**Pattern:** `examples/api_client_pattern.py` for the `httpx` shape, but synchronous
(`httpx.Client`) — async adds nothing for a single target and would force the rest
of the module to be async.
**Details:**
- Public API: `fetch_target(url: str, config: FingerprintConfig, candidate_paths: tuple[str, ...]) -> TargetSnapshot`.
- Validate scheme: only `http` and `https`. Raise `ValueError` immediately on
  anything else (caller catches and turns into a `MatchResult` with `notes="bad-scheme"`).
- robots.txt: build the robots URL from the target's scheme+host, fetch with the
  same client (with a tiny budget — 1s connect, 2s read; failures are treated as
  "no robots.txt = allowed"). Use `urllib.robotparser.RobotFileParser`.
- If robots disallows the homepage path for our user agent, return a snapshot with
  `notes="robots-disallowed"` and no fetched bytes.
- Otherwise: fetch the homepage (capped to `max_bytes_per_asset`), then iterate
  `candidate_paths` (deduplicated, joined onto the same origin). Stop at
  `max_assets_per_target`.
- Each fetched asset becomes a `FetchedAsset(url, sha256, byte_size, truncated, status)`.
- `TargetSnapshot` is a frozen dataclass with: `target_url`, `fetched_at`,
  `homepage_html: bytes` (or `b""`), `fetched_assets: tuple[FetchedAsset, ...]`,
  `notes: str`.
- All tests use `httpx.MockTransport`. Cover: happy path, robots disallow, oversize
  asset truncation, redirect chain (max 3 redirects), 404 homepage, scheme
  rejection.

**Validation:**
```bash
python -m pytest tests/test_fingerprint_web_probe.py -v
```

### Task 5: Matchers and scoring
**Goal:** Convert `(RepoFingerprint, TargetSnapshot)` into ranked `MatchResult`.
**Files:** `fingerprint/matchers/*.py`, `fingerprint/scoring.py`,
`tests/test_fingerprint_matchers.py`, `tests/test_fingerprint_scoring.py`.
**Details:**
- `asset_hash.match(repo, snapshot) -> list[MatchSignal]`: for each
  `AssetFingerprint`, scan `snapshot.fetched_assets` for an equal sha256. Favicon
  matches get weight `high`; other assets get weight `medium`.
- `html_regex.match(repo, snapshot) -> list[MatchSignal]`: for each `HtmlSignature`,
  apply to `snapshot.homepage_html.decode("utf-8", errors="replace")`. Bound regex
  execution with a compile-time check (signature regexes are validated when
  loading the fingerprint; reject anything containing nested quantifiers).
- `scoring.score_signals(signals) -> float`:
  - weight values: `high=0.45`, `medium=0.20`, `low=0.05`.
  - `score = min(1.0, sum(weights))`.
  - `band_for_score`: `<0.3 weak`, `<0.6 plausible`, otherwise `strong`.
  - Tested directly with hand-crafted signal lists at every band boundary.

**Validation:**
```bash
python -m pytest tests/test_fingerprint_matchers.py tests/test_fingerprint_scoring.py -v
```

### Task 6: Match CLI and report
**Goal:** End-to-end match against a target with JSON + Markdown output.
**Files:** `fingerprint/run_match.py`, `fingerprint/report.py`,
`tests/test_fingerprint_report.py`.
**Pattern:** `scanner/run_scan.py` + `scanner/report.py` for the writer style.
**Details:**
- `run_match.py` argparse: `--target <url>` (required), `--db-dir <path>`,
  `--report-dir <path>`, `--min-score <float>` (defaults to 0.0; below this the
  candidate is omitted from the Markdown but still present in JSON).
- Report file naming: `match_<host>_<UTC-YYYYMMDD-HHMMSS>.json` + `.md`. Host is
  sanitized to `[a-z0-9-]+`.
- Markdown writer always emits the disclaimer block at the top. Tested.
- JSON writer outputs `{"target": ..., "fetched_at": ..., "results": [MatchResult.to_dict(), ...], "notes": ...}`.
- CLI prints the two paths (mirror `scanner/run_scan.py`'s use of `print()`).
- Always exit 0; the partial-result discipline of the scanner module applies here
  too. A "no fingerprints in DB" condition is reported as an empty result with a
  helpful note, not an error.

**Validation:**
```bash
python -m pytest tests/test_fingerprint_report.py -v
python fingerprint/run_match.py --target https://example.com --db-dir fingerprint/db
```
(the second command requires Task 3 to have run at least once.)

### Task 7: Documentation, ADR, roadmap, runtime parity
**Goal:** Keep CLAUDE.md / AGENTS.md / ROADMAP / DECISIONS / README aligned with
the new module.
**Files:** `CLAUDE.md`, `AGENTS.md`, `ROADMAP.md`, `DECISIONS.md`, `README.md`.
**Details:**
- CLAUDE.md and AGENTS.md: add `fingerprint/` to **Key Directories**; add a
  **Fingerprint adapter contract** subsection that mirrors the **Scanner adapter
  contract** (extractors, runners, matchers, registry, no-raise discipline);
  add the gotchas listed in this PRP.
- ROADMAP.md: add `## Phase 4 — Template Fingerprinting` with the v0.1 checklist;
  mark complete with `(2026-05-14)` once tests pass.
- DECISIONS.md: add ADR-012 (Lite format) at the top:
  - Decision: probabilistic single-target fingerprinting via curated seeds.
  - Context: AI PatchLab needs to surface "this site looks like it was built from
    repo X" as a signal feeding future remediation work, without becoming a mass
    crawler or making attribution claims.
  - Consequences: indexer + matcher live under `fingerprint/`; no DB; no DOM
    parser; matches are ranked but never confirmed; expanding to multi-target or
    auto-discovery requires a new ADR.
- README.md: add a `## Web Template Fingerprinting (experimental)` section with
  setup, indexer command, match command, sample report path, robots.txt + caps
  callout, and a clear "this is a signal, not an attribution" line.

**Validation:**
```bash
rg "fingerprint" CLAUDE.md AGENTS.md README.md
rg "ADR-012|Phase 4 . Template Fingerprinting" DECISIONS.md ROADMAP.md
```

### Task 8: Full validation
**Goal:** Lint, format, tests, smoke run.
**Details:**
- Add `fingerprint` to the lint/format paths used in CLAUDE.md's `Common Commands`
  block (this is a doc-only change in `CLAUDE.md` and `AGENTS.md`).
- Smoke: index seeds, then match against `https://example.com` with mocked HTTPX
  (or a real run done manually and not in CI).

**Validation:**
```bash
ruff check scanner src tests fingerprint
python -m black --check scanner src tests fingerprint
python -m pytest tests/ -v
```

## Final Validation Loop

After ALL tasks complete, run in order:

```bash
# 1. Lint
ruff check scanner src tests fingerprint

# 2. Format check
python -m black --check scanner src tests fingerprint

# 3. Tests
python -m pytest tests/ -v

# 4. Indexer smoke (real network — manual, not in CI)
python fingerprint/run_index.py --rebuild

# 5. Match smoke (real network — manual, not in CI)
python fingerprint/run_match.py --target https://example.com
```

Fix ANY failures. Re-run until ALL pass.

## Success Criteria
- [ ] `fingerprint/` module exists with the file layout above and no new runtime
      dependencies in `pyproject.toml`.
- [ ] `RepoFingerprint`, `AssetFingerprint`, `HtmlSignature`, `MatchResult`, and
      `MatchSignal` are frozen dataclasses with `__post_init__` validation matching
      the contracts in this PRP.
- [ ] `fingerprint/seeds/repos.json` ships with 3 curated entries.
- [ ] Indexer can rebuild the local DB from the seed list using only
      `scanner/git_source.cloned_repo` for cloning.
- [ ] Match CLI accepts exactly one `--target` URL per invocation. No
      `--targets-file` flag exists.
- [ ] Web probe rejects non-http(s) schemes immediately.
- [ ] Web probe respects `robots.txt` for the configured `User-Agent` and records
      `notes="robots-disallowed"` when blocked.
- [ ] Web probe enforces both `max_bytes_per_asset` and `max_assets_per_target`.
- [ ] Report Markdown always begins with the disclaimer wording specified in the
      Critical Gotchas section, and tests assert the disclaimer is present even
      for empty result sets.
- [ ] Score banding (weak/plausible/strong) is computed by a single helper used by
      both writer and validator, and tested at every boundary.
- [ ] Tests use `httpx.MockTransport` (or `respx` if already in dev deps) — the
      test suite never opens a real socket.
- [ ] Tests use temp git repos (`tmp_path`) for the indexer, not real clones.
- [ ] Match CLI exits 0 even when the DB is empty, the target is unreachable, or
      robots disallows.
- [ ] CLAUDE.md and AGENTS.md both contain a `fingerprint/` entry under Key
      Directories and a Fingerprint adapter contract subsection.
- [ ] DECISIONS.md contains ADR-012.
- [ ] ROADMAP.md contains a Phase 4 Template Fingerprinting block, marked complete
      with `(2026-05-14)` after tests pass.
- [ ] README has a `Web Template Fingerprinting (experimental)` section with the
      setup, commands, output path, and the "signal, not attribution" line.
- [ ] No paid API, no AI provider, and no service besides the user-supplied target
      and the seeded git remotes is contacted at any point.
- [ ] All tests pass; no lint or format errors.

## PRP Quality Checklist
- [x] All referenced local files exist in the project (verified against current
      tree before writing).
- [x] Each task has at least one validation command.
- [x] Database changes are explicitly marked None.
- [x] Dependencies section filled.
- [x] Architecture clearly states what is OUT of scope (mass crawl, DOM parser, AI,
      auto-discovery, multi-target).
- [x] Confidence score >= 7.

## Confidence Score: 8/10
The architecture is straightforward (clone → extract → hash → fetch → match → score
→ report) and reuses existing patterns (git_source, frozen dataclasses, runner
shape, JSON+MD writer). The 2-point deduction reflects two real unknowns:
1. The HTML signature extractor heuristics may need tuning after the first real
   run against the seeds — false positives on common framework strings are likely.
2. The seeded repos themselves may not have stable `notable_paths` over time, so
   the matcher's hit rate will drift unless the seed list is maintained. This PRP
   accepts that drift as a manual-curation cost rather than building auto-update.
