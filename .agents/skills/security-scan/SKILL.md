---
name: security-scan
description: Comprehensive security audit — OWASP top 10, secrets, vulnerable deps, injection patterns. Combines Claude's two-stage Karpathy pipeline (researcher + security-auditor per ADR-016) into one inline pass.
---

# Security Scan

Inline two-stage scan: gather candidates first (mechanical grep), then judge severity and propose fixes.

## Phase 1: Gather candidates
Default scope: `src/` and `tests/` (or `$ARGUMENTS` if provided). Grep for:
- Unsafe `eval` / `exec` calls
- SQL string concatenation (f-strings or `%` formatting in queries)
- Hardcoded credentials, API keys, passwords, tokens
- Unsanitized user input flowing into shell or SQL
- HTTP requests without TLS verification (`verify=False`)
- Insecure deserialization (`pickle.load`, `yaml.load` without `SafeLoader`)
- Missing CSRF / auth on API routes (api / web stacks)
- Hardcoded production hostnames or paths

Plus:
- Read `.env.example` — flag any non-placeholder values (real secrets leaked)
- Scan recent git history:
  ```
  git log --all -p -S "password" --since="30 days ago" 2>&1 | head -50
  git log --all -p -S "api_key" --since="30 days ago" 2>&1 | head -50
  git log --all -p -S "secret" --since="30 days ago" 2>&1 | head -50
  ```
- Run `pip-audit 2>&1` if available (else suggest installing it)

## Phase 2: Judge severity
For each candidate:
- Assess severity: CRITICAL / HIGH / MEDIUM / LOW
- Filter false positives (test fixtures, examples, intentional patterns)
- Determine real exploitability
- Propose a concrete fix (not a high-level recommendation)

## Phase 3: Report + act
Produce a structured report grouped by severity. Then:
- For CRITICAL: propose immediate fixes (do NOT apply without user confirmation)
- For HIGH: suggest adding to project TODO
- For MEDIUM/LOW: report only

## Rules
- Always check `.env.example` for leaked real values
- Always scan recent git history for committed secrets
- Run `pip-audit` if available
- Do NOT modify code without user confirmation
- Report findings even if you suspect false positives — show your work in Phase 2
