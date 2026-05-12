# ai-patchlab

> [REMPLIR â€” Description du projet en 1-2 phrases]

## Quick Start

```bash
# Setup
cd ai-patchlab
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -e ".[dev]"
cp .env.example .env

# Run
python -m src.main

# Tests
pytest tests/ -v

# Lint & Format
ruff check src/ tests/
black src/ tests/
```

## AI Developer Runtimes

### Claude Code

Ce projet utilise [Claude Code](https://docs.anthropic.com/en/docs/claude-code) avec des slash commands personnalisÃ©es :

| Commande | Description |
|----------|-------------|
| `/kickoff` | Interview interactive pour dÃ©finir une feature |
| `/generate-prp INITIAL.md` | GÃ©nÃ¨re un plan d'implÃ©mentation (PRP) |
| `/execute-prp PRPs/feature.md` | ExÃ©cute le PRP |
| `/review-code` | Code review automatisÃ©e |
| `/status` | Snapshot rapide de l'Ã©tat du projet |
| `/audit-project` | Audit du CLAUDE.md |
| `/cleanup` | Analyse de dead code |
| `/housekeeping` | Mise Ã  jour documentation post-implÃ©mentation |
| `/retrospective` | Analyse rÃ©trospective et amÃ©lioration continue |

### Codex / OpenAI

Si le support Codex a Ã©tÃ© scaffoldÃ© pour le projet, il inclut aussi :

- `AGENTS.md` â€” instructions runtime pour Codex/OpenAI
- `.agents/skills/ez-project-workflow` â€” rÃ¨gles de travail EzProject par dÃ©faut
- `.agents/skills/kickoff` â€” workflow d'interview kickoff
- `.agents/skills/generate-prp` â€” gÃ©nÃ©ration de PRP
- `.agents/skills/execute-prp` â€” exÃ©cution de PRP avec housekeeping
- `.agents/skills/review-code` â€” revue de code
- `.agents/skills/audit-project` â€” audit runtime/docs
- `.agents/skills/status` â€” snapshot rapide du projet
- `.agents/skills/housekeeping` â€” synchronisation de la documentation
- `.agents/skills/create-skill` â€” gÃ©nÃ©ration d'un skill Codex local au projet

## Project Structure

```
ai-patchlab/
â”œâ”€â”€ src/                 # Code source principal
â”‚   â””â”€â”€ main.py          # Point d'entrÃ©e
â”œâ”€â”€ tests/               # Tests pytest
â”œâ”€â”€ examples/            # Code patterns de rÃ©fÃ©rence
â”œâ”€â”€ PRPs/                # Product Requirements Prompts
â”œâ”€â”€ docs/                # Documentation technique
â”œâ”€â”€ .claude/             # Slash commands + subagents + settings
â”œâ”€â”€ .agents/             # Codex skills (optionnel, si scaffoldÃ©)
â”œâ”€â”€ AGENTS.md            # Instructions runtime Codex/OpenAI (optionnel)
â””â”€â”€ pyproject.toml       # Dependencies et config
```

## License

[REMPLIR â€” Private / MIT / etc.]
