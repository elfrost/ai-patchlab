# Project: ai-patchlab

> Ce fichier est lu automatiquement par Claude Code au début de chaque session.
> Il définit les règles, standards et contexte du projet.

## About
AI PatchLab is an AI-assisted security remediation toolkit. The MVP focuses on a local Python scanner that accepts a repository path, normalizes security findings, and writes JSON plus Markdown reports for remediation planning.
This project can optionally include a parallel Codex/OpenAI runtime via `AGENTS.md` and `.agents/skills/`.

## Project Awareness & Context
- Always read ROADMAP.md at the start of a new conversation to understand the current state
- Check DECISIONS.md for past architectural decisions and context
- Check PRPs/ folder for any existing implementation plans
- Read examples/ before implementing new features to match existing patterns
- Check INITIAL.md for the current feature requirements
- Run `/status` at the start of a session for a quick project snapshot

## Tech Stack
- Python 3.11+
- Local CLI scanner foundation (Semgrep, Gitleaks, Trivy, pip-audit, opt-in local AI review)
- JSON and Markdown report generation
- Data stack selected for repository analysis workflows
- MySQL 8.0 (aiomysql for async, available but not required in v0.1)
- Playwright (optional extra `[scraping]`, si scraping requis plus tard)
- Discord webhooks (alertes optionnelles plus tard)
- Loguru (logging)
- pytest + pytest-asyncio + pytest-mock (testing)
- ruff + black (linting/formatting)
- httpx (async HTTP client)
- pydantic + pydantic-settings + python-dotenv (validation + config)
- Standard-library `subprocess` for external scanner runners (no remote endpoints)

