# Project: ai-patchlab

> This file captures the Codex/OpenAI workflow for the project.
> It should stay aligned with `CLAUDE.md` when both runtimes are present.

## About
AI PatchLab is an AI-assisted security remediation toolkit. The MVP focuses on a local Python scanner that accepts a repository path, normalizes security findings from Semgrep, Gitleaks, Trivy, pip-audit, and an opt-in local AI review, and writes JSON plus Markdown reports for remediation planning.

## Runtime Parity
- Treat `INITIAL.md`, `PRPs/`, `ROADMAP.md`, `DECISIONS.md`, `README.md`, and `examples/` as shared sources of truth across runtimes
- If `CLAUDE.md` exists, keep it aligned with structural, dependency, and workflow changes made through Codex
- Prefer adding Codex behavior in `.agents/skills/` instead of changing Claude-specific files unless parity requires it

## Project Awareness & Context
- Always read `ROADMAP.md` at the start of a new conversation to understand the current state
- Check `DECISIONS.md` for past architectural decisions and context
- Check `PRPs/` for active or completed implementation plans
- Read `examples/` before implementing new features to match existing patterns
- Check `INITIAL.md` for the current feature requirements
- Use the `status` skill at the start of a session for a quick project snapshot

## Tech Stack
- Python 3.11+
- Local CLI scanner foundation (Semgrep, Gitleaks, Trivy, pip-audit, opt-in local AI review)
- JSON and Markdown report generation
- Data stack selected for repository analysis workflows
- MySQL 8.0 (aiomysql for async, available but not required in v0.1)
- Playwright (optional extra `[scraping]`, if scraping is needed later)
- Discord webhooks (alerts, optional later)
- Loguru (logging)
- pytest + pytest-asyncio + pytest-mock (testing)
- ruff + black (linting/formatting)
- httpx (async HTTP client)
- pydantic + pydantic-settings + python-dotenv (validation + config)
- Standard-library `subprocess` for external scanner runners (no remote endpoints)

