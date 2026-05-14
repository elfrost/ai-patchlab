# Project: ai-patchlab

> Ce fichier est lu automatiquement par Claude Code au dÃ©but de chaque session.
> Il dÃ©finit les rÃ¨gles, standards et contexte du projet.

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
- Local CLI scanner foundation
- JSON and Markdown report generation
- Data stack selected for repository analysis workflows
- MySQL 8.0 (aiomysql for async, available but not required in v0.1)
- Playwright (si scraping requis plus tard)
- Discord webhooks (alertes optionnelles plus tard)
- Loguru (logging)
- pytest (testing)
- ruff + black (linting/formatting)
- httpx (async HTTP client)
- pydantic + pydantic-settings (validation + config)

## Key Directories
- `scanner/` â€” Scanner CLI, finding model, recommendation enrichment, report generation, scanner registry
- `scanner/remediation/` â€” Deterministic patch suggestion engine for known vulnerability patterns
- `scanner/scanners/` â€” Scanner adapters for Semgrep, Gitleaks, Trivy, dependency scan, and a disabled-by-default local-only AI review boundary
- `scanner/tools/` â€” External scanner process runners such as Semgrep, Gitleaks, Trivy, pip-audit, and the opt-in AI review local command runner
- `scanner/config.py` â€” Disabled-by-default AI review configuration loaded from environment / `.env`
- `reports/` â€” Generated security reports (`security_report.json`, `security_report.md`)
- `src/` â€” Code source principal
- `src/main.py` â€” Point d'entrÃ©e (`python -m src.main`)
- `src/scrapers/` â€” Scrapers Playwright (si applicable)
- `src/models/` â€” ModÃ¨les de donnÃ©es / MySQL schemas
- `src/services/` â€” Business logic / calculs
- `src/utils/` â€” Utilitaires partagÃ©s (logging, config, helpers)
- `tests/` â€” Tests pytest
- `tests/conftest.py` â€” Fixtures partagÃ©es (DB mock, HTTP mock, etc.)
- `examples/` â€” Code de rÃ©fÃ©rence â€” LIRE AVANT D'IMPLÃ‰MENTER
- `PRPs/` â€” Product Requirements Prompts (actifs)
- `PRPs/done/` â€” PRPs complÃ©tÃ©s (archive)
- `docs/` â€” Documentation technique
- `logs/` â€” Log files (gitignored except .gitkeep)
- `AGENTS.md` â€” Codex/OpenAI runtime instructions (if Codex support is enabled)
- `.agents/skills/` â€” Codex skills for repeatable workflows (if Codex support is enabled)

## Coding Standards

### Python
- Type hints REQUIRED on all functions
- Docstrings Google-style on public functions
- Files max 300 lines â€” split if bigger
- Variable/function names in English
- Comments OK in French
- Use `async/await` for all I/O (scraping, DB, API calls)
- Logging with `loguru` â€” never use print() in production code
- Config via `.env` files â€” never hardcode secrets (see `examples/config_pattern.py`)
- Use `pathlib.Path` for file paths
- Use `pydantic` models for data validation

### File Structure
- One class per file for major components
- Group related functions in modules
- `__init__.py` should only contain imports
- Keep utils genuinely generic

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: prefix with `_`

## Slash Commands (Claude Code)
```
/kickoff              â€” Interview interactive â†’ gÃ©nÃ¨re INITIAL.md
/generate-prp FILE    â€” Recherche + gÃ©nÃ¨re un PRP d'implÃ©mentation
/execute-prp FILE     â€” ExÃ©cute un PRP (implÃ©mente la feature)
/review-code          â€” Code review automatisÃ©e
/status               â€” Snapshot rapide de l'Ã©tat du projet
/next                 â€” SuggÃ¨re les 1-3 prochaines actions selon l'Ã©tat actuel du projet
/upgrade-status       â€” Compare le projet au template courant; liste les features manquantes
/audit-project        â€” Audit du CLAUDE.md
/cleanup              â€” Analyse de dead code
/housekeeping         â€” Mise Ã  jour docs post-implÃ©mentation
/rollback             â€” Rollback sÃ©curitaire des changements
/retrospective [PRP]  â€” RÃ©trospective: vide=sprint 2 semaines, "last" ou nom de PRP=self-healing per-PRP en contexte frais
/create-skill DESC    â€” GÃ©nÃ¨re un nouveau skill (command + agent) Ã  partir d'une description
/upgrade-to-project   â€” Upgrade MVP vers Project mode (orchestrator + extended phases)
/security-scan [PATH] â€” Full security audit: secrets, deps vulnÃ©rables, OWASP patterns
/refactor [PATH]      â€” Analyse code smells + complexitÃ©, refactoring ciblÃ© avec validation
/fix-issue DESC       â€” End-to-end: diagnose -> fix -> test -> review -> commit
/idea-to-pr DESC      â€” End-to-end: idea -> research -> design -> implement -> test -> review -> PR
/pipeline NAME [DESC] â€” Execute un pipeline (feature, bugfix, security, release, ou custom)
/dependency-check     â€” Audit dependances: vulnerabilites, updates, compatibilite
/do DESC              â€” Smart router: dÃ©cris ce que tu veux â†’ route vers la bonne action
/document [SCOPE]     â€” Auto-gÃ©nÃ¨re la documentation (api, data, architecture, modules, all)
/performance [PATH]   â€” Profile le code, identifie bottlenecks et optimisations
/monitor-setup [TYPE] â€” Configure health checks, alerting, uptime (health, alerts, uptime, all)
/tdd DESC             â€” ImplÃ©mentation Red-Green-Refactor stricte (Iron Law: pas de code sans test failing observÃ©)
```