## Key Directories
- `fingerprint/` — Web template fingerprinting (v0.1, experimental): seed loader, extractors, indexer CLI, web probe, matchers, scoring, JSON+MD match report. Local-first, single-target probe, probabilistic signal only.
- `fingerprint/models.py` — Frozen dataclasses (`RepoFingerprint`, `AssetFingerprint`, `HtmlSignature`, `MatchResult`, `MatchSignal`) and the canonical `band_for_score()` helper used by writer and validator
- `fingerprint/config.py` — `FingerprintConfig` (pydantic-settings, `AI_PATCHLAB_FINGERPRINT_` env prefix): bytes cap per asset, asset cap per target, timeouts, user agent
- `fingerprint/git_seeds.py` — Loader + validator for `fingerprint/seeds/repos.json` + deterministic `slug_from_repo_url`
- `fingerprint/seeds/repos.json` — Curated seed list (committed; expand via PR only)
- `fingerprint/extractors/` — Pure functions over a cloned repo: `favicon.py`, `static_assets.py`, `html_signatures.py`
- `fingerprint/repo_index.py` — Clones a seed via `scanner.git_source.cloned_repo`, runs extractors, writes `fingerprint/db/<slug>.json`
- `fingerprint/run_index.py` — CLI: `.venv/Scripts/python.exe fingerprint/run_index.py --rebuild` / `--repo-url <url>`
- `fingerprint/web_probe.py` — Sync `httpx.Client` probe with robots.txt respect, scheme allowlist, hard bytes/asset caps; optional `transport=` param for tests
- `fingerprint/matchers/` — `asset_hash.py`, `html_regex.py`; registered in `fingerprint/matchers/__init__.py:MATCHERS`
- `fingerprint/scoring.py` — Bounded weighted score (`WEIGHT_VALUES`) — single source of truth, tested directly
- `fingerprint/run_match.py` — CLI: `.venv/Scripts/python.exe fingerprint/run_match.py --target <url>` → writes `reports/fingerprint/match_<host>_<UTC>.json` + `.md`; always exits 0
- `fingerprint/report.py` — JSON + Markdown writer for match results; disclaimer block is mandatory
- `fingerprint/db/` — Per-repo fingerprint JSONs (gitignored except `.gitkeep`; regenerable from seeds)
- `reports/fingerprint/` — Generated match reports
- `scanner/` — Scanner CLI, finding model, recommendation enrichment, report generation, scanner registry
- `scanner/run_scan.py` — CLI entry point (`.venv/Scripts/python.exe scanner/run_scan.py --repo <path>` or `--from-git-url <url>`)
- `scanner/git_source.py` — Shallow-clone a public git URL into a temp directory via the `cloned_repo` context manager; cleanup-on-exit, `shell=False`, no remote API calls
- `scanner/paths.py` — `rebase_finding_paths(findings, repo_root)` rewrites each finding's `file` (and `id` when it embeds the same path) to a repo-relative POSIX path so reports survive temp-dir cleanup
- `scanner/ignore.py` — `apply_ignore(findings, patterns)` + `load_ignore_patterns(path)` provide `.gitignore`-style path suppression of findings (used by the `--ignore-file` CLI flag). Empty-file findings are never suppressed. `DEFAULT_SAMPLE_IGNORE_PATTERNS` holds the demo/sample/example subtree patterns opted into via the `--ignore-samples` flag
- `scanner/models.py` — Normalized `Finding` dataclass + severity/confidence enums + `FINDING_FIELDS`; `Finding.is_meta` flags scanner-infrastructure findings that `--min-severity` must never drop
- `scanner/recommendations.py` — Deterministic keyword-based recommendation enrichment
- `scanner/confidence.py` — Centralized `Finding.confidence` rules (one function per scanner + `confidence_for_meta_finding` for shared `not-installed` / `scan-error` / etc.)
- `scanner/report.py` — JSON + Markdown report writers (severity-grouped, "Top Findings" highlight block, patch suggestion blocks); also exposes `filter_by_min_severity` and `select_top_findings`
- `scanner/config.py` — Disabled-by-default AI review configuration loaded from environment / `.env` (`AI_PATCHLAB_*`)
- `scanner/remediation/` — Deterministic patch suggestion engine (`patch_suggestions.py`) for known vulnerability patterns
- `scanner/scanners/` — Scanner adapters: `semgrep.py`, `gitleaks.py`, `trivy.py`, `dependency_scan.py`, `ai_review.py`, plus `common.py` placeholder helper and `__init__.py` registry (`SCANNERS`)
- `scanner/tools/` — External scanner process runners: `semgrep_runner.py`, `gitleaks_runner.py`, `trivy_runner.py`, `pip_audit_runner.py`, `ai_review_runner.py`
- `reports/` — Generated security reports (`security_report.json`, `security_report.md`)
- `reports/raw/` — Raw scanner JSON outputs (`semgrep.json`, `gitleaks.json`, `trivy.json`, `pip-audit.json`, `ai-review.json` when enabled)
- `src/` — Legacy scaffold entry point (kept for template parity)
- `src/main.py` — Legacy point d'entrée (`python -m src.main`) — currently a loguru-wired async stub with TODOs
- `.github/workflows/ci.yml` — CI: ruff + black + pytest on Python 3.11 and 3.13 (the 3.13 leg catches stdlib removals such as PEP 594 dropping `cgi`)
- `reports/disclosures/` — Drafted private disclosure emails awaiting a manual send (gitignored with the rest of `reports/`)
- `tests/` — Tests pytest (`test_scanner_foundation.py`, `test_semgrep_scanner.py`, `test_gitleaks_scanner.py`, `test_trivy_scanner.py`, `test_dependency_scan.py`, `test_ai_review.py`, `test_patch_suggestions.py`, `test_recommendations.py`, `test_meta_findings.py`, `test_confidence_field_rules.py`)
- `tests/conftest.py` — Fixtures partagées (`mock_db`, `mock_http_client`, `mock_discord`, `test_config`, session `event_loop`)
- `examples/` — Code de référence — LIRE AVANT D'IMPLÉMENTER (api_client, config, discord_alert, mysql, playwright_scraper, scheduler, service)
- `PRPs/` — Product Requirements Prompts (actifs)
- `PRPs/done/` — PRPs complétés (archive — `2026-05-12-trivy-integration.md`, `20260513-phase-3-ai-review-behavior.md`)
- `PRPs/templates/` — Templates PRP réutilisables (`prp_base.md`)
- `docs/` — GitHub Pages site (Jekyll, theme `cayman`): `_config.yml`, `index.md` (landing: intro, six featured scans, compact 83-row table), `scan-log.md` (full prose archive of every scan entry), `scans/` (per-scan write-ups), top-level pages (`work-with-me.md` conversion funnel, `daybreak-and-local-first.md` positioning essay vs OpenAI Daybreak), `templates/scan-post.md` (template, excluded from publish)
- `logs/` — Log files (gitignored except .gitkeep)
- `AGENTS.md` — Codex/OpenAI runtime instructions (kept in parity with this file)
- `.agents/skills/` — Codex skills for repeatable workflows (one folder per skill — kickoff, generate-prp, execute-prp, fix-issue, pipeline, tdd, review-code, refactor, retrospective, next, upgrade-status, status, audit-project, housekeeping, cleanup, security-scan, dependency-check, performance, document, monitor-setup, rollback, create-skill, daily, ez-project-workflow)
- `.claude/commands/` — Claude slash command definitions (one Markdown file per command)
- `.claude/agents/` — Claude subagent definitions (architect, code-reviewer, debugger, dependency-manager, documentation-writer, integration-tester, orchestrator, performance-profiler, refactorer, release-manager, researcher, security-auditor, smart-context, tester)
- `.claude/pipelines/` — Reusable pipeline YAML definitions (`feature.yml`, `bugfix.yml`, `security.yml`, `release.yml`)

