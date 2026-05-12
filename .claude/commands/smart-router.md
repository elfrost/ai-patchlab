# /do — Smart Router

Describe what you want in natural language. The system analyzes your intent and routes to the best pipeline, command, or agent.

## Argument
`$ARGUMENTS` — Natural language description of what you want to accomplish.

## Process

### Phase 1: Analyze Intent
Read `$ARGUMENTS` and classify the user's intent into one of these categories:

| Intent | Indicators | Route To |
|--------|-----------|----------|
| **Fix a bug** | "fix", "bug", "error", "broken", "crash", "TypeError", "fails" | `/fix-issue` |
| **Build a feature** | "add", "create", "build", "implement", "new feature" | `/idea-to-pr` or `/generate-prp` |
| **Implement a PRP** | "execute PRP", "implement this PRP", "run PRP", "implement plan", "execute plan" | `/execute-prp` |
| **TDD discipline** | "TDD", "test first", "test-driven", "red green refactor", "tests before code" | `/tdd` |
| **Review code** | "review", "check code", "look at changes", "before commit" | `/review-code` |
| **Security audit** | "security", "vulnerable", "audit", "secrets", "OWASP" | `/security-scan` |
| **Refactor** | "refactor", "clean up", "simplify", "reduce complexity" | `/refactor` |
| **Check deps** | "dependencies", "outdated", "vulnerable packages", "update deps" | `/dependency-check` |
| **Write tests** | "test", "coverage", "write tests", "missing tests" | Spawn tester agent |
| **Debug** | "debug", "investigate", "why does", "trace", "diagnose" | Spawn debugger agent |
| **Research** | "research", "explore", "how does", "understand", "explain" | Spawn researcher agent |
| **Architecture** | "design", "architecture", "should I", "trade-offs", "evaluate" | Spawn architect agent |
| **Documentation** | "document", "docs", "README", "API reference", "explain code" | `/document` |
| **Performance** | "slow", "optimize", "performance", "bottleneck", "profile" | `/performance` |
| **Run pipeline** | "pipeline", "run workflow", "full process" | `/pipeline` |
| **Project status** | "status", "where are we", "progress", "what's done" | `/status` |
| **Release** | "release", "version", "deploy", "tag", "changelog" | `/pipeline release` |
| **Monitoring** | "monitor", "health check", "alerting", "uptime" | `/monitor-setup` |
| **Cleanup** | "dead code", "unused", "clean", "remove clutter" | `/cleanup` |
| **Housekeeping** | "housekeeping", "update docs", "sync ROADMAP", "post-implementation tidy" | `/housekeeping` |
| **Audit CLAUDE.md** | "audit CLAUDE.md", "review CLAUDE.md", "claude.md drift", "is CLAUDE.md up to date" | `/audit-project` |
| **Retrospective** | "retrospective", "lessons learned", "what went wrong", "self-heal", "AI-layer drift" | `/retrospective` (warn user — best run in a fresh context) |
| **Rollback / Undo** | "undo", "revert", "rollback", "undo last change", "go back" | `/rollback` |
| **New slash command** | "create command", "create skill", "new slash command", "make a command for" | `/create-skill` |
| **What's next?** | "what now", "next step", "what should I do", "guide me", "I'm lost", "where am I", "what next" | `/next` |
| **Upgrade status** | "is my project up to date", "am I behind", "upgrade status", "what's new in template", "any new features" | `/upgrade-status` |

### Phase 2: Confirm Route
1. Display the detected intent and proposed action:
   ```
   Detected: [intent category]
   Action: [command/pipeline/agent to invoke]
   Input: [parsed context to pass]
   ```
2. Ask for confirmation (one-liner, not verbose):
   `Proceed? (y/n/change)`
3. If user says "change" or suggests different action, re-route

### Phase 3: Execute
1. Invoke the selected command/pipeline/agent with the parsed context
2. Pass `$ARGUMENTS` as input to the target

### Phase 4: Learn (optional)
If the user corrected the routing (Phase 2 "change"):
- Note: this is a signal that the routing heuristics should be refined
- The smart-context agent can pick this up in future runs

## Ambiguity Handling
If the intent is ambiguous (matches multiple categories equally):
1. Present the top 2-3 matches with brief explanation
2. Let user choose
3. Example:
   ```
   Your request could be:
   1. Bug fix → /fix-issue (you mentioned "error")
   2. Refactoring → /refactor (you mentioned "clean up")
   Which fits best? (1/2)
   ```

## Rules
- ALWAYS confirm before executing — never auto-route without showing the plan
- If intent is completely unclear, ask a clarifying question instead of guessing
- Prefer specific commands over generic ones (e.g., `/fix-issue` over spawning a debugger)
- Prefer pipelines over individual agents when the task is multi-step
- Pass the FULL user text as context to the target — don't truncate
- Keep routing fast — don't over-analyze, just classify and confirm