## Common Commands
```bash
# Dev
python scanner/run_scan.py --repo "C:\path\to\repo"  # Run scanner foundation
python -m src.main              # Run main entry point
python -m pytest tests/ -v                # Run all tests
python -m pytest tests/ -v -k "test_name" # Run specific test

# Lint & Format
ruff check scanner src/ tests/          # Lint
ruff check scanner src/ tests/ --fix    # Auto-fix lint issues
python -m black scanner src/ tests/      # Format

# Setup (nouveau projet)
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"         # Install deps from pyproject.toml
cp .env.example .env            # Configure environment

# Database
# Schema in docs/schema.sql
```

## MCP Servers
- **memory** â€” Persistance Claude Code entre sessions
- **mysql** â€” AccÃ¨s direct Ã  la DB via `@bytebase/dbhub` (configurer `MYSQL_DSN` dans `.env`)
  - Utilise la variable `MYSQL_DSN` au format: `mysql://user:password@host:port/database`
  - cPanel: `mysql://cpaneluser_dbuser:password@sql.yourhost.com:3306/cpaneluser_dbname`
  - Requiert: IP whitelistÃ©e dans cPanel > Remote MySQL
  - Premier lancement: `npx @bytebase/dbhub@latest --help` pour prÃ©-cacher le package

## Database Conventions
- MySQL tables in `snake_case`
- Always include `id` (AUTO_INCREMENT), `created_at`, `updated_at`
- Indexes on frequently queried columns
- Schema migrations: append new SQL to `docs/schema.sql` with date comment
- Use parameterized queries â€” NEVER string concatenation for SQL
- Connection pooling with aiomysql
- Migration format in `docs/schema.sql`:
  ```sql
  -- Migration: YYYY-MM-DD â€” Description
  ALTER TABLE ... ;
  ```

## Error Handling
- ALWAYS wrap external calls (API, scraping, DB) in try/except
- Log errors with full context using loguru
- Retry logic with exponential backoff for network calls (see `examples/api_client_pattern.py`)
- NEVER silently suppress errors
- Use custom exception classes for domain-specific errors

## Testing
- pytest for all tests
- Fixtures in `tests/conftest.py` (DB mock, HTTP mock, Discord mock pre-built)
- Mock external calls (API, DB) in unit tests
- Test critical calculation functions thoroughly
- Use `pytest-asyncio` for async tests
- Markers available: `@pytest.mark.slow`, `@pytest.mark.integration`

## Git Workflow
- Create a branch for each feature
- Descriptive commit messages in English
- Format: `type: description` (feat, fix, refactor, docs, test)
- Never commit directly to main
- Run tests before committing

## Roadmap Management
- Always check ROADMAP.md first
- Progression: `[ ]` Todo â†’ `[-]` In Progress ðŸ—ï¸ â†’ `[x]` Done âœ…
- Add timestamp (YYYY/MM/DD) when status changes
- Update ROADMAP.md after completing each task

## Architecture Decisions
- All architectural decisions are logged in `DECISIONS.md`
- Before making a structural decision, check DECISIONS.md for precedent
- Use the architect agent (`/architect` or Task tool) for complex decisions
- Format: ADR (Architecture Decision Record) â€” date, decision, context, consequences

## Known Gotchas
- `ai-patchlab` and `2026-05-12` are template placeholders replaced by ez-new-project.ps1 â€” do not remove from template source files
- aiomysql: toujours fermer le pool avec `await db.disconnect()` dans le finally
- Playwright: `wait_until="networkidle"` peut timeout sur les SPA â€” utiliser `"domcontentloaded"` si nÃ©cessaire
- Discord webhooks: rate limit de 30 messages/minute par webhook
- pydantic-settings: les variables .env sont case-insensitive par dÃ©faut
- MCP MySQL (dbhub): si le password contient `@`, `:`, `/` ou `%`, il faut l'URL-encoder dans le DSN
- cPanel MySQL: les noms de DB et users sont prÃ©fixÃ©s (ex: `cpaneluser_dbname`) â€” ne pas oublier le prÃ©fixe
- AI review must remain disabled by default and local-first. Never add a default remote provider, default endpoint, default model, or default token variable. Any future remote/paid provider requires explicit configuration and a new ADR.

## IMPORTANT RULES
- Keep things SIMPLE â€” MVP first, iterate later
- Read examples in examples/ before implementing anything new
- Validate each step before moving to the next (Plan â†’ Implement â†’ Validate)
- Do NOT over-engineer â€” no premature abstractions
- When in doubt, ask before assuming
- Proactively suggest improvements when you spot issues
- ULTRATHINK before making architectural decisions
- Log architectural decisions in DECISIONS.md

## Self-Healing Layer (AI-layer evolution)
When something is painful in an implementation, fix the underlying AI layer â€” not just the code. The "AI layer" is everything that shapes how the coding agent behaves: `CLAUDE.md`, `AGENTS.md`, `examples/`, `.claude/commands/`, `.claude/agents/`, `.agents/skills/`, PRP templates.

**Rule:** never review the implementer's work in the same context window that produced it. The writer is biased about its own output ("kid grading own homework"). Always run reviews and retrospectives in a fresh conversation.

**Workflow:**
1. `/execute-prp <prp>` â†’ implements + housekeeps + outputs handoff message (does NOT self-review)
2. **New conversation** â†’ `/retrospective last` â†’ identifies AI-layer drift and proposes concrete file edits
3. User approves the proposed edits â†’ applied to CLAUDE.md / examples / skills / agents

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