## Key Directories
- `fingerprint/` - Web template fingerprinting (v0.1, experimental): seed loader, extractors, indexer CLI, web probe, matchers, scoring, JSON+MD match report. Local-first, single-target probe, probabilistic signal only.
- `fingerprint/models.py` - Frozen dataclasses (`RepoFingerprint`, `AssetFingerprint`, `HtmlSignature`, `MatchResult`, `MatchSignal`) and the canonical `band_for_score()` helper
- `fingerprint/config.py` - `FingerprintConfig` (pydantic-settings, `AI_PATCHLAB_FINGERPRINT_` env prefix)
- `fingerprint/git_seeds.py` - Loader + validator for `fingerprint/seeds/repos.json` + `slug_from_repo_url`
- `fingerprint/seeds/repos.json` - Curated seed list (committed; expand via PR only)
- `fingerprint/extractors/` - Pure functions over a cloned repo: `favicon.py`, `static_assets.py`, `html_signatures.py`
- `fingerprint/repo_index.py` - Clones via `scanner.git_source.cloned_repo`, runs extractors, writes `fingerprint/db/<slug>.json`
- `fingerprint/run_index.py` - CLI: `.venv/Scripts/python.exe fingerprint/run_index.py --rebuild` / `--repo-url <url>`
- `fingerprint/web_probe.py` - Sync `httpx.Client` probe with robots.txt respect, scheme allowlist, bytes/asset caps
- `fingerprint/matchers/` - `asset_hash.py`, `html_regex.py`; registered in `fingerprint/matchers/__init__.py:MATCHERS`
- `fingerprint/scoring.py` - Bounded weighted score (`WEIGHT_VALUES`); shared `band_for_score` helper from models
- `fingerprint/run_match.py` - CLI: `.venv/Scripts/python.exe fingerprint/run_match.py --target <url>` -> `reports/fingerprint/match_<host>_<UTC>.json` + `.md`
- `fingerprint/report.py` - JSON + Markdown writer; disclaimer block is mandatory
- `fingerprint/db/` - Per-repo fingerprint JSONs (gitignored except `.gitkeep`)
- `reports/fingerprint/` - Generated match reports
- `scanner/` - Scanner CLI, finding model, recommendation enrichment, report generation, scanner registry
- `scanner/run_scan.py` - CLI entry point (`.venv/Scripts/python.exe scanner/run_scan.py --repo <path>` or `--from-git-url <url>`)
- `scanner/git_source.py` - Shallow-clone a public git URL into a temp directory via the `cloned_repo` context manager; cleanup-on-exit, `shell=False`, no remote API calls
- `scanner/paths.py` - `rebase_finding_paths(findings, repo_root)` rewrites each finding's `file` (and `id` when it embeds the same path) to a repo-relative POSIX path so reports survive temp-dir cleanup
- `scanner/ignore.py` - `apply_ignore(findings, patterns)` + `load_ignore_patterns(path)` provide `.gitignore`-style path suppression (used by the `--ignore-file` CLI flag). Empty-file findings are never suppressed. `DEFAULT_SAMPLE_IGNORE_PATTERNS` holds demo/sample/example subtree patterns opted into via `--ignore-samples`
- `scanner/models.py` - Normalized `Finding` dataclass + severity/confidence enums + `FINDING_FIELDS`
- `scanner/recommendations.py` - Deterministic keyword-based recommendation enrichment
- `scanner/confidence.py` - Centralized `Finding.confidence` rules (one function per scanner + `confidence_for_meta_finding` for shared `not-installed` / `scan-error` / etc.)
- `scanner/report.py` - JSON + Markdown report writers (severity-grouped, "Top Findings" highlight block, patch suggestion blocks); also exposes `filter_by_min_severity` and `select_top_findings`
- `scanner/config.py` - Disabled-by-default AI review configuration loaded from environment / `.env` (`AI_PATCHLAB_*`)
- `scanner/remediation/` - Deterministic patch suggestion engine (`patch_suggestions.py`) for known vulnerability patterns
- `scanner/scanners/` - Scanner adapters (`semgrep.py`, `gitleaks.py`, `trivy.py`, `dependency_scan.py`, `ai_review.py`) plus `common.py` placeholder helper and `__init__.py` registry (`SCANNERS`)
- `scanner/tools/` - External scanner process runners (`semgrep_runner.py`, `gitleaks_runner.py`, `trivy_runner.py`, `pip_audit_runner.py`, `ai_review_runner.py`)
- `reports/` - Generated security reports (`security_report.json`, `security_report.md`)
- `reports/raw/` - Raw scanner JSON outputs (`semgrep.json`, `gitleaks.json`, `trivy.json`, `pip-audit.json`, `ai-review.json` when enabled)
- `src/` - Legacy scaffold entry point (kept for template parity)
- `src/main.py` - Legacy entry point (`python -m src.main`) - currently a loguru-wired async stub with TODOs
- `.github/workflows/ci.yml` - CI: ruff + black + pytest on Python 3.11 and 3.13
- `reports/disclosures/` - Drafted private disclosure emails awaiting a manual send (gitignored)
- `tests/` - pytest tests (one module per scanner: `test_scanner_foundation.py`, `test_semgrep_scanner.py`, `test_gitleaks_scanner.py`, `test_trivy_scanner.py`, `test_dependency_scan.py`, `test_ai_review.py`, `test_patch_suggestions.py`, `test_recommendations.py`, `test_meta_findings.py`, `test_confidence_field_rules.py`)
- `tests/conftest.py` - Shared fixtures (`mock_db`, `mock_http_client`, `mock_discord`, `test_config`, session `event_loop`)
- `examples/` - Reference patterns to read before implementing
- `PRPs/` - Active Product Requirements Prompts
- `PRPs/done/` - Archived PRPs (`2026-05-12-trivy-integration.md`, `20260513-phase-3-ai-review-behavior.md`)
- `PRPs/templates/` - Reusable PRP templates (`prp_base.md`)
- `docs/` - GitHub Pages site (Jekyll, theme `cayman`): `_config.yml`, `index.md` (landing + scan log), `scans/` (per-scan write-ups), `templates/scan-post.md` (template, excluded from publish)
- `logs/` - Log files (gitignored except `.gitkeep`)
- `.agents/skills/` - Codex skills for repeatable workflows
- `.claude/` - Claude runtime files (commands, agents, pipelines), if present

