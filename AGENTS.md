# Project: ai-patchlab

> This file captures the Codex/OpenAI workflow for the project.
> It should stay aligned with `CLAUDE.md` when both runtimes are present.

## About
AI PatchLab is an AI-assisted security remediation toolkit. The MVP focuses on a local Python scanner that accepts a repository path, normalizes security findings, and writes JSON plus Markdown reports for remediation planning.

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
- Local CLI scanner foundation
- JSON and Markdown report generation
- Data stack selected for repository analysis workflows
- MySQL 8.0 (aiomysql for async, available but not required in v0.1)
- Playwright (if scraping is needed later)
- Discord webhooks (alerts, optional later)
- Loguru (logging)
- pytest (testing)
- ruff + black (linting/formatting)
- httpx (async HTTP client)
- pydantic + pydantic-settings (validation + config)

## Key Directories
- `scanner/` - Scanner CLI, finding model, recommendation enrichment, report generation, scanner registry
- `scanner/remediation/` - Deterministic patch suggestion engine for known vulnerability patterns
- `scanner/scanners/` - Scanner adapters for Semgrep, Gitleaks, Trivy, dependency scan, and a disabled-by-default local-only AI review boundary
- `scanner/tools/` - External scanner process runners such as Semgrep, Gitleaks, Trivy, pip-audit, and the opt-in AI review local command runner
- `scanner/config.py` - Disabled-by-default AI review configuration loaded from environment / `.env`
- `reports/` - Generated security reports (`security_report.json`, `security_report.md`)
- `src/` - Main source code
- `src/main.py` - Entry point (`python -m src.main`)
- `tests/` - pytest tests
- `tests/conftest.py` - Shared fixtures
- `examples/` - Reference patterns to read before implementing
- `PRPs/` - Active Product Requirements Prompts
- `PRPs/done/` - Archived PRPs
- `docs/` - Technical documentation
- `logs/` - Log files
- `.agents/skills/` - Codex skills for repeatable workflows
- `.claude/` - Claude runtime files, if present

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
- `retrospective` - Self-healing retrospective in a fresh context after `/execute-prp` (lite mode) or sprint-wide (no arg)
- `next` - Read project state and recommend the 1-3 best next actions
- `upgrade-status` - Compare project to latest template; list features not yet adopted
- `status` - Produce a compact project status snapshot
- `audit-project` - Audit runtime docs and project scaffolding
- `housekeeping` - Sync docs and remove temporary artifacts
- `cleanup` - Identify dead code via import-graph trace; report and ask before deleting
- `security-scan` - OWASP top 10 + secrets + vulnerable deps audit (inline two-stage per ADR-016)
- `dependency-check` - Vulnerabilities, outdated packages, compatibility audit; optional safe auto-update
- `performance` - Static hot-path scan + optional runtime profiling (inline two-stage per ADR-016)
- `document` - Auto-generate docs from code (API ref, data dict, architecture, modules)
- `monitor-setup` - Health check endpoint + alerting + uptime tracking adapted to stack
- `rollback` - Safe git rollback (always revert + stash, never reset --hard)
- `create-skill` - Scaffold a new Codex skill for the project

## Claude-only commands (no Codex skill mirror)
These Claude slash commands are intentionally not mirrored on the Codex side. Listed in `tests/template/test_codex_parity.py` as `KNOWN_EXCEPTIONS`.

- `/do` (smart-router) â€” natural-language intent routing requires a Claude-side primitive that Codex doesn't expose; the pattern table at `.claude/commands/smart-router.md` is Claude-only.
- `/idea-to-pr` â€” end-to-end idea â†’ PR flow requires PR/branching orchestration that's tightly coupled to Claude's tool layer.
- `/upgrade-to-project` â€” one-shot MVPâ†’Project upgrade run rarely; the equivalent on the Codex side is to invoke `ez-upgrade-project.ps1` directly.

## Common Commands
```bash
# Dev
python scanner/run_scan.py --repo "C:\path\to\repo"
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
cp .env.example .env
```

## MCP Servers
- `memory` - Session persistence when configured
- `mysql` - Direct database access through MCP when `MYSQL_DSN` is configured

## Database Conventions
- MySQL tables in `snake_case`
- Always include `id`, `created_at`, and `updated_at`
- Index frequently queried columns
- Append migrations to `docs/schema.sql` with a dated comment
- Use parameterized queries only

## Error Handling
- Wrap external calls in `try/except`
- Log errors with context using loguru
- Use retries with backoff for network calls when needed
- Never silently suppress errors
- Use custom exception classes for domain-specific failures

## Testing
- Use pytest for all tests
- Mock external calls in unit tests
- Cover critical calculation and workflow paths
- Use `pytest-asyncio` for async tests
- Available markers: `slow`, `integration`

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

## Known Gotchas
- `ai-patchlab` and `2026-05-12` are template placeholders replaced during scaffolding
- `aiomysql` pools must be closed explicitly
- Playwright `networkidle` can time out on SPAs; use `domcontentloaded` when needed
- MCP MySQL DSNs require URL-encoding special characters in passwords
- AI review must remain disabled by default and local-first. Never add a default remote provider, default endpoint, default model, or default token variable. Any future remote/paid provider requires explicit configuration and a new ADR.

## Important Rules
- Keep things simple - MVP first
- Read `examples/` before inventing new patterns
- Validate each step before moving on
- Do not over-engineer
- Log meaningful architecture decisions in `DECISIONS.md`

## Self-Healing Layer (AI-layer evolution)
When an implementation is painful, fix the underlying AI layer â€” not just the code. The AI layer is `CLAUDE.md`, `AGENTS.md`, `examples/`, `.claude/commands/`, `.claude/agents/`, `.agents/skills/`, PRP templates, pipelines.

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
