# /monitor-setup — Configure Monitoring & Health Checks

Set up health check endpoints, uptime monitoring, and alerting patterns for the project.

## Argument
`$ARGUMENTS` — Optional: `health`, `alerts`, `uptime`, or `all` (default: `all`).

## Process

### Phase 1: Assess Current State
1. Read CLAUDE.md for stack type
2. Check if health endpoint already exists (grep for `/health`, `healthcheck`)
3. Check if Discord webhook alerting is configured
4. Check if logging is properly structured for monitoring

### Phase 2: Health Check Endpoint (if stack = api or ai-agent)
1. Create or update health check endpoint at `/health`:
   ```python
   @router.get("/health")
   async def health_check():
       return {
           "status": "healthy",
           "version": settings.VERSION,
           "uptime": get_uptime(),
           "checks": {
               "database": await check_db(),
               "external_apis": await check_apis()
           }
       }
   ```
2. Create `src/utils/health.py` with:
   - `get_uptime()` — time since process start
   - `check_db()` — database connectivity test
   - `check_apis()` — external API reachability
3. Add health check to examples/ as a pattern

### Phase 3: Alert Patterns
1. Review existing `examples/discord_alert_pattern.py`
2. Create structured alert system:
   - **Alert levels:** INFO, WARNING, ERROR, CRITICAL
   - **Alert channels:** Discord webhook (default), loguru file, stdout
   - **Alert deduplication:** Don't spam same error repeatedly
3. Create `src/utils/alerts.py` with alert helper functions
4. Create monitoring example pattern in `examples/`

### Phase 4: Uptime Tracking (for data stack)
1. Create simple uptime tracking:
   - Process start time stored in memory
   - Periodic health self-check (optional)
   - Log uptime milestones (1h, 6h, 24h, 7d)
2. If long-running process: add graceful shutdown logging

### Phase 5: Validate & Document
1. If API endpoint created: test it responds correctly
2. Update CLAUDE.md with monitoring section if not present
3. Update README.md with health check URL
4. Commit changes

## Usage
- `/monitor-setup` — Set up everything
- `/monitor-setup health` — Only health endpoint
- `/monitor-setup alerts` — Only alerting patterns
- `/monitor-setup uptime` — Only uptime tracking

## Instructions

1. Read CLAUDE.md for project context and stack type
2. Determine the scope:
   - If `$ARGUMENTS` is provided, set up only that component
   - If empty or `all`, set up everything applicable to the stack
3. Assess current state:
   - Check for existing health endpoints, alert code, uptime tracking
   - Don't duplicate what already exists
4. For each component:
   - Show the user what will be created
   - Create the code files
   - Add example patterns to `examples/` if applicable
5. Validate:
   - Run `ruff check` on new files
   - Run `black` on new files
   - If API endpoint: show example curl command
6. Commit: `feat: add monitoring setup ([components])`

## Rules
- Adapt to project stack — don't add API endpoints to a data-only project
- Use existing patterns from examples/ as starting point
- Discord webhook URL comes from .env (never hardcode)
- Health checks should be FAST (< 500ms total)
- Alert deduplication is critical — never spam a webhook
- Monitoring code should never crash the main application