## Coding Standards

### Python
- Type hints REQUIRED on all functions
- Docstrings Google-style on public functions
- Files max 300 lines — split if bigger (note: `scanner/remediation/patch_suggestions.py` is ~280 lines and approaching the limit)
- Variable/function names in English
- Comments OK in French
- Use `async/await` for all I/O when async is appropriate (the scanner core is synchronous on purpose because it shells out via `subprocess.run`; `src/main.py` and DB code use async)
- Logging with `loguru` — never use print() in production code (note: `scanner/run_scan.py` uses `print()` only to emit CLI report paths; this is intentional for the local CLI surface)
- Config via `.env` files / `AI_PATCHLAB_*` env vars — never hardcode secrets (see `examples/config_pattern.py` and `scanner/config.py`)
- Use `pathlib.Path` for file paths
- Use `pydantic` models for data validation (config); use `@dataclass(frozen=True)` for internal normalized records (e.g. `Finding`)
- Always run external scanner subprocesses with `shell=False` and an explicit argv list

### File Structure
- One class per file for major components
- Group related functions in modules
- `__init__.py` should only contain imports (the `scanner/scanners/__init__.py` registry tuple `SCANNERS` is the canonical pattern for scanner registration)
- Keep utils genuinely generic

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: prefix with `_`

### Scanner adapter contract
- Each scanner in `scanner/scanners/` exposes one `scan_<name>(repo_path: Path, reports_dir: Path) -> list[Finding]` function and is registered in `scanner/scanners/__init__.py:SCANNERS`
- Scanners must never raise on a missing or failing external tool — emit a normalized `info` finding instead so the report still completes
- Each adapter pipes its findings through `apply_patch_suggestions(enrich_findings(...))` before returning
- Each external tool runner lives in `scanner/tools/<tool>_runner.py`, returns a frozen `*Result` dataclass, writes the raw JSON to `reports/raw/<tool>.json`, and uses `subprocess.run(..., shell=False, check=False)` with captured stdout/stderr
- New scanners must follow the same registry + runner split — do not call subprocesses directly from `scanner/scanners/*`
- Any finding built with `confidence_for_meta_finding(...)` must also set `is_meta=True` so `--min-severity` cannot drop it
- `Finding.confidence` values come from `scanner/confidence.py` — never inline `confidence="high"` / `"medium"` / `"low"` in a scanner adapter; add or reuse a rule function instead

### Fingerprint adapter contract
- Extractors in `fingerprint/extractors/` are pure functions over a cloned repo path (and the active `FingerprintConfig` when bytes caps matter). They never call subprocess, never reach the network, and never raise on a missing file — they return `None` or an empty tuple.
- Matchers in `fingerprint/matchers/` take a `(RepoFingerprint, TargetSnapshot)` pair and return `list[MatchSignal]`. They are registered in `fingerprint/matchers/__init__.py:MATCHERS`. A mismatch is the empty list, not an exception.
- The indexer (`fingerprint/repo_index.py:index_seed`) is the only place that performs a git clone in this module. It clones through `scanner.git_source.cloned_repo` — never re-implement cloning.
- The web probe (`fingerprint/web_probe.py:fetch_target`) is the only place that makes outbound HTTP requests. Scheme allowlist is `http`/`https` only; `robots.txt` is honoured before any other fetch; bytes per asset and total assets per target are hard-capped.
- The match CLI (`fingerprint/run_match.py`) always exits 0 (partial-result discipline). An empty DB, an unreachable target, a bad scheme, and a robots disallow all produce a valid JSON + Markdown report with the appropriate `notes` value.
- The Markdown report ALWAYS includes the disclaimer (`fingerprint/report.py:DISCLAIMER`). Tests assert the disclaimer is present even for empty result sets, and that attribution words ("confirmed", "proven", "stolen", "copied") never appear.
- Score banding goes through `band_for_score()` in `fingerprint/models.py` — single source of truth for both the validator (`MatchResult.__post_init__`) and the writer.
- Seed list (`fingerprint/seeds/repos.json`) is curated and committed. Adding a new entry is a human PR — never auto-discover repos via the GitHub API.

