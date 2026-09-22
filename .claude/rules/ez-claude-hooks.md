---
paths:
  - ".claude/hooks/**"
  - ".claude/settings.json"
  - ".claude/settings.local.json"
  - "template/.claude/hooks/**"
  - "template/.claude/settings.json"
  - "template/.claude/settings.local.json"
---

# Hooks & settings Claude Code

<!-- Template-owned (EzProject ADR-027): refreshed by ez-upgrade-project.ps1 on every upgrade, byte-identical to the template repo's root copy (tested). Edit it in the template, never in a project. -->

- `.claude/settings.json` = config partagée/committée (hooks + permissions + MCP); `.claude/settings.local.json` = overrides personnels uniquement — ne jamais mettre de hooks dans settings.local.json (perdus s'il est gitignoré, double-exécution s'ils sont aussi dans settings.json) — ADR-023
- Hooks qui appliquent une politique: **`exit 1` ne bloque RIEN** — Claude Code le traite comme une erreur non bloquante et exécute l'action quand même. Utiliser `permissionDecision: "deny"|"ask"` en JSON sur stdout (ou `exit 2`) — ADR-024
- **`jq` n'est pas installé sur Windows** — ne jamais l'utiliser dans une commande de hook: la substitution retourne vide, la condition ne matche jamais, et le hook devient inerte **sans aucune erreur visible**. Parser le JSON stdin en Python (`.claude/hooks/*.py`) — ADR-024
- **`$CLAUDE_FILE` n'existe pas.** Claude Code définit `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_EFFORT` — rien d'autre. Un hook qui teste `$CLAUDE_FILE` est du code mort qui a l'air vivant. Le chemin du fichier écrit est dans le payload stdin: `tool_input.file_path` — ADR-024
- Chemin d'un hook: **toujours** `python "${CLAUDE_PROJECT_DIR}/.claude/hooks/x.py"`, jamais relatif. Les hooks tournent dans le cwd *courant*; un interpréteur qui ne trouve pas son script sort **2** = le code bloquant. Un chemin relatif dans un hook PreToolUse/Bash bloque donc **toutes** les commandes dès que le cwd sort du projet (ex: working directories additionnels) — ADR-024
