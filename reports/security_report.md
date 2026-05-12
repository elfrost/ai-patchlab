# AI PatchLab Security Report

Repository: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo`
Generated at: `2026-05-12T18:11:25.111011+00:00`

## Summary

| Severity | Findings |
| --- | ---: |
| Critical | 0 |
| High | 5 |
| Medium | 6 |
| Low | 0 |
| Info | 3 |

## Findings

### Critical

No findings.

### High

#### generic.secrets.security.detected-stripe-api-key.detected-stripe-api-key

- ID: `semgrep-generic.secrets.security.detected-stripe-api-key.detected-stripe-api-key-C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\config.py-8`
- Tool: `semgrep`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\config.py`
- Line: `8`
- Confidence: `medium`
- Description: Stripe API Key detected
- Recommendation: Rotate the exposed secret, remove it from source code, move it to environment variables, and rewrite git history if committed.
- Patch suggestion:

  Before:

  ```text
  STRIPE_API_KEY = "sk_live_redacted"
  ```

  After:

  ```text
  STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]
  ```

- Remediation explanation: Move secrets out of source code, rotate exposed values, and load them from environment variables or a secret manager.

#### python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query

- ID: `semgrep-python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query-C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py-90`
- Tool: `semgrep`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py`
- Line: `90`
- Confidence: `medium`
- Description: Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy provides TextualSQL to easily used prepared statement with named parameters. For complex SQL composition, use SQL Expression Language or Schema Definition Language. In most cases, SQLAlchemy ORM will be a better option.
- Recommendation: Replace string-concatenated SQL with parameterized queries or SQLAlchemy ORM bindings.
- Patch suggestion:

  Before:

  ```text
  cursor.execute("SELECT * FROM users WHERE id = " + user_id)
  ```

  After:

  ```text
  cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
  ```

- Remediation explanation: Parameterized queries keep user input separate from SQL syntax and prevent injection.

#### python.lang.security.audit.subprocess-shell-true.subprocess-shell-true

- ID: `semgrep-python.lang.security.audit.subprocess-shell-true.subprocess-shell-true-C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py-99`
- Tool: `semgrep`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py`
- Line: `99`
- Confidence: `medium`
- Description: Found 'subprocess' function 'check_output' with 'shell=True'. This is dangerous because this call will spawn the command using a shell process. Doing so propagates current shell settings and variables, which makes it much easier for a malicious actor to execute commands. Use 'shell=False' instead.
- Recommendation: Avoid shell=True. Pass command arguments as a list and validate/allowlist user-controlled input.
- Patch suggestion:

  Before:

  ```text
  subprocess.run(f"git log {branch}", shell=True)
  ```

  After:

  ```text
  subprocess.run(["git", "log", branch], check=True)
  ```

- Remediation explanation: Passing arguments as a list avoids shell interpretation. Validate or allowlist any user-controlled values before execution.

#### Potential secret detected: stripe-access-token

- ID: `C:/Users/Elfrost/OneDrive/NetProject/EzWebSolution/vulnerable-api-demo/app/config.py:stripe-access-token:8`
- Tool: `gitleaks`
- File: `C:/Users/Elfrost/OneDrive/NetProject/EzWebSolution/vulnerable-api-demo/app/config.py`
- Line: `8`
- Confidence: `high`
- Description: Found a Stripe Access Token, posing a risk to payment processing services and sensitive financial data.
- Recommendation: Rotate the exposed secret, remove it from source code, move it to environment variables, and rewrite git history if committed.
- Patch suggestion:

  Before:

  ```text
  STRIPE_API_KEY = "sk_live_redacted"
  ```

  After:

  ```text
  STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]
  ```

- Remediation explanation: Move secrets out of source code, rotate exposed values, and load them from environment variables or a secret manager.

#### Potential secret detected: github-pat

- ID: `C:/Users/Elfrost/OneDrive/NetProject/EzWebSolution/vulnerable-api-demo/app/config.py:github-pat:11`
- Tool: `gitleaks`
- File: `C:/Users/Elfrost/OneDrive/NetProject/EzWebSolution/vulnerable-api-demo/app/config.py`
- Line: `11`
- Confidence: `high`
- Description: Uncovered a GitHub Personal Access Token, potentially leading to unauthorized repository access and sensitive content exposure.
- Recommendation: Revoke the exposed GitHub personal access token, remove it from source code, move it to environment variables, and rewrite git history if committed.
- Patch suggestion:

  Before:

  ```text
  GITHUB_TOKEN = "ghp_redacted"
  ```

  After:

  ```text
  GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
  ```

- Remediation explanation: Revoke the exposed GitHub token, remove it from source code, and load it from environment variables or a secret manager.

### Medium

#### python.fastapi.security.wildcard-cors.wildcard-cors