## Slash Commands (Claude Code)
```
/kickoff              — Interview interactive → génère INITIAL.md
/generate-prp FILE    — Recherche + génère un PRP d'implémentation
/execute-prp FILE     — Exécute un PRP (implémente la feature)
/review-code          — Code review automatisée
/status               — Snapshot rapide de l'état du projet
/next                 — Suggère les 1-3 prochaines actions selon l'état actuel du projet
/upgrade-status       — Compare le projet au template courant; liste les features manquantes
/audit-project        — Audit du CLAUDE.md
/cleanup              — Analyse de dead code
/housekeeping         — Mise à jour docs post-implémentation
/rollback             — Rollback sécuritaire des changements
/retrospective [PRP]  — Rétrospective: vide=sprint 2 semaines, "last" ou nom de PRP=self-healing per-PRP en contexte frais
/create-skill DESC    — Génère un nouveau skill (command + agent) à partir d'une description
/upgrade-to-project   — Upgrade MVP vers Project mode (orchestrator + extended phases)
/security-scan [PATH] — Full security audit: secrets, deps vulnérables, OWASP patterns
/refactor [PATH]      — Analyse code smells + complexité, refactoring ciblé avec validation
/fix-issue DESC       — End-to-end: diagnose -> fix -> test -> review -> commit
/idea-to-pr DESC      — End-to-end: idea -> research -> design -> implement -> test -> review -> PR
/pipeline NAME [DESC] — Execute un pipeline (feature, bugfix, security, release, ou custom)
/dependency-check     — Audit dependances: vulnerabilites, updates, compatibilite
/do DESC              — Smart router (file: `smart-router.md`): décris ce que tu veux → route vers la bonne action
/document [SCOPE]     — Auto-génère la documentation (api, data, architecture, modules, all)
/performance [PATH]   — Profile le code, identifie bottlenecks et optimisations
/monitor-setup [TYPE] — Configure health checks, alerting, uptime (health, alerts, uptime, all)
/tdd DESC             — Implémentation Red-Green-Refactor stricte (Iron Law: pas de code sans test failing observé)
/daily [MODE]         — Pipeline autonome quotidien scan→curation→post→issue→PR (MODE: vide=autonome, --dry-run, --status-only). Garde-fous: 1 scan/jour, quality-gate sur dépôt d'issue, détection strict-norm, kill switch `.daily-paused`
```

## Claude Subagents (`.claude/agents/`)
Use the Task tool with the matching `subagent_type` to delegate a focused job:
- `architect` — high-impact design decisions (output an ADR)
- `code-reviewer` — diff-level review
- `debugger` — failure reproduction and root-cause
- `dependency-manager` — dependency upgrades and audits
- `documentation-writer` — generate or refresh docs
- `integration-tester` — end-to-end / integration test design
- `orchestrator` — multi-phase Project-mode workflows
- `performance-profiler` — profiling and hot-path analysis
- `refactorer` — code-smell and refactor planning
- `release-manager` — release checklist execution
- `researcher` — codebase / external research
- `security-auditor` — security review (used by `/security-scan`)
- `smart-context` — keeps this file aligned with reality (used by `/audit-project`)
- `tester` — unit test design and execution

## Codex Skills (`.agents/skills/`)
Mirror of slash commands for the Codex runtime: kickoff, generate-prp, execute-prp, fix-issue, pipeline, tdd, review-code, refactor, retrospective, next, upgrade-status, status, audit-project, housekeeping, cleanup, security-scan, dependency-check, performance, document, monitor-setup, rollback, create-skill, daily, plus `ez-project-workflow` (operating rules). `AGENTS.md` lists which Claude commands intentionally have no Codex mirror (`/do`, `/idea-to-pr`, `/upgrade-to-project`).

