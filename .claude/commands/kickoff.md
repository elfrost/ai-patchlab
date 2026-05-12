You are starting a new feature or project. Your job is to INTERVIEW the user, generate INITIAL.md, AND populate all project documentation files (CLAUDE.md, ROADMAP.md, README.md, DECISIONS.md) with real project-specific context.

## Process

### Phase 0: Mode & Stack Detection

Before starting the interview, check if the project has a `.ezproject.json` file:

```bash
cat .ezproject.json 2>/dev/null
```

**If `.ezproject.json` exists** — read its `mode` and `stack`:

- **Stack is one of `data | api | ai-agent | web`** → tell the user:
  "Je vois que le projet est configure en mode [mode] avec le stack [stack]. On continue avec ca?"
  Skip to Phase 1.

- **Stack is `auto` (with `stack_pending: true`)** → tell the user:
  "Le stack est en 'auto' — on va d'abord parler de ce que tu veux batir, puis je te recommanderai un stack base sur tes reponses."
  Set an internal flag `STACK_PENDING = true`. Skip Phase 0b. Run Phase 1, then **Phase 1.5 — Stack Advisor** (see below) before Phase 2.

**If `.ezproject.json` does NOT exist** (pre-v4 project or manual setup), ask:

**Question 0a — Le Mode:**
"On part en mode MVP (rapide, solo, ideal pour un prototype) ou en mode Projet complet (orchestration multi-agent, phases etendues, CI/CD)?"

If the user seems unsure, recommend MVP: "Si t'es pas sur, commence en MVP — tu pourras upgrade plus tard."

**Question 0b — Le Stack:**
"Quel stack preset tu veux?"
- **data** (default) — Python + MySQL + Playwright + aiomysql (scraping, data pipelines)
- **api** — Python + FastAPI + MySQL (API backends, web services)
- **ai-agent** — Python + PydanticAI + FastMCP (AI agents, tool-calling)
- **web** — Python + FastAPI + Jinja2 + MySQL (full-stack web apps, SSR or SPA)
- **Je sais pas** — set `STACK_PENDING = true` and run Phase 1.5 after the interview.

Save the chosen mode and stack for use in file generation.

### Phase 1: Discovery Interview

Ask these questions ONE AT A TIME. Wait for the answer before asking the next. Be conversational, not robotic.

**Question 1 — Le Quoi:**
"Decris-moi en quelques phrases ce que tu veux batir. Pas besoin d'etre technique — juste l'idee."

**Question 2 — Le Pourquoi:**
"C'est quoi le probleme que ca resout? Qui va l'utiliser?"

**Question 3 — Le Stack:**
"Quel tech stack tu veux utiliser? (Si t'es pas sur, je vais suggerer base sur le projet)"

**Skip Q3 if `STACK_PENDING = true`** — the stack will be decided in Phase 1.5 from the full interview.

Suggest based on the answer to Q1:
- Scraping → Python + Playwright + MySQL
- API/Backend → Python + FastAPI + MySQL
- Automation → Python + n8n + Discord
- Web app → Python + FastAPI + Jinja2/React/HTML (web stack)
- AI Agent → Python + PydanticAI + FastMCP

**Question 4 — Les Donnees:**
"D'ou viennent les donnees? (APIs, scraping, base de donnees existante, input utilisateur, fichiers)"

**Question 5 — Les Outputs:**
"Ca sort ou le resultat? (Discord alerts, dashboard web, fichier, base de donnees, email, API)"

**Question 6 — Les Contraintes:**
"Y a-t-il des contraintes que je dois connaitre? (rate limits, budget, APIs payantes, deadlines, integrations existantes)"

**Question 7 — Le Scope:**
"Pour le MVP, c'est quoi le minimum qui te rendrait content? Oublie le 'nice to have' — juste le core."

**Question 8 — L'Environnement:**
"Tu developpes ou et tu deploies ou? (local, VPS, cloud, Docker, etc.) Est-ce que c'est un projet standalone ou il fait partie d'un ecosysteme?"