- ID: `semgrep-python.fastapi.security.wildcard-cors.wildcard-cors-C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py-30`
- Tool: `semgrep`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py`
- Line: `30`
- Confidence: `medium`
- Description: CORS policy allows any origin (using wildcard '*'). This is insecure and should be avoided.
- Recommendation: Replace wildcard origins with an explicit allowlist of trusted frontend domains.
- Patch suggestion:

  Before:

  ```text
  CORS(app, origins="*")
  ```

  After:

  ```text
  CORS(app, origins=["https://app.example.com"])
  ```

- Remediation explanation: Wildcard CORS allows any origin to read browser responses. Restrict origins to trusted frontend domains.

#### python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure

- ID: `semgrep-python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure-C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py-40`
- Tool: `semgrep`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py`
- Line: `40`
- Confidence: `medium`
- Description: Detected a python logger call with a potential hardcoded secret "Starting app with STRIPE_API_KEY=%s and JWT_SECRET=%s" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.
- Recommendation: Remove secrets/passwords/tokens from logs and add redaction for sensitive fields.
- Patch suggestion:

  Before:

  ```text
  logger.info("Starting app with STRIPE_API_KEY=%s and JWT_SECRET=%s", STRIPE_API_KEY, JWT_SECRET)
  ```

  After:

  ```text
  logger.info("Starting app")
  ```

- Remediation explanation: Logs are often widely retained and searched. Remove sensitive fields and redact tokens, passwords, and secrets before logging.

#### python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure

- ID: `semgrep-python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure-C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py-51`
- Tool: `semgrep`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py`
- Line: `51`
- Confidence: `medium`
- Description: Detected a python logger call with a potential hardcoded secret "Login attempt username=%s password=%s api_key=%s" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.
- Recommendation: Remove secrets/passwords/tokens from logs and add redaction for sensitive fields.
- Patch suggestion:

  Before:

  ```text
  logger.info("Login attempt username=%s password=%s api_key=%s", username, password, api_key)
  ```

  After:

  ```text
  logger.info("Login attempt username=%s", username)
  ```

- Remediation explanation: Logs are often widely retained and searched. Remove sensitive fields and redact tokens, passwords, and secrets before logging.

#### python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure

- ID: `semgrep-python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure-C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py-54`
- Tool: `semgrep`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py`
- Line: `54`
- Confidence: `medium`
- Description: Detected a python logger call with a potential hardcoded secret "Issued JWT token=%s signed_with=%s" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.
- Recommendation: Remove secrets/passwords/tokens from logs and add redaction for sensitive fields.
- Patch suggestion:

  Before:

  ```text
  logger.info("Issued JWT token=%s signed_with=%s", token, JWT_SECRET)
  ```

  After:

  ```text
  logger.info("Issued JWT token for user_id=%s", user_id)
  ```

- Remediation explanation: Logs are often widely retained and searched. Remove sensitive fields and redact tokens, passwords, and secrets before logging.

#### python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure

- ID: `semgrep-python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure-C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py-70`
- Tool: `semgrep`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py`
- Line: `70`
- Confidence: `medium`
- Description: Detected a python logger call with a potential hardcoded secret "Registered user username=%s email=%s password=%s" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.
- Recommendation: Remove secrets/passwords/tokens from logs and add redaction for sensitive fields.
- Patch suggestion:

  Before:

  ```text
  logger.info("Registered user username=%s email=%s password=%s", username, email, password)
  ```

  After:

  ```text
  logger.info("Registered user username=%s email=%s", username, email)
  ```

- Remediation explanation: Logs are often widely retained and searched. Remove sensitive fields and redact tokens, passwords, and secrets before logging.

#### python.lang.security.audit.formatted-sql-query.formatted-sql-query

- ID: `semgrep-python.lang.security.audit.formatted-sql-query.formatted-sql-query-C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py-90`
- Tool: `semgrep`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo\app\main.py`
- Line: `90`
- Confidence: `medium`
- Description: Detected possible formatted SQL query. Use parameterized queries instead.
- Recommendation: Review the Semgrep rule guidance and update the affected code.
- Patch suggestion:

  Before:

  ```text
  cursor.execute("SELECT * FROM users WHERE id = " + user_id)
  ```

  After:

  ```text
  cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
  ```

- Remediation explanation: Parameterized queries keep user input separate from SQL syntax and prevent injection.

### Low

No findings.

### Info

#### Trivy placeholder

- ID: `trivy-placeholder`
- Tool: `trivy`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo`
- Line: `N/A`
- Confidence: `low`
- Description: Filesystem, container, or IaC scanning through Trivy is not implemented yet.
- Recommendation: Wire this placeholder to the real scanner and map results into the normalized finding schema.

#### Dependency scan placeholder

- ID: `dependency-scan-placeholder`
- Tool: `dependency-scan`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo`
- Line: `N/A`
- Confidence: `low`
- Description: Dependency vulnerability scanning is not implemented yet.
- Recommendation: Wire this placeholder to the real scanner and map results into the normalized finding schema.

#### AI security review placeholder

- ID: `ai-review-placeholder`
- Tool: `ai-security-review`
- File: `C:\Users\Elfrost\OneDrive\NetProject\EzWebSolution\vulnerable-api-demo`
- Line: `N/A`
- Confidence: `low`
- Description: AI-assisted review is not implemented yet and no paid API is called.
- Recommendation: Wire this placeholder to the real scanner and map results into the normalized finding schema.

## Normalized Finding Fields

`id`, `tool`, `severity`, `title`, `description`, `file`, `line`, `recommendation`, `confidence`, `patch_before`, `patch_after`, `remediation_explanation`