## Pipelines (`.claude/pipelines/`)
- `feature.yml` — feature delivery
- `bugfix.yml` — defect triage and fix
- `security.yml` — full security audit pipeline
- `release.yml` — release checklist

## Common Commands
```bash
# Dev
.venv/Scripts/python.exe scanner/run_scan.py --repo "C:\path\to\repo"  # Run scanner foundation
.venv/Scripts/python.exe scanner/run_scan.py --repo "." --reports-dir reports  # Self-scan
python -m src.main                                   # Legacy entry point
.venv/Scripts/python.exe -m pytest tests/ -v                            # Run all tests
.venv/Scripts/python.exe -m pytest tests/ -v -k "test_name"             # Run specific test

# Lint & Format
.venv/Scripts/ruff.exe check scanner src/ tests/ fingerprint/          # Lint
.venv/Scripts/ruff.exe check scanner src/ tests/ fingerprint/ --fix    # Auto-fix lint issues
.venv/Scripts/python.exe -m black scanner src/ tests/ fingerprint/      # Format

# Web template fingerprinting (experimental)
.venv/Scripts/python.exe fingerprint/run_index.py --rebuild                                 # Rebuild local DB from seed list (real git clones)
.venv/Scripts/python.exe fingerprint/run_match.py --target https://example.com              # Probe a single live URL against the local DB

# Setup (nouveau projet)
python -m venv .venv && source .venv/bin/activate   # REQUIRED - never run off the global interpreter
pip install -e ".[dev]"                  # Install deps from pyproject.toml
pip install -e ".[scraping]"             # Optional Playwright extra
cp .env.example .env                     # Configure environment

# External scanners (install separately, must be on PATH)
semgrep --version
gitleaks version
trivy --version
.venv/Scripts/python.exe -m pip install pip-audit && pip-audit --version

# Optional AI review (disabled by default — see scanner/config.py)
$env:AI_PATCHLAB_AI_REVIEW_ENABLED = "true"
$env:AI_PATCHLAB_AI_REVIEW_PROVIDER = "local_command"
$env:AI_PATCHLAB_AI_REVIEW_COMMAND  = "C:\tools\ai-review-wrapper.cmd"

# Database
# Schema in docs/schema.sql (not yet created — `docs/` is empty)
```

## MCP Servers
- **memory** — Persistance Claude Code entre sessions
- **mysql** — Accès direct à la DB via `@bytebase/dbhub` (configurer `MYSQL_DSN` dans `.env`)
  - Utilise la variable `MYSQL_DSN` au format: `mysql://user:password@host:port/database`
  - cPanel: `mysql://cpaneluser_dbuser:password@sql.yourhost.com:3306/cpaneluser_dbname`
  - Requiert: IP whitelistée dans cPanel > Remote MySQL
  - Premier lancement: `npx @bytebase/dbhub@latest --help` pour pré-cacher le package

## Database Conventions
- MySQL tables in `snake_case`
- Always include `id` (AUTO_INCREMENT), `created_at`, `updated_at`
- Indexes on frequently queried columns
- Schema migrations: append new SQL to `docs/schema.sql` with date comment
- Use parameterized queries — NEVER string concatenation for SQL
- Connection pooling with aiomysql
- Migration format in `docs/schema.sql`:
  ```sql
  -- Migration: YYYY-MM-DD — Description
  ALTER TABLE ... ;
  ```

## Error Handling
- ALWAYS wrap external calls (API, scraping, DB) in try/except
- Log errors with full context using loguru
- Retry logic with exponential backoff for network calls (see `examples/api_client_pattern.py`)
- NEVER silently suppress errors
- Use custom exception classes for domain-specific errors
- Scanner runners catch `OSError` and `subprocess.TimeoutExpired`, write a safe empty raw JSON, and return a structured `*Result` instead of propagating

## Testing
- pytest for all tests (`pytest-asyncio` mode is `auto`, see `pyproject.toml`)
- Fixtures in `tests/conftest.py` (DB mock, HTTP mock, Discord mock, test config, session event loop)
- Mock external calls (API, DB, subprocess) in unit tests
- Test critical calculation functions thoroughly
- Use `pytest-asyncio` for async tests
- Markers available: `@pytest.mark.slow`, `@pytest.mark.integration`
- Each scanner adapter has a dedicated test module under `tests/test_<scanner>.py`

