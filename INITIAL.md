# Feature Request: EzProject v4 — Dual-Mode Template with Team Agents & Skill Creator

## FEATURE:
Evolve the EzProject template (v3 → v4) from a solo MVP-only scaffolding tool into a dual-mode project generator. The template must support both quick MVPs (current behavior, unchanged) and full-scale projects with multi-agent orchestration, extended roadmap phases, modular tech stack selection, and self-extending skill creation.

The `/kickoff` command will ask the user to choose between "MVP mode" (current behavior, unchanged) and "Project mode" (adds orchestrator agent, team coordination, extended ROADMAP phases, CI/CD templates). Stack selection during kickoff adapts `examples/`, `pyproject.toml`, and agent configurations based on presets (data, api, ai-agent).

A new orchestrator agent decomposes epics into parallel tasks and coordinates existing agents via git worktrees. A `/create-skill` command enables any project to generate custom skills (slash commands + agents) on the fly, making the system self-extensible without modifying the template.

Existing v3 projects can be upgraded to Project mode via a command/script without breaking their current setup.

MVP first — keep it simple.

## EXAMPLES:
- `examples/config_pattern.py` — Base pattern for stack-agnostic configuration
- `examples/service_pattern.py` — Service pattern to extend per stack preset
- `examples/api_client_pattern.py` — Pattern relevant for FastAPI stack preset
- `.claude/agents/architect.md` — Reference for designing the orchestrator agent
- `.claude/agents/researcher.md` — Reference for agent structure and tool declarations
- `.claude/commands/kickoff.md` — Current kickoff command to extend with mode/stack selection
- `.claude/commands/generate-prp.md` — Reference for skill creator command design
- `ez-new-project.ps1` — Current scaffold script to update for mode/stack selection
- `ez-upgrade-project.ps1` — Current upgrade script to extend for MVP→Project upgrade
- `ez-launcher.ps1` — GUI launcher to update with mode/stack options

## DOCUMENTATION:
- Claude Code agents: https://docs.anthropic.com/en/docs/claude-code/agents
- Claude Code custom commands: https://docs.anthropic.com/en/docs/claude-code/slash-commands
- PydanticAI docs: https://ai.pydantic.dev/
- FastMCP docs: https://gofastmcp.com/
- FastAPI docs: https://fastapi.tiangolo.com/

## TECH STACK:
- **Template itself:** PowerShell (launcher/scripts), Markdown (docs/agents/commands), JSON (settings)
- **Default generated project:** Python 3.11+, MySQL 8.0, Loguru, Pydantic, httpx
- **Stack presets:**
  - `data` (default): Python + MySQL + Playwright + aiomysql
  - `api`: Python + FastAPI + MySQL + aiomysql
  - `ai-agent`: Python + PydanticAI + FastMCP

## DATA FLOW:
```
User Input (ez-launcher / kickoff)
    → Mode Selection (MVP / Project)
    → Stack Selection (data / api / ai-agent)
    → Template Engine (PowerShell string replacement + conditional file copy)
    → Scaffold Output (agents, commands, examples, deps adapted to mode + stack)
    → Configured Project ready for Claude Code
```

## CONSTRAINTS:
- Backward-compatible: v3 projects must upgrade cleanly to v4 without data loss
- PowerShell launcher (ez-launcher.ps1, ez-new-project.ps1) must keep working on Windows 11
- No heavy templating frameworks — keep it simple (string replacement, conditional file copy/skip)
- Existing slash commands and agents must remain functional in MVP mode
- Windows 11 + OneDrive environment (path handling, file locking considerations)
- Claude Code is the primary consumer — optimize for its agent/command/MCP workflow
- Template source files currently serve dual role (project docs + scaffold source) — must be separated

## MVP SCOPE:
1. **Mode selector in `/kickoff`** — asks "MVP ou Projet complet?" and adapts generated files accordingly
2. **Orchestrator agent** — decomposes epics into parallel tasks, coordinates existing agents via git worktrees
3. **Extended ROADMAP phases** — post-MVP phase templates (scaling, CI/CD, monitoring, releases) activated in Project mode
4. **Stack presets** — kickoff adapts `examples/` and `pyproject.toml` for 3 stack presets (data, api, ai-agent)
5. **Upgrade path** — command/script to upgrade an existing MVP project to Project mode
6. **Skill Creator** — `/create-skill` command that generates new custom skills (command + agent) adapted to the project context, making the system self-extensible

## OUT OF SCOPE (for now):
- Web-based project dashboard / status tracker
- Automatic CI/CD pipeline generation (GitHub Actions YAML)
- Multi-language support (beyond Python)
- Template marketplace / sharing between users
- Docker/container scaffolding
- Database migration tooling (beyond schema.sql)
- n8n / external orchestration integration
- Visual dependency graph between agents/tasks

## SUCCESS CRITERIA:
- [ ] `/kickoff` in a new project offers MVP vs Project mode choice and stack selection
- [ ] Choosing "Project mode" scaffolds orchestrator agent, extended ROADMAP phases, and team coordination
- [ ] Stack selection correctly adapts `pyproject.toml` dependencies and `examples/` patterns
- [ ] An existing v3 MVP project upgrades to Project mode without losing existing work
- [ ] `/create-skill` generates a functional command + agent pair from a description
- [ ] All existing MVP-mode functionality remains unchanged (full backward compatibility)
- [ ] The ez-launcher GUI supports mode and stack selection for new projects