## Codex Skills
- `ez-project-workflow` - Core EzProject operating rules for any coding task
- `kickoff` - Interview flow that updates `INITIAL.md` and project docs
- `generate-prp` - Build a self-contained PRP from a feature spec (with optional Understanding Lock for ambiguous specs)
- `execute-prp` - Implement a PRP end to end with validation and housekeeping
- `fix-issue` - Diagnose, fix, test, review, and commit a bug end-to-end
- `pipeline` - Execute a YAML-defined workflow step by step (feature, bugfix, security, release, custom)
- `tdd` - Strict Red-Green-Refactor implementation (Iron Law: no production code without an observed-failing test)
- `review-code` - Review the current diff or target files
- `refactor` - Analyze code smells and execute selected refactorings with per-change validation
- `retrospective` - Self-healing retrospective in a fresh context after `execute-prp` (lite mode) or sprint-wide (no arg)
- `next` - Read project state and recommend the 1-3 best next actions
- `upgrade-status` - Compare project to latest template; list features not yet adopted
- `status` - Produce a compact project status snapshot
- `audit-project` - Audit runtime docs and project scaffolding
- `housekeeping` - Sync docs and remove temporary artifacts
- `cleanup` - Identify dead code via import-graph trace; report and ask before deleting
- `security-scan` - OWASP top 10 + secrets + vulnerable deps audit
- `dependency-check` - Vulnerabilities, outdated packages, compatibility audit; optional safe auto-update
- `performance` - Static hot-path scan + optional runtime profiling
- `document` - Auto-generate docs from code (API ref, data dict, architecture, modules)
- `monitor-setup` - Health check endpoint + alerting + uptime tracking adapted to stack
- `rollback` - Safe git rollback (always revert + stash, never reset --hard)
- `create-skill` - Scaffold a new Codex skill for the project
- `daily` - Autonomous daily scan-and-disclose pipeline (status sweep -> candidate discovery -> one scan -> curation -> gated publication). Full-auto per the 2026-05-28 decision; guardrails: 1 scan/day, quality gate on issue/PR filing, strict-norm detection, kill switch `.daily-paused`

## Claude-only commands (no Codex skill mirror)
These Claude slash commands are intentionally not mirrored on the Codex side. Listed in `tests/template/test_codex_parity.py` as `KNOWN_EXCEPTIONS`.

- `/do` (smart-router) - natural-language intent routing requires a Claude-side primitive that Codex doesn't expose; the pattern table at `.claude/commands/smart-router.md` is Claude-only.
- `/idea-to-pr` - end-to-end idea -> PR flow requires PR/branching orchestration that's tightly coupled to Claude's tool layer.
- `/upgrade-to-project` - one-shot MVP -> Project upgrade; the equivalent on the Codex side is to invoke `ez-upgrade-project.ps1` directly.

## Common Commands
```bash
# Dev
.venv/Scripts/python.exe scanner/run_scan.py --repo "C:\path\to\repo"
.venv/Scripts/python.exe scanner/run_scan.py --repo "." --reports-dir reports
python -m src.main
.venv/Scripts/python.exe -m pytest tests/ -v
.venv/Scripts/python.exe -m pytest tests/ -v -k "test_name"

# Lint & Format
.venv/Scripts/ruff.exe check scanner src/ tests/ fingerprint/
.venv/Scripts/ruff.exe check scanner src/ tests/ fingerprint/ --fix
.venv/Scripts/python.exe -m black scanner src/ tests/ fingerprint/

# Web template fingerprinting (experimental)
.venv/Scripts/python.exe fingerprint/run_index.py --rebuild                      # Rebuild local DB from seed list
.venv/Scripts/python.exe fingerprint/run_match.py --target https://example.com   # Probe a single live URL

# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install -e ".[scraping]"   # Optional Playwright extra
cp .env.example .env

# External scanners (install separately, must be on PATH)
semgrep --version
gitleaks version
trivy --version
.venv/Scripts/python.exe -m pip install pip-audit && pip-audit --version

# Optional AI review (disabled by default - see scanner/config.py)
export AI_PATCHLAB_AI_REVIEW_ENABLED=true
export AI_PATCHLAB_AI_REVIEW_PROVIDER=local_command
export AI_PATCHLAB_AI_REVIEW_COMMAND=/path/to/ai-review-wrapper
```