### Phase 1.5: Stack Advisor (only if STACK_PENDING)

**Skip this phase entirely if `STACK_PENDING` is false.** Otherwise, run it before Phase 2.

The 4 stacks available are:
- **data** — Python + MySQL + Playwright + aiomysql. Fits: scraping, ETL, parsing files (PDF/CSV), pushing to a DB or sheet.
- **api** — Python + FastAPI + MySQL. Fits: REST endpoints, webhooks, services consumed by clients you don't control.
- **ai-agent** — Python + PydanticAI + FastMCP. Fits: LLM agents, tool-calling, MCP servers, autonomous decision-making.
- **web** — Python + FastAPI + Jinja2 + MySQL. Fits: server-rendered web app with login/sessions, dashboards, HTMX-style interactivity.

**Step 1 — Score the answers.** Read Q1 (what), Q4 (data sources), Q5 (outputs), Q7 (MVP) and award points to each stack:

| Signal in answers | +data | +api | +ai-agent | +web |
|---|---|---|---|---|
| "scrape", "parse", "PDF/CSV/Excel/relevés", "extract from files" | +3 | | | |
| "MySQL", "database storage", "push to sheet/spreadsheet" | +2 | +1 | | +1 |
| "REST endpoint", "API for X", "webhook receiver", "expose for clients" | | +3 | | |
| "LLM", "GPT", "Claude", "agent", "tool-calling", "categorize intelligently" | | | +3 | |
| "MCP server", "give Claude/Codex access to" | | | +3 | |
| "dashboard", "UI", "form", "login", "user-facing web page" | | | | +3 |
| "Discord webhook", "alert", "notification only" (no UI) | +1 | | | |
| "automation", "scheduled job", "cron" | +1 | | | |

**Step 2 — Pick primary + optional secondary.**
- Primary = highest-scoring stack.
- If a second stack is within 1 point of the primary AND addresses a distinct concern (e.g., `data` for the pipeline + `ai-agent` for intelligent categorization), flag it as a **secondary**.
- Common hybrids to recognize:
  - **Statements/receipts → spreadsheet with auto-categorization** = `data` (primary, parsing + sheet write) + `ai-agent` patterns (categorization)
  - **Internal admin dashboard backed by scraped data** = `web` (primary) + `data` patterns (scraper)
  - **API that wraps an LLM agent** = `api` (primary, exposed surface) + `ai-agent` patterns (the agent itself)

**Step 3 — Recommend.** Tell the user, in French:

> "D'apres ce que tu m'as dit, je recommande **`<primary>`**.
> Pourquoi: [1-2 phrases concretes citant les reponses, ex: 'tu parses des relevés PDF et tu écris dans un sheet — c'est exactement le pattern data avec aiomysql en option']
> [Si secondaire:] On va aussi cherry-pick quelques patterns de **`<secondary>`** pour [reason].
> Ca te va, ou tu veux qu'on parte sur autre chose? (data | api | ai-agent | web)"

Wait for user confirmation. If they push back, listen to why and reconsider — don't argue. The user knows their context better than the heuristics.

**Step 4 — Apply the stack.** Once confirmed, run the finalize script:

```bash
# Read ezproject_root from .ezproject.json (recorded by ez-new-project.ps1 at scaffold time)
EZ_ROOT=$(python -c "import json; print(json.load(open('.ezproject.json'))['ezproject_root'])")
powershell -ExecutionPolicy Bypass -File "$EZ_ROOT/ez-finalize-stack.ps1" -ProjectPath "$(pwd)" -Stack <chosen-stack>
```

This installs stack-specific deps in `pyproject.toml`, copies the right `examples/`, adjusts `.mcp.json`, and updates `.ezproject.json` (`stack: auto` → `stack: <chosen>`).

If the user picked a hybrid, **after** the finalize script, also cherry-pick the secondary's most relevant example file(s) by hand:

```bash
EZ_ROOT=$(python -c "import json; print(json.load(open('.ezproject.json'))['ezproject_root'])")
cp "$EZ_ROOT/template/examples/<secondary>/<file>.py" examples/
```

Pick at most 1-2 secondary files — the goal is patterns to reference, not bulk.

Update `STACK = <chosen>` for the rest of the kickoff (used in CLAUDE.md / INITIAL.md / DECISIONS.md generation).

### Phase 2: Codebase Research

After the interview, BEFORE writing any files:

1. Read CLAUDE.md for project standards (identify all `[REMPLIR]` placeholders)
2. If `AGENTS.md` exists, read it too so both runtimes stay aligned
3. Read ROADMAP.md (identify generic phases to replace)
4. Read README.md (identify `[REMPLIR]` placeholders)
5. Read DECISIONS.md (check existing ADRs)
6. Explore the codebase (if it exists) for:
   - Existing patterns to reference
   - Files that might be affected
   - Dependencies already in use
7. Check examples/ for available patterns
8. If the user mentioned specific APIs/services, research their constraints (rate limits, pricing, auth requirements)

### Phase 3: Generate ALL Project Files

Based on the interview answers and research, generate/update ALL of the following files. This is CRITICAL — do not skip any file.

#### 3A: Write INITIAL.md

Write it to `INITIAL.md` using this structure:

```markdown
# Feature Request: [Clear Name]

## FEATURE:
[Comprehensive description synthesized from answers to Q1, Q2, Q7]
[Be SPECIFIC — include exact behaviors, not vague goals]
[End with: "MVP first — keep it simple."]

## EXAMPLES:
[Reference files from examples/ that match patterns needed]
[If the project has existing code, reference those files too]
- `examples/[pattern].py` — [why this pattern applies]

## DOCUMENTATION:
[URLs for APIs, libraries, and references needed]
[If user mentioned specific services, include their docs]

## TECH STACK:
[From Q3, refined based on what makes sense]

## DATA FLOW:
[From Q4 → processing → Q5]
[Simple diagram using text:]
[Source] → [Processing] → [Storage] → [Output]

## CONSTRAINTS:
[From Q6 — rate limits, budget, integrations]

## MVP SCOPE:
[From Q7 — the minimum viable feature set]
[Numbered list, max 5 items]

## OUT OF SCOPE (for now):
[Things mentioned but explicitly deferred to later]

## SUCCESS CRITERIA:
[How do we know this works? Measurable outcomes]
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]
```

#### 3B: Update CLAUDE.md

Read the current CLAUDE.md and replace ALL `[REMPLIR]` placeholders with real project context:

1. **About section** — Replace `[REMPLIR — Description du projet en 2-3 phrases]` with a real description from Q1/Q2. Include mode and stack info if known (e.g., "Mode: MVP, Stack: data").
2. **Tech Stack section** — Update with the actual stack from Q3 (add project-specific libraries, remove irrelevant ones). Add a Deployment subsection from Q8 if relevant.
3. **Key Directories section** — Update if the project will use directories not in the template (e.g., `src/clients/`, `src/scrapers/`, `src/api/`)
4. **Architecture Decisions section** — Replace `[REMPLIR — Lister les decisions cles]` with initial decisions made during the interview (e.g., choice of API vs scraping, DB schema strategy, etc.)
5. **Known Gotchas section** — Replace `[REMPLIR — Rate limits d'APIs, bugs connus]` with actual constraints from Q6 (API rate limits, platform restrictions, auth requirements, deployment gotchas from Q8)

DO NOT rewrite the entire CLAUDE.md. Only replace `[REMPLIR]` placeholders and update sections that need project-specific content. Keep all generic rules, coding standards, and procedures intact.

If `AGENTS.md` exists, mirror the equivalent project-specific updates there too so Codex and Claude share the same project understanding.

#### 3C: Update ROADMAP.md

Replace the generic Phase 1-3 sections with real project phases:

1. Keep **Phase 0 — Bootstrap** as-is (already completed)
2. Replace **Phase 1 — Setup & Foundation** with the actual foundation tasks for this project
3. Replace **Phase 2 — Core MVP** with the actual MVP features from Q7
4. Replace **Phase 3 — Polish & Deploy** with real deployment/polish tasks
5. Add additional phases if the project has a clear progression path
6. Replace **Backlog** `[Features futures ici]` with actual future features from "OUT OF SCOPE"

Each roadmap item should be specific and actionable, not generic.

#### 3D: Update README.md

1. Replace `[REMPLIR — Description du projet en 1-2 phrases]` with a real project description
2. Update the Project Structure section if directories differ from template
3. Update Quick Start if there are project-specific setup steps
4. Replace `[REMPLIR]` in License section (ask user if unsure — default to "Private")

#### 3E: Update DECISIONS.md (if applicable)

If `STACK_PENDING` was true and the advisor picked a stack in Phase 1.5, **always** add an ADR for that choice (the rationale is project-defining and shouldn't be lost):

```markdown
### ADR-001: Stack choice — [chosen stack]
**Date:** [today]
**Status:** accepted
**Decision:** Use the `[chosen]` stack [+ cherry-picked patterns from `[secondary]` if hybrid].
**Context:** Selected via /kickoff Phase 1.5 stack advisor. Project does [Q1 summary]; data flow is [Q4 → Q5]. Heuristic signals: [list 2-3 concrete signals from the answers].
**Consequences:** [What this means: deps installed, examples available, MCP servers active. Mention any secondary patterns cherry-picked.]
```

If architectural decisions were made during the interview (e.g., "use API X instead of scraping", "platform-agnostic schema", "specific library choice"), add them as new ADR entries:

```markdown
### ADR-XXX: [Decision title]
**Date:** [today]
**Status:** accepted
**Decision:** [One sentence]
**Context:** [Why this was decided during kickoff]
**Consequences:** [What this means for implementation]
```

### Phase 4: Confirmation

After generating ALL files, present a summary:

"Voici ce que j'ai genere/mis a jour:

**INITIAL.md** — [1-line summary of feature request]
**CLAUDE.md** — Sections mises a jour: [list sections changed]
**AGENTS.md** — [updated in parallel / not present]
**ROADMAP.md** — [X] phases avec [Y] items specifiques au projet
**README.md** — Description et structure mises a jour
**DECISIONS.md** — [X] nouvelles decisions ajoutees

Lis les fichiers et dis-moi si:
1. J'ai bien compris ce que tu veux
2. Il manque quelque chose d'important
3. Le scope MVP est correct

Je peux ajuster avant qu'on passe au /generate-prp."

### Phase 5: Commit

After the user confirms, commit all changes:

```bash
git add INITIAL.md CLAUDE.md ROADMAP.md README.md DECISIONS.md
# If present: git add AGENTS.md
git commit -m "docs: initialize project context from kickoff interview"
```

### Phase 6: Suggest Next Step

After the commit succeeds, end the conversation with this exact message:

```
Project initialized. **Next step:**
- `/generate-prp INITIAL.md` — turn the feature spec into an implementation plan
- `/next` — context-aware advice based on the current state
- `/do "<describe what you want>"` — natural-language routing if you prefer

Throughout the project lifecycle, run `/next` any time you're not sure what to do — it reads the project state and recommends the best next command.
```

## IMPORTANT RULES
- Ask questions ONE AT A TIME — don't dump all at once
- Use French (quebecois) for the conversation
- Be concise in your questions
- If the user's answer is vague, ask a follow-up to clarify BEFORE moving on
- The file content should be in English (for Claude Code compatibility)
- Always include "MVP first — keep it simple" to prevent over-engineering
- Reference real files from examples/ and the codebase, not hypothetical ones
- NEVER leave `[REMPLIR]` placeholders in any file after kickoff is complete
- Every file must contain real, project-specific content when kickoff finishes
