# Code Patterns

Examples are organized by stack preset. Your project includes patterns matching your selected stack.

## Common (all stacks)
- `config_pattern.py` — Configuration with Pydantic Settings and .env loading
- `service_pattern.py` — Business logic service pattern (data → calculation → action)

## Data Stack (Python + MySQL + Playwright)
- `mysql_pattern.py` — Async MySQL with aiomysql connection pooling
- `api_client_pattern.py` — REST API client with retry, rate limiting, pagination
- `playwright_scraper_pattern.py` — Browser scraping with Playwright
- `discord_alert_pattern.py` — Discord webhook notifications
- `scheduler_pattern.py` — Async task scheduling with intervals

## API Stack (Python + FastAPI + MySQL)
- `fastapi_app_pattern.py` — Application setup, lifespan, CORS, error handling, logging
- `fastapi_router_pattern.py` — CRUD router with pagination, validation, dependency injection

## AI Agent Stack (Python + PydanticAI + FastMCP)
- `pydantic_ai_agent_pattern.py` — PydanticAI agent with tools, structured output, dependency injection, and provider-configured model selection
- `fastmcp_server_pattern.py` — FastMCP server with tools, resources, prompts

## Web Stack (Python + FastAPI + Jinja2 + MySQL)
- `fastapi_app_pattern.py` — Application setup, lifespan, CORS, error handling, logging *(shared with API stack)*
- `fastapi_router_pattern.py` — CRUD router with pagination, validation *(shared with API stack)*
- `jinja2_templates_pattern.py` — Jinja2 template engine setup, rendering, custom filters
- `static_files_pattern.py` — Static file serving (CSS, JS, images), cache control
- `htmx_pattern.py` — HTMX integration for interactive server-rendered pages
- `auth_session_pattern.py` — Session-based authentication with cookies
- `form_handling_pattern.py` — HTML form processing, file uploads, CSRF protection

## Usage
Read the relevant patterns BEFORE implementing a feature. They demonstrate the project's coding conventions.