## MCP Servers
- `memory` - Session persistence when configured
- `mysql` - Direct database access through MCP when `MYSQL_DSN` is configured

## Coding Standards

### Python
- Type hints REQUIRED on all functions
- Google-style docstrings on public functions
- Max ~300 lines per file (note: `scanner/remediation/patch_suggestions.py` is ~280 lines)
- English identifiers; French comments are fine
- Use `async/await` where appropriate; the scanner core is synchronous on purpose because it shells out via `subprocess.run`
- Use loguru, never `print()` in production code (exception: `scanner/run_scan.py` prints report paths to stdout as the CLI surface)
- Config via `.env` / `AI_PATCHLAB_*` env vars; never hardcode secrets
- Use `pathlib.Path` for filesystem paths
- Use `pydantic` for env-loaded config; use `@dataclass(frozen=True)` for internal normalized records (`Finding`, `*Result`)
- External scanner subprocesses MUST use `shell=False` and an explicit argv list

### Scanner adapter contract
- Each scanner in `scanner/scanners/` exposes one `scan_<name>(repo_path: Path, reports_dir: Path) -> list[Finding]` function and is registered in `scanner/scanners/__init__.py:SCANNERS`
- Scanners must never raise on a missing or failing external tool - emit a normalized `info` finding instead so the report still completes
- Each adapter pipes its findings through `apply_patch_suggestions(enrich_findings(...))` before returning
- Any finding built with `confidence_for_meta_finding(...)` must also set `is_meta=True` so `--min-severity` cannot drop it
- Each external tool runner lives in `scanner/tools/<tool>_runner.py`, returns a frozen `*Result` dataclass, writes raw JSON to `reports/raw/<tool>.json`, and uses `subprocess.run(..., shell=False, check=False)` with captured stdout/stderr
- Do not call subprocesses directly from `scanner/scanners/*` - go through the runner module
- `Finding.confidence` values come from `scanner/confidence.py` - never inline `confidence="high"` / `"medium"` / `"low"` in a scanner adapter; add or reuse a rule function instead

### Fingerprint adapter contract
- Extractors in `fingerprint/extractors/` are pure functions over a cloned repo path (and the active `FingerprintConfig`). No subprocess, no network, no raise on missing files.
- Matchers in `fingerprint/matchers/` take `(RepoFingerprint, TargetSnapshot)` and return `list[MatchSignal]`. Registered in `fingerprint/matchers/__init__.py:MATCHERS`. A mismatch is the empty list.
- The indexer (`fingerprint/repo_index.py:index_seed`) is the only place that performs a git clone; it goes through `scanner.git_source.cloned_repo`.
- The web probe (`fingerprint/web_probe.py:fetch_target`) is the only place that makes outbound HTTP requests. Scheme allowlist: `http`/`https`. Honours `robots.txt` and hard byte/asset caps.
- The match CLI (`fingerprint/run_match.py`) always exits 0 (partial-result discipline). Empty DB, unreachable target, bad scheme, robots-disallowed all still produce a valid report.
- The Markdown report ALWAYS includes the `DISCLAIMER` block and never uses attribution words ("confirmed", "proven", "stolen", "copied") - tested in `tests/test_fingerprint_report.py`.
- Score banding goes through `band_for_score()` in `fingerprint/models.py` - single source of truth used by validator and writer.
- The seed list `fingerprint/seeds/repos.json` is curated. Adding a new entry is a human PR - never auto-discover via the GitHub API.

