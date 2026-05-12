---
name: monitor-setup
description: Configure health checks, alerting patterns, and uptime tracking adapted to the project's stack. Use after kickoff or before deployment to add operational hooks.
---

# Monitor Setup

## Phase 1: Assess current state
1. Read CLAUDE.md / AGENTS.md for stack type
2. Grep for existing `/health` or `healthcheck` endpoints
3. Check if Discord webhook alerting is configured (env var, `examples/discord_alert_pattern.py`)
4. Check if logging is structured for monitoring

Default scope: all (`$ARGUMENTS` can narrow to `health`, `alerts`, or `uptime`).

## Phase 2: Health check endpoint (if stack = api or ai-agent)
Create or update an endpoint at `/health`:
- `status: "healthy"`, `version`, `uptime`
- Sub-checks: database connectivity, external API reachability

Add `src/utils/health.py` with helpers (`get_uptime`, `check_db`, `check_apis`). Add a health-check pattern to `examples/`.

## Phase 3: Alert patterns
Build on `examples/discord_alert_pattern.py`:
- Levels: INFO / WARNING / ERROR / CRITICAL
- Channels: Discord webhook (primary), loguru file, stdout
- Deduplication: don't spam the same error

Add `src/utils/alerts.py` with the helper functions.

## Phase 4: Uptime (data stack)
Track process start time in memory. Optionally log uptime milestones (1h, 6h, 24h, 7d). On long-running processes, add graceful shutdown logging.

## Phase 5: Validate + document
1. Run `ruff check` and `black` on new files
2. If an API endpoint was created, show the user a curl test command
3. Update CLAUDE.md / AGENTS.md with a Monitoring section
4. Update README with the health-check URL
5. Commit: `feat: add monitoring setup (<components>)`

## Rules
- Adapt to the project stack — do not add API endpoints to a data-only project
- Discord webhook URL comes from `.env` (never hardcode)
- Health checks must be FAST (< 500ms total)
- Alert deduplication is critical — never spam a webhook
- Monitoring code should never crash the main application