## Git Workflow
- Create a branch for each feature
- Descriptive commit messages in English
- Format: `type: description` (feat, fix, refactor, docs, test)
- Never commit directly to main
- Run tests before committing

## Roadmap Management
- Always check ROADMAP.md first
- Progression: `[ ]` Todo → `[-]` In Progress 🏗️ → `[x]` Done ✅
- Add timestamp (YYYY/MM/DD) when status changes
- Update ROADMAP.md after completing each task

## Architecture Decisions
- All architectural decisions are logged in `DECISIONS.md`
- Before making a structural decision, check DECISIONS.md for precedent
- Use the architect agent (`/architect` or Task tool) for complex decisions
- Format: ADR (Architecture Decision Record) — date, decision, context, consequences
- Current ADRs of record: ADR-001 scaffold, ADR-002 data stack, ADR-003 placeholder adapters, ADR-004 Gitleaks, ADR-005 Semgrep, ADR-006 recommendation enrichment, ADR-007 patch suggestions, ADR-008 Trivy, ADR-009 pip-audit, ADR-010 disabled-by-default AI review boundary, ADR-011 centralized scanner confidence rules, ADR-012 probabilistic web template fingerprinting boundary, ADR-013 meta findings exempt from severity filtering, ADR-014 field-derived confidence tiers

## Known Gotchas
- Semgrep is a **Python program on the shared user-site interpreter**, not a standalone binary like gitleaks/trivy. Anything that breaks that interpreter breaks Semgrep too — a pydantic downgrade on 2026-08-20 made `semgrep --version` raise ImportError and every scan would have silently lost 52% of its coverage. The project `.venv` does NOT protect it. Check `semgrep --version` before trusting a scan; repair with `python -m pip install --user --upgrade "pydantic>=2.11" "httpx>=0.27"`
- ALWAYS run through `.venv` (`.venv/Scripts/python.exe` on Windows). The project ran for three months off the shared user-site and on 2026-08-20 an unrelated `pip install` downgraded pydantic to 1.x and httpx to 0.21: `scanner`, `fingerprint` and every test stopped importing, while the scan pipeline had passed hours earlier. A global interpreter is a shared mutable dependency
- Meta findings (`Finding.is_meta=True`) survive `--min-severity` but are NOT yet exempt from `--ignore-file` suppression - a path pattern can still hide a coverage warning. Any new finding built with `confidence_for_meta_finding(...)` must also set `is_meta=True`; the two always travel together
- Semgrep coverage comes from the `errors` array, never `paths.skipped`. Across the scan series `skipped` has been empty on every run where rules timed out - including a run where both subprocess-injection rules timed out on the 20k-line file that was the whole API surface. `scan_semgrep` emits `semgrep-partial-coverage` naming each `rule -> file` pair that did not run
- `ai-patchlab` and `2026-05-12` are template placeholders replaced by ez-new-project.ps1 — do not remove from template source files
- aiomysql: toujours fermer le pool avec `await db.disconnect()` dans le finally
- Playwright: `wait_until="networkidle"` peut timeout sur les SPA — utiliser `"domcontentloaded"` si nécessaire
- Discord webhooks: rate limit de 30 messages/minute par webhook
- pydantic-settings: les variables .env sont case-insensitive par défaut
- MCP MySQL (dbhub): si le password contient `@`, `:`, `/` ou `%`, il faut l'URL-encoder dans le DSN
- cPanel MySQL: les noms de DB et users sont préfixés (ex: `cpaneluser_dbname`) — ne pas oublier le préfixe
- AI review must remain disabled by default and local-first. Never add a default remote provider, default endpoint, default model, or default token variable. Any future remote/paid provider requires explicit configuration and a new ADR.
- Scanner subprocess invocations MUST use `shell=False` and an explicit argv list — `shell=True` is the exact anti-pattern the patch engine warns about (see `scanner/remediation/patch_suggestions.py:SUBPROCESS_SHELL_SUGGESTION`)
- Semgrep on Windows: when not on `PATH`, the runner falls back to `Path.home() / AppData/Roaming/Python/Python313/Scripts/semgrep.exe` (see `scanner/tools/semgrep_runner.py:PIP_USER_SEMGREP_PATH`). The Python minor version is hardcoded — if the user installs under a different Python version, the runner will silently skip Semgrep until the constant is updated
- Semgrep UTF-8 output (Windows, 2026-06-11 fix): Semgrep writes its `--output` JSON via Python's default text codec, which on Windows is the locale codepage (cp1252). A repo with non-Latin-1 source content (Chinese/Japanese/Korean comments, emoji) crashes Semgrep mid-write with `UnicodeEncodeError`, leaving a **0-byte report** and exit code 2. `_build_semgrep_env` now forces `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` in the child env to prevent this. As defense-in-depth, `scan_semgrep` treats an empty/0-byte report as a `semgrep-scan-error` finding (not silently zero findings). NOTE: the scan-error finding is `info` severity, so a run with `--min-severity medium` still filters it from the report — RESOLVED 2026-08-21: scanner-infrastructure findings now carry `is_meta=True` and are exempt from `--min-severity`
- All external scanners are optional — if a tool is missing, the adapter emits a normalized `info` finding (e.g. `semgrep-not-installed`, `gitleaks-not-installed`, `trivy-not-installed`, `pip-audit-not-installed`, `ai-review-disabled`) instead of failing
- pip-audit supports requirements files, `pyproject.toml` projects, or `pylock.*.toml` locked projects — the runner picks the first match in that order
- AI review timeouts default to 120s (`AI_PATCHLAB_AI_REVIEW_TIMEOUT_SECONDS`); on timeout the runner writes `[]` to `reports/raw/ai-review.json` and emits a normalized error finding so the report still completes
- Fingerprint web probe respects `robots.txt`. Be careful when crafting tests: `urllib.robotparser` splits the live user-agent on `/` before matching, so a robots.txt block for `ai-patchlab-fingerprint/0.1` is matched as `ai-patchlab-fingerprint` (drop the version when authoring rules)
- Fingerprint matching is a SIGNAL, not an attribution. The Markdown report must keep the `DISCLAIMER` block and must never claim a match is "confirmed", "proven", "stolen", or "copied" — these words are blocked by a regression test in `tests/test_fingerprint_report.py`
- The fingerprint CLI accepts exactly one `--target` per invocation. No `--targets-file` flag exists by design — multi-target scanning would require a new ADR
- Fingerprinting must not add DOM-parser dependencies (`beautifulsoup4`, `lxml`) or browser stacks (`playwright`, `selenium`). v0.1 stays on `re` + `hashlib` + `httpx` only