## Database Conventions
- MySQL tables in `snake_case`
- Always include `id`, `created_at`, and `updated_at`
- Index frequently queried columns
- Append migrations to `docs/schema.sql` with a dated comment (file not yet created - `docs/` is empty)
- Use parameterized queries only

## Error Handling
- Wrap external calls in `try/except`
- Log errors with context using loguru
- Use retries with backoff for network calls when needed
- Never silently suppress errors
- Use custom exception classes for domain-specific failures
- Scanner runners catch `OSError` and `subprocess.TimeoutExpired`, write a safe empty raw JSON, and return a structured `*Result` instead of propagating

## Testing
- Use pytest for all tests (`pytest-asyncio` mode is `auto` per `pyproject.toml`)
- Mock external calls (API, DB, subprocess) in unit tests
- Cover critical calculation and workflow paths
- Use `pytest-asyncio` for async tests
- Available markers: `slow`, `integration`
- Each scanner adapter has a dedicated `tests/test_<scanner>.py` module

## Git Workflow
- Create a branch per feature
- Use descriptive English commit messages
- Format commits as `type: description`
- Never commit directly to `main`
- Run validation before committing

## Roadmap Management
- Always check `ROADMAP.md` first
- Progression: `[ ]` todo -> `[-]` in progress -> `[x]` done
- Add a `YYYY/MM/DD` timestamp when status changes
- Update `ROADMAP.md` after completing each meaningful task

## Architecture Decisions
- Log architectural decisions in `DECISIONS.md`
- Check existing ADRs before making structural changes
- Record date, decision, context, and consequences
- Current ADRs of record: ADR-001 scaffold, ADR-002 data stack, ADR-003 placeholder adapters, ADR-004 Gitleaks, ADR-005 Semgrep, ADR-006 recommendation enrichment, ADR-007 patch suggestions, ADR-008 Trivy, ADR-009 pip-audit, ADR-010 disabled-by-default AI review boundary, ADR-011 centralized scanner confidence rules, ADR-012 probabilistic web template fingerprinting boundary, ADR-013 meta findings exempt from severity filtering, ADR-014 field-derived confidence tiers

