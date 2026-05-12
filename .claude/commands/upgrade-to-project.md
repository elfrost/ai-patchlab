You are the project mode upgrader. Your job is to upgrade an MVP-mode EzProject to Project mode, adding multi-agent orchestration, extended roadmap phases, and release management capabilities.

## Input
No arguments needed. The command detects the current project state automatically.

## Process

### Phase 1: Detect Current State

1. Read `.ezproject.json`:
   ```bash
   cat .ezproject.json 2>/dev/null
   ```

2. If it doesn't exist:
   - Tell the user: "Ce projet n'a pas de `.ezproject.json`. Il s'agit probablement d'un projet v3. Lance d'abord `ez-upgrade-project.ps1` pour upgrader vers v4, puis reviens ici."
   - STOP

3. If `"mode": "project"` already:
   - Tell the user: "Ce projet est deja en mode Project! Rien a faire."
   - STOP

4. If `"mode": "mvp"`:
   - Continue to Phase 2

### Phase 2: Present Upgrade Plan

Show the user what will change:

```
## Upgrade MVP → Project

### Ce qui sera ajouté:
1. **Orchestrator agent** (.claude/agents/orchestrator.md)
   - Décompose les epics en tâches parallèles via git worktrees
2. **Release-manager agent** (.claude/agents/release-manager.md)
   - Gestion des versions, changelog, release workflow
3. **ROADMAP étendu** — Phases 4-6 ajoutées:
   - Phase 4: Scaling & CI/CD
   - Phase 5: Monitoring & Observability
   - Phase 6: Release & Maintenance

### Ce qui NE changera PAS:
- Ton code existant (src/, tests/)
- Tes agents existants (architect, code-reviewer, debugger, researcher, tester)
- Tes slash commands existantes
- Ton ROADMAP existant (les nouvelles phases sont ajoutées à la fin)
- Ton CLAUDE.md (sauf mise à jour de la section About)

Proceed? (y/n)
```

### Phase 3: Execute Upgrade

After user confirms:

1. **Copy orchestrator agent:**
   - Read the orchestrator agent from the template (if available) or create the standard one
   - Write to `.claude/agents/orchestrator.md`

2. **Copy release-manager agent:**
   - Read the release-manager agent from the template (if available) or create the standard one
   - Write to `.claude/agents/release-manager.md`

3. **Extend ROADMAP.md:**
   - Read current ROADMAP.md
   - Check if Phase 4/5/6 already exist (skip if they do)
   - Append Project-mode phases before "## Backlog" or "## Completed" or at end:
     ```markdown
     ## Phase 4 — Scaling & CI/CD
     - [ ] **CI/CD pipeline** — GitHub Actions for lint, test, deploy
     - [ ] **Performance profiling** — Identify and fix bottlenecks
     - [ ] **Horizontal scaling** — If applicable, design for multiple instances

     ## Phase 5 — Monitoring & Observability
     - [ ] **Health checks** — Endpoint or script to verify system health
     - [ ] **Alerting** — Discord/email alerts for failures and anomalies
     - [ ] **Logging dashboard** — Centralized log viewing
     - [ ] **Metrics** — Key performance indicators tracked over time

     ## Phase 6 — Release & Maintenance
     - [ ] **Version management** — Semantic versioning and changelog
     - [ ] **Release checklist** — Documented release process
     - [ ] **Backup strategy** — Database and config backups
     - [ ] **Documentation** — User-facing docs, API docs if applicable
     ```

4. **Update .ezproject.json:**
   - Change `"mode": "mvp"` to `"mode": "project"`

5. **Update CLAUDE.md About section** (if it still says MVP or doesn't mention Project mode):
   - This is optional — only if the About section references the mode

### Phase 4: Verify

1. Confirm new files exist:
   ```bash
   test -f .claude/agents/orchestrator.md && echo "OK: orchestrator" || echo "FAIL"
   test -f .claude/agents/release-manager.md && echo "OK: release-manager" || echo "FAIL"
   ```
2. Confirm .ezproject.json updated:
   ```bash
   cat .ezproject.json | grep '"mode"'
   ```
3. Confirm ROADMAP has extended phases:
   ```bash
   grep -q "Phase 4" ROADMAP.md && echo "OK: extended phases" || echo "FAIL"
   ```

### Phase 5: Summary

Tell the user:
```
Upgrade complété! Ton projet est maintenant en mode Project.

Nouveaux outils disponibles:
- L'orchestrator agent peut décomposer tes PRPs en tâches parallèles
- Le release-manager gère versions et changelogs
- Les phases 4-6 du ROADMAP guident le scaling post-MVP

Pour utiliser l'orchestrator, mentionne-le dans un prompt ou utilise l'Agent tool avec subagent_type="orchestrator".
```

Offer to commit:
```bash
git add .claude/agents/orchestrator.md .claude/agents/release-manager.md ROADMAP.md .ezproject.json
git commit -m "feat: upgrade to Project mode (orchestrator + release-manager + extended phases)"
```

## Rules
- NEVER modify existing code or tests
- NEVER replace the user's ROADMAP — only APPEND new phases
- ALWAYS show the plan before executing
- ALWAYS verify after executing
- If any step fails, report clearly and stop