## IMPORTANT RULES
- Keep things SIMPLE — MVP first, iterate later
- Read examples in examples/ before implementing anything new
- Validate each step before moving to the next (Plan → Implement → Validate)
- Do NOT over-engineer — no premature abstractions
- When in doubt, ask before assuming
- Proactively suggest improvements when you spot issues
- ULTRATHINK before making architectural decisions
- Log architectural decisions in DECISIONS.md

## Self-Healing Layer (AI-layer evolution)
When something is painful in an implementation, fix the underlying AI layer — not just the code. The "AI layer" is everything that shapes how the coding agent behaves: `CLAUDE.md`, `AGENTS.md`, `examples/`, `.claude/commands/`, `.claude/agents/`, `.claude/pipelines/`, `.agents/skills/`, PRP templates.

**Rule:** never review the implementer's work in the same context window that produced it. The writer is biased about its own output ("kid grading own homework"). Always run reviews and retrospectives in a fresh conversation.

**Workflow:**
1. `/execute-prp <prp>` → implements + housekeeps + outputs handoff message (does NOT self-review)
2. **New conversation** → `/retrospective last` → identifies AI-layer drift and proposes concrete file edits
3. User approves the proposed edits → applied to CLAUDE.md / examples / skills / agents

**When to skip:** trivial implementations, doc-only changes, or PRPs that went perfectly clean. The retrospective should produce zero items in those cases.

## AUTOMATIC HOUSEKEEPING (do this without being asked)
- After completing any feature or fix, ALWAYS update ROADMAP.md (mark items done with date)
- After any structural change (new files, new folders, new dependencies), update the relevant sections of THIS file (CLAUDE.md)
- If `AGENTS.md` exists, update the matching sections there too so Codex and Claude stay aligned
- After completing a PRP, move it to `PRPs/done/` with date prefix
- After creating temporary/scratch files for debugging, DELETE them when done
- If CLAUDE.md.proposed exists and changes have been applied, DELETE it
- If AGENTS.md.proposed exists and changes have been applied, DELETE it
- When committing, include doc updates in the same commit or a separate "docs:" commit immediately after
- NEVER leave documentation out of sync with code