## Known Gotchas
- Semgrep is a **Python program on the shared user-site interpreter**, not a standalone binary like gitleaks/trivy. Anything that breaks that interpreter breaks Semgrep too — a pydantic downgrade on 2026-08-20 made `semgrep --version` raise ImportError and every scan would have silently lost 52% of its coverage. The project `.venv` does NOT protect it. Check `semgrep --version` before trusting a scan; repair with `python -m pip install --user --upgrade "pydantic>=2.11" "httpx>=0.27"`
- ALWAYS run through `.venv` (`.venv/Scripts/python.exe` on Windows). The project ran three months off the shared user-site; on 2026-08-20 an unrelated `pip install` downgraded pydantic to 1.x and httpx to 0.21 and every import broke, hours after a scan had passed
- Meta findings survive `--min-severity` but are NOT yet exempt from `--ignore-file` suppression
- Semgrep coverage comes from the `errors` array, never `paths.skipped` - `skipped` has been empty on every series run where rules timed out. `scan_semgrep` emits `semgrep-partial-coverage` naming each `rule -> file` pair that did not run
- `ai-patchlab` and `2026-05-12` are template placeholders replaced during scaffolding
- `aiomysql` pools must be closed explicitly with `await db.disconnect()` in `finally`
- Playwright `networkidle` can time out on SPAs; use `domcontentloaded` when needed
- Discord webhooks: 30 messages/minute rate limit per webhook
- pydantic-settings: `.env` variables are case-insensitive by default
- MCP MySQL DSNs require URL-encoding for special characters in passwords
- cPanel MySQL DB and user names are prefixed (e.g. `cpaneluser_dbname`) - don't forget the prefix
- AI review must remain disabled by default and local-first. Never add a default remote provider, default endpoint, default model, or default token variable. Any future remote/paid provider requires explicit configuration and a new ADR.
- Scanner subprocess invocations MUST use `shell=False` and an explicit argv list - `shell=True` is the exact anti-pattern the patch engine warns about (see `scanner/remediation/patch_suggestions.py:SUBPROCESS_SHELL_SUGGESTION`)
- Semgrep on Windows: when not on `PATH`, the runner falls back to `Path.home() / AppData/Roaming/Python/Python313/Scripts/semgrep.exe` (see `scanner/tools/semgrep_runner.py:PIP_USER_SEMGREP_PATH`). The Python minor version is hardcoded - if the user installs under a different Python version, the runner will silently skip Semgrep until the constant is updated
- Semgrep UTF-8 output (Windows, 2026-06-11 fix): Semgrep writes its `--output` JSON via Python's default codec (cp1252 on Windows). A repo with non-Latin-1 source (Chinese/Japanese/Korean/emoji) crashes Semgrep mid-write with `UnicodeEncodeError`, leaving a 0-byte report + exit 2. `_build_semgrep_env` forces `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`; `scan_semgrep` treats an empty report as a `semgrep-scan-error`. The scan-error is `info` severity, so `--min-severity medium` still filters it (RESOLVED 2026-08-21: meta findings carry `is_meta=True` and are exempt from `--min-severity`)
- All external scanners are optional - if a tool is missing, the adapter emits a normalized `info` finding (`semgrep-not-installed`, `gitleaks-not-installed`, `trivy-not-installed`, `pip-audit-not-installed`, `ai-review-disabled`) instead of failing
- pip-audit input resolution order: root `requirements*.txt` first, then `pylock.*.toml` (with `--locked`), then `pyproject.toml`
- AI review timeouts default to 120s (`AI_PATCHLAB_AI_REVIEW_TIMEOUT_SECONDS`); on timeout the runner writes `[]` to `reports/raw/ai-review.json` and emits a normalized error finding so the report still completes
- Fingerprint web probe respects `robots.txt`. `urllib.robotparser` splits the live user-agent on `/` before matching, so a robots.txt block for `ai-patchlab-fingerprint/0.1` is matched as `ai-patchlab-fingerprint` (drop the version when authoring rules)
- Fingerprint matching is a SIGNAL, not an attribution. The Markdown report keeps the `DISCLAIMER` block and never claims a match is "confirmed", "proven", "stolen", or "copied" - blocked by a regression test
- The fingerprint CLI accepts exactly one `--target` per invocation. No `--targets-file` flag exists by design - multi-target scanning requires a new ADR
- Fingerprinting must not add DOM-parser dependencies (`beautifulsoup4`, `lxml`) or browser stacks (`playwright`, `selenium`). v0.1 stays on `re` + `hashlib` + `httpx` only

## Important Rules
- Keep things simple - MVP first
- Read `examples/` before inventing new patterns
- Validate each step before moving on
- Do not over-engineer
- Log meaningful architecture decisions in `DECISIONS.md`

## Self-Healing Layer (AI-layer evolution)
When an implementation is painful, fix the underlying AI layer - not just the code. The AI layer is `CLAUDE.md`, `AGENTS.md`, `examples/`, `.claude/commands/`, `.claude/agents/`, `.claude/pipelines/`, `.agents/skills/`, PRP templates.

- Never review the implementer's work in the same context that produced it (writer is biased about its own output)
- After `execute-prp`, in a NEW session, run the `retrospective` skill with the PRP name (lite mode) to surface AI-layer drift and propose concrete file edits
- Apply the proposed edits only after the user approves
- Periodically run `retrospective` with no argument for a broader sprint review

## Automatic Housekeeping
- After any feature or fix, update `ROADMAP.md`
- After structural changes, update `AGENTS.md`
- If `CLAUDE.md` exists, update the matching sections there too
- If new setup steps or commands were added, update `README.md`
- After completing a PRP, move it to `PRPs/done/` with a date prefix
- Delete scratch files and obvious temporary artifacts when done
- Never leave documentation out of sync with the code
