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
- `scanner/` - Scanner CLI, finding model, recommendation enrichment, report generation, scanner registry
- `scanner/run_scan.py` - CLI entry point (`python scanner/run_scan.py --repo <path>`)
- `scanner/models.py` - Normalized `Finding` dataclass + severity/confidence enums + `FINDING_FIELDS`
- `scanner/recommendations.py` - Deterministic keyword-based recommendation enrichment
- `scanner/confidence.py` - Centralized `Finding.confidence` rules (one function per scanner + `confidence_for_meta_finding` for shared `not-installed` / `scan-error` / etc.)
- `scanner/report.py` - JSON + Markdown report writers (severity-grouped, patch suggestion blocks)
- `scanner/config.py` - Disabled-by-default AI review configuration loaded from environment / `.env` (`AI_PATCHLAB_*`)
- `scanner/remediation/` - Deterministic patch suggestion engine (`patch_suggestions.py`) for known vulnerability patterns
- `scanner/scanners/` - Scanner adapters (`semgrep.py`, `gitleaks.py`, `trivy.py`, `dependency_scan.py`, `ai_review.py`) plus `common.py` placeholder helper and `__init__.py` registry (`SCANNERS`)
- `scanner/tools/` - External scanner process runners (`semgrep_runner.py`, `gitleaks_runner.py`, `trivy_runner.py`, `pip_audit_runner.py`, `ai_review_runner.py`)
- `reports/` - Generated security reports (`security_report.json`, `security_report.md`)
- `reports/raw/` - Raw scanner JSON outputs (`semgrep.json`, `gitleaks.json`, `trivy.json`, `pip-audit.json`, `ai-review.json` when enabled)
- `src/` - Legacy scaffold entry point (kept for template parity)
- `src/main.py` - Legacy entry point (`python -m src.main`) - currently a loguru-wired async stub with TODOs
- `tests/` - pytest tests (one module per scanner: `test_scanner_foundation.py`, `test_semgrep_scanner.py`, `test_gitleaks_scanner.py`, `test_trivy_scanner.py`, `test_dependency_scan.py`, `test_ai_review.py`, `test_patch_suggestions.py`, `test_recommendations.py`)
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

## Claude-only commands (no Codex skill mirror)
These Claude slash commands are intentionally not mirrored on the Codex side. Listed in `tests/template/test_codex_parity.py` as `KNOWN_EXCEPTIONS`.

- `/do` (smart-router) - natural-language intent routing requires a Claude-side primitive that Codex doesn't expose; the pattern table at `.claude/commands/smart-router.md` is Claude-only.
- `/idea-to-pr` - end-to-end idea -> PR flow requires PR/branching orchestration that's tightly coupled to Claude's tool layer.
- `/upgrade-to-project` - one-shot MVP -> Project upgrade; the equivalent on the Codex side is to invoke `ez-upgrade-project.ps1` directly.

## Common Commands
```bash
# Dev
python scanner/run_scan.py --repo "C:\path\to\repo"
python scanner/run_scan.py --repo "." --reports-dir reports
python -m src.main
python -m pytest tests/ -v
python -m pytest tests/ -v -k "test_name"

# Lint & Format
ruff check scanner src/ tests/
ruff check scanner src/ tests/ --fix
python -m black scanner src/ tests/

# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install -e ".[scraping]"   # Optional Playwright extra
cp .env.example .env

# External scanners (install separately, must be on PATH)
semgrep --version
gitleaks version
trivy --version
python -m pip install pip-audit && pip-audit --version

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
- Each external tool runner lives in `scanner/tools/<tool>_runner.py`, returns a frozen `*Result` dataclass, writes raw JSON to `reports/raw/<tool>.json`, and uses `subprocess.run(..., shell=False, check=False)` with captured stdout/stderr
- Do not call subprocesses directly from `scanner/scanners/*` - go through the runner module
- `Finding.confidence` values come from `scanner/confidence.py` - never inline `confidence="high"` / `"medium"` / `"low"` in a scanner adapter; add or reuse a rule function instead

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
- Current ADRs of record: ADR-001 scaffold, ADR-002 data stack, ADR-003 placeholder adapters, ADR-004 Gitleaks, ADR-005 Semgrep, ADR-006 recommendation enrichment, ADR-007 patch suggestions, ADR-008 Trivy, ADR-009 pip-audit, ADR-010 disabled-by-default AI review boundary, ADR-011 centralized scanner confidence rules

## Known Gotchas
- `ai-patchlab` and `2026-05-12` are template placeholders replaced during scaffolding
- `aiomysql` pools must be closed explicitly with `await db.disconnect()` in `finally`
- Playwright `networkidle` can time out on SPAs; use `domcontentloaded` when needed
- Discord webhooks: 30 messages/minute rate limit per webhook
- pydantic-settings: `.env` variables are case-insensitive by default
- MCP MySQL DSNs require URL-encoding for special characters in passwords
- cPanel MySQL DB and user names are prefixed (e.g. `cpaneluser_dbname`) - don't forget the prefix
- AI review must remain disabled by default and local-first. Never add a default remote provider, default endpoint, default model, or default token variable. Any future remote/paid provider requires explicit configuration and a new ADR.
- Scanner subprocess invocations MUST use `shell=False` and an explicit argv list - `shell=True` is the exact anti-pattern the patch engine warns about (see `scanner/remediation/patch_suggestions.py:SUBPROCESS_SHELL_SUGGESTION`)
- Semgrep on Windows: when not on `PATH`, the runner falls back to a hard-coded `pip --user` path (`scanner/tools/semgrep_runner.py:PIP_USER_SEMGREP_PATH`). That path is user-specific - if it shifts, the runner will silently skip Semgrep. Update fallback paths in one place
- All external scanners are optional - if a tool is missing, the adapter emits a normalized `info` finding (`semgrep-not-installed`, `gitleaks-not-installed`, `trivy-not-installed`, `pip-audit-not-installed`, `ai-review-disabled`) instead of failing
- pip-audit input resolution order: root `requirements*.txt` first, then `pylock.*.toml` (with `--locked`), then `pyproject.toml`
- AI review timeouts default to 120s (`AI_PATCHLAB_AI_REVIEW_TIMEOUT_SECONDS`); on timeout the runner writes `[]` to `reports/raw/ai-review.json` and emits a normalized error finding so the report still completes

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
