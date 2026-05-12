# /idea-to-pr — End-to-End Feature Delivery

From a feature idea to a PR-ready branch in one command.
Shortcut for `/pipeline feature` with automatic branch creation and PR preparation.

## Argument
`$ARGUMENTS` — Feature description in natural language.

## Process

### Phase 1: Research
1. Read `$ARGUMENTS` — parse the feature description
2. Spawn **researcher** agent:
   - Multi-source research (codebase, examples, docs, web, git history)
   - Produce research brief with confidence score
3. If confidence < 6, ask user for clarification before proceeding
4. Create TodoWrite tracking: Research -> Design -> Implement -> Test -> Review -> PR

### Phase 2: Design
1. Spawn **architect** agent with research brief:
   - Evaluate design options
   - Produce architecture decision
   - List files to create/modify
   - Identify risks
2. Present design to user for approval (gate):
   ```
   ## Architecture Plan
   [architect output]

   Approve to proceed? (y/n)
   ```
3. If rejected, iterate with user feedback

### Phase 3: Branch Setup
1. Derive a short branch name from the feature description (lowercase, hyphens, max 40 chars):
   - e.g., "add health check endpoint" -> `feat/add-health-check-endpoint`
2. Create feature branch:
   ```bash
   git checkout -b feat/[short-name]
   ```

### Phase 4: Implement
**Check project mode** — read `.ezproject.json` for `"mode"` field.

**Project mode:**
1. Spawn **orchestrator** agent with architecture decision
2. Orchestrator decomposes into waves and executes in parallel
3. Loop-until-passing validation gates between waves

**MVP mode:**
1. Implement changes sequentially based on architecture decision
2. Validate after each file change:
   ```bash
   ruff check src/ tests/
   black --check src/ tests/
   ```
3. Commit progress incrementally

### Phase 5: Test & Review (parallel)
1. Spawn **tester** agent:
   - Write comprehensive tests
   - Coverage analysis with pytest-cov
   - Report results
2. Spawn **code-reviewer** agent (parallel with tester):
   - Multi-reviewer mode (5 sub-reviewers)
   - Synthesize findings
3. Address any CRITICAL or HIGH findings before proceeding

### Phase 6: Final Validation
1. Run full validation suite:
   ```bash
   ruff check src/ tests/
   black --check src/ tests/
   pytest tests/ -v
   ```
2. Loop-until-passing (max 3 retries):
   - If ruff fails: `ruff check src/ tests/ --fix`
   - If black fails: `black src/ tests/`
   - If pytest fails: spawn debugger

### Phase 7: PR Preparation
1. Commit all remaining changes:
   ```bash
   git add [specific files]
   git commit -m "feat: [description]"
   ```
2. Push branch to remote:
   ```bash
   git push -u origin feat/[short-name]
   ```
3. Generate PR description from:
   - Feature description (from $ARGUMENTS)
   - Architecture decisions made
   - Files created/modified
   - Test coverage achieved
   - Review summary
4. Create PR:
   ```bash
   gh pr create --title "[short title]" --body "[generated description]"
   ```
5. Return PR URL to user

## Rules
- ALWAYS get design approval before implementing
- ALWAYS create a feature branch — never work on main
- ALWAYS run full validation before PR creation
- If ANY step fails after retries, stop and ask user — don't create a broken PR
- PR description must include: what, why, how, test plan
- Do NOT merge the PR — only create it. User decides when to merge
- Keep branch name short and descriptive (max 40 chars after feat/)
- Commit messages follow project convention: `type: description`
