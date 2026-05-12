Analyze recent work and suggest improvements to the project and template.

Optional argument: $ARGUMENTS

## Modes

This command runs in one of two modes depending on $ARGUMENTS:

- **Sprint mode** (no argument or `sprint`) — broad retrospective over the last ~2 weeks. Use periodically to find patterns across many features.
- **Self-healing mode** (`last` or a PRP name like `feature-name` or `PRPs/done/20260425-feature.md`) — focused review of ONE recent implementation. Use right after `/execute-prp` finishes, in a fresh Claude Code context window. Inspired by the "self-healing layer" pattern: when something was painful in this implementation, fix the underlying system (CLAUDE.md, skills, examples, agents) so the next implementation doesn't hit it again.

If `$ARGUMENTS` is empty, default to **sprint mode**.

---

## Self-Healing Mode (focused on one PRP)

Run this in a fresh context — separate from the conversation that did the implementation. The implementer is biased about its own work; a clean reader catches more.

### Step 1: Identify the target

- If $ARGUMENTS is `last`, find the most recently archived PRP: `ls -t PRPs/done/ | head -1`
- If $ARGUMENTS is a PRP name or path, use it directly
- Read the PRP completely

### Step 2: Compare plan vs reality

```bash
# Find the implementation commits for this PRP
git log --oneline --since="3 days ago" | head -20

# What files actually changed?
git log --since="3 days ago" --name-only --pretty=format: | sort -u | grep -v "^$"
```

Compare against the PRP's "Files to create/modify" section. Note any deviations.

### Step 3: Find the friction signals

Look at git history for this PRP's commits:

- **fix: commits right after feat: commits** → implementation needed touch-ups → why?
- **Many small commits on the same file** → instability → why?
- **Commits that revert or rework earlier work in the same PRP** → planning gap → why?

### Step 4: Categorize each friction point

For each painful moment in this PRP, ask: **what could we have put in CLAUDE.md / skills / examples / agents to prevent this?**

Possible root causes:
- Missing rule in `CLAUDE.md` (gotcha not documented, convention unclear)
- Missing pattern in `examples/` (had to invent something that should be reusable)
- Skill or command was too vague (workflow needs more steps)
- Agent prompt didn't have enough context
- PRP template missing a section
- Validation gate wasn't strict enough (let a bad pattern through)

### Step 5: Output — concrete AI-layer improvements

```
## Self-Healing Retrospective — [PRP name]

### Plan vs Reality
- Files planned: X | Files actually changed: Y
- Deviations: [list any unplanned changes, or "none"]

### Friction signals
- [Specific painful moment 1]
  - Root cause: [missing rule / pattern / skill detail / etc.]
  - Fix: [concrete change to CLAUDE.md / skills / examples / agent prompt]
- [Specific painful moment 2]
  - Root cause: ...
  - Fix: ...

### Proposed AI-layer changes
- [ ] **[file path]** — [exact addition/edit, e.g. "add gotcha about aiomysql pool cleanup to Known Gotchas section"]
- [ ] **examples/[name].py** — [pattern to extract, with one-line description]
- [ ] **.claude/commands/[name].md** — [step to add, with location]
- [ ] **.claude/agents/[name].md** — [prompt clarification]

### What worked well (do NOT change)
- [Aspect that went smoothly — confirm and keep as-is]
```

### Self-Healing Rules
- Be specific — no "improve documentation" vibes; say which file, which section, what to add
- Only flag an improvement if you can name the next bug it prevents
- If nothing went wrong, output "Implementation was clean, no AI-layer changes needed" and stop
- Do NOT propose changes that contradict existing ADRs without explicit reasoning
- Apply changes ONLY if the user accepts — never silently edit CLAUDE.md/skills/examples

---

## Sprint Mode (broad retrospective over ~2 weeks)

### Phase 1: Gather Data

1. **Read ROADMAP.md** — what was completed recently?
2. **Read DECISIONS.md** — what decisions were made?
3. **Check git history:**
   ```bash
   git log --oneline -30 --since="2 weeks ago"
   git log --oneline -30 --since="2 weeks ago" | grep -c "fix:"
   git log --oneline -30 --since="2 weeks ago" | grep -c "feat:"
   git log --oneline -30 --since="2 weeks ago" | grep -c "refactor:"
   ```
4. **Check PRPs done:**
   ```bash
   ls PRPs/done/ 2>/dev/null
   ls PRPs/ 2>/dev/null
   ```
5. **Check code quality:**
   ```bash
   ruff check src/ 2>&1 | tail -5
   find src/ -name "*.py" -exec wc -l {} + | sort -n | tail -10
   ```
6. **Check test coverage trend:**
   ```bash
   find tests/ -name "*.py" -not -name "__init__.py" -not -name "conftest.py" | wc -l
   pytest tests/ -v --tb=no 2>&1 | tail -5
   ```

### Phase 2: Analyze Patterns

Look for:

**What went well?**
- Features completed smoothly (feat: commits without immediate fix: commits)
- Good test coverage on new code
- Clean PRPs that worked in one pass

**What was painful?**
- Features that required many fix: commits after initial implementation
- Files that were modified many times (unstable code):
  ```bash
  git log --since="2 weeks ago" --name-only --pretty=format: | sort | uniq -c | sort -rn | head -10
  ```
- Tests that break often
- Patterns that were confusing or poorly documented

**What's missing?**
- Code without tests
- Repeated patterns that should be in examples/
- Decisions not documented in DECISIONS.md
- Files over 300 lines (need splitting)

### Phase 3: Generate Recommendations

Categorize recommendations:

1. **Process improvements** — changes to how we work
2. **Code improvements** — refactoring opportunities
3. **Documentation gaps** — things that should be documented
4. **Template improvements** — patterns/commands to add to EzProject template
5. **Technical debt** — things to fix before they become problems

### Sprint Output Format

```
## Rétrospective — [date range]

### Résumé
- Features complétées: X
- Bugs fixés: Y
- Refactoring: Z
- Fichiers les plus modifiés: [list]

### ✅ Ce qui a bien marché
- [Item 1]
- [Item 2]

### ⚠️ Ce qui était difficile
- [Item 1] — Suggestion: [improvement]
- [Item 2] — Suggestion: [improvement]

### 🔧 Améliorations suggérées

#### Process
- [ ] [Improvement 1]

#### Code
- [ ] [Refactoring opportunity]

#### Documentation
- [ ] [Missing docs]

#### Template (EzProject)
- [ ] [Pattern/command to add]

#### Dette technique
- [ ] [Tech debt item]

### 📊 Métriques santé
- Source files: X (total Y lines)
- Test files: X
- Lint issues: X
- Files > 300 lines: [list or "none"]
- Commit ratio: X feat / Y fix / Z refactor
```

## Rules (both modes)
- Be honest — point out real issues, not theoretical ones
- Focus on ACTIONABLE items — each suggestion should be something concrete to do
- Prioritize by impact — what would improve quality the most?
- Keep it concise — no essays, bullet points only
- If the project is new (few commits), focus on setup quality and patterns
- **Always run in a fresh context** — never review work in the same conversation that produced it (the writer is biased about its own output)
