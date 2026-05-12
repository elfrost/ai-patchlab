# /security-scan — Full Security Audit

Run a comprehensive security audit on the project using a two-stage Karpathy-style pipeline (per ADR-016): the sonnet `researcher` does the breadth scan (find candidates with enough context), then the opus `security-auditor` judges severity and proposes fixes.

## Argument
`$ARGUMENTS` — Optional path to scan. Default: `src/` and `tests/`.

## Process

### Phase 1: Delegate breadth scan to `researcher` (sonnet)

Do NOT scan the codebase yourself in this context. Spawn the `researcher` subagent with a security-focused directive — heavy grep work on cheap tokens, main context stays free for coordination.

Use the Task tool with `subagent_type: "researcher"`. Pass it:
- Scope: `$ARGUMENTS` if provided, else `src/` + `tests/`
- An explicit list of patterns to grep for and report (file:line + sample, NO severity judgment — that's Phase 2):
  - Unsafe eval/exec calls
  - SQL string concatenation (f-strings or `%` formatting in queries)
  - Hardcoded credentials / API keys / passwords / tokens
  - Unsanitized user input flowing into shell or SQL
  - HTTP requests without TLS verification (`verify=False`)
  - Insecure deserialization (`pickle.load`, `yaml.load` without `SafeLoader`)
  - Missing CSRF / auth on API routes (api / web stacks)
  - Hardcoded production hostnames or paths
- Also: read `.env.example` and flag any non-placeholder values (leaked real secrets)
- Also: scan recent git history for committed secrets:
  ```bash
  git log --all -p -S "password" --since="30 days ago" 2>&1 | head -50
  git log --all -p -S "api_key" --since="30 days ago" 2>&1 | head -50
  git log --all -p -S "secret" --since="30 days ago" 2>&1 | head -50
  ```
- Also: run `pip-audit 2>&1` if available, capture output
- Confidence score with justification

The researcher returns a structured brief of raw candidates. It MUST NOT judge severity or filter false positives — that's the security-auditor's job in Phase 2.

**Hard gate:** if researcher's confidence < 5 (scope too vague, codebase unreadable, etc.), ask the user for clarification before proceeding.

### Phase 2: Delegate severity assessment to `security-auditor` (opus)

Spawn `security-auditor` with the researcher's brief verbatim.

Use the Task tool with `subagent_type: "security-auditor"`. Pass it:
- The researcher's full structured findings
- The git history excerpts and pip-audit output
- A directive: assess severity (CRITICAL / HIGH / MEDIUM / LOW), filter false positives, judge real exploitability, propose concrete fixes per finding

The security-auditor returns the final report — that's what goes to the user.

### Phase 3: Present + act

1. Show the security-auditor's report
2. For CRITICAL findings: propose immediate fixes with specific code changes (do NOT apply without user confirmation)
3. For HIGH findings: suggest adding to project TODO
4. Run `pip-audit` recommendation if not already installed: `pip install pip-audit`

## Rules
- ALWAYS delegate Phase 1 to `researcher` — do NOT scan inline in main context
- ALWAYS delegate Phase 2 to `security-auditor` — do NOT make severity calls in main context
- Do NOT modify code without user confirmation
- Report all findings (even likely false positives) — let security-auditor judge in Phase 2
