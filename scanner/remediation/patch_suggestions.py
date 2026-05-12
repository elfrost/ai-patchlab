"""Deterministic patch suggestions for known vulnerability patterns."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace

from scanner.models import Finding


@dataclass(frozen=True)
class PatchSuggestion:
    """Concise before/after guidance for a remediation pattern."""

    patch_before: str
    patch_after: str
    remediation_explanation: str


@dataclass(frozen=True)
class PatchSuggestionRule:
    """Rule wrapper kept small so future providers can share the same contract."""

    name: str
    matches: Callable[[str], bool]
    suggestion: PatchSuggestion


WILDCARD_CORS_SUGGESTION = PatchSuggestion(
    patch_before='CORS(app, origins="*")',
    patch_after='CORS(app, origins=["https://app.example.com"])',
    remediation_explanation=(
        "Wildcard CORS allows any origin to read browser responses. Restrict origins to "
        "trusted frontend domains."
    ),
)
SUBPROCESS_SHELL_SUGGESTION = PatchSuggestion(
    patch_before='subprocess.run(f"git log {branch}", shell=True)',
    patch_after='subprocess.run(["git", "log", branch], check=True)',
    remediation_explanation=(
        "Passing arguments as a list avoids shell interpretation. Validate or allowlist any "
        "user-controlled values before execution."
    ),
)
SQL_INJECTION_SUGGESTION = PatchSuggestion(
    patch_before='cursor.execute("SELECT * FROM users WHERE id = " + user_id)',
    patch_after='cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))',
    remediation_explanation=(
        "Parameterized queries keep user input separate from SQL syntax and prevent injection."
    ),
)
GITHUB_TOKEN_SUGGESTION = PatchSuggestion(
    patch_before='GITHUB_TOKEN = "ghp_redacted"',
    patch_after='GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]',
    remediation_explanation=(
        "Revoke the exposed GitHub token, remove it from source code, and load it from "
        "environment variables or a secret manager."
    ),
)
HARDCODED_SECRET_SUGGESTION = PatchSuggestion(
    patch_before='STRIPE_API_KEY = "sk_live_redacted"',
    patch_after='STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]',
    remediation_explanation=(
        "Move secrets out of source code, rotate exposed values, and load them from environment "
        "variables or a secret manager."
    ),
)
CREDENTIAL_LOGGING_SUGGESTION = PatchSuggestion(
    patch_before='logger.info("login failed for %s with password %s", user, password)',
    patch_after='logger.info("login failed for %s", user)',
    remediation_explanation="Logs are often widely retained and searched. Remove sensitive fields and redact tokens, passwords, and secrets before logging.",
)


PATCH_SUGGESTION_RULES = (
    PatchSuggestionRule(
        name="credential_logging",
        matches=lambda text: _contains_any(
            text,
            (
                "logger-credential",
                "logger credential",
                "credential-disclosure",
                "credential disclosure",
                "logged",
                "logging",
                "logger call",
            ),
        )
        or (
            _contains_any(text, ("credential", "password", "secret", "token"))
            and _contains_any(text, (" log", "logging", "logger"))
        ),
        suggestion=CREDENTIAL_LOGGING_SUGGESTION,
    ),
    PatchSuggestionRule(
        name="github_token",
        matches=lambda text: _contains_any(
            text,
            (
                "github pat",
                "github personal access token",
                "personal access token",
                "ghp_",
                "github token",
            ),
        ),
        suggestion=GITHUB_TOKEN_SUGGESTION,
    ),
    PatchSuggestionRule(
        name="hardcoded_secret",
        matches=lambda text: _contains_any(
            text,
            (
                "hardcoded secret",
                "hard-coded secret",
                "api key",
                "apikey",
                "secret key",
                "stripe",
                "sk_live",
                "sk_test",
            ),
        )
        or ("gitleaks" in text and "secret" in text),
        suggestion=HARDCODED_SECRET_SUGGESTION,
    ),
    PatchSuggestionRule(
        name="sql_injection",
        matches=lambda text: _contains_any(
            text,
            (
                "sql injection",
                "sqli",
                "raw sql",
                "string concatenated sql",
                "string-concatenated sql",
                "sqlalchemy-execute-raw-query",
                "sqlalchemy execute raw query",
                "formatted-sql-query",
                "formatted sql query",
            ),
        ),
        suggestion=SQL_INJECTION_SUGGESTION,
    ),
    PatchSuggestionRule(
        name="subprocess_shell_true",
        matches=lambda text: "shell=true" in text
        or ("subprocess" in text and "shell true" in text),
        suggestion=SUBPROCESS_SHELL_SUGGESTION,
    ),
    PatchSuggestionRule(
        name="wildcard_cors",
        matches=lambda text: _contains_any(
            text,
            (
                "wildcard cors",
                "cors wildcard",
                "access control allow origin *",
                "allow origin *",
            ),
        )
        or ("cors" in text and "wildcard" in text),
        suggestion=WILDCARD_CORS_SUGGESTION,
    ),
)


def apply_patch_suggestions(findings: list[Finding]) -> list[Finding]:
    """Return findings enriched with deterministic patch suggestion fields."""
    return [apply_patch_suggestion(finding) for finding in findings]


def apply_patch_suggestion(finding: Finding) -> Finding:
    """Apply the first matching patch suggestion to a normalized finding."""
    suggestion = suggest_patch(finding)
    if suggestion is None:
        return finding

    return replace(
        finding,
        patch_before=suggestion.patch_before,
        patch_after=suggestion.patch_after,
        remediation_explanation=suggestion.remediation_explanation,
    )


def suggest_patch(finding: Finding) -> PatchSuggestion | None:
    """Return the deterministic patch suggestion for a finding, if known."""
    text = _match_text(finding)
    for rule in PATCH_SUGGESTION_RULES:
        if rule.matches(text):
            if rule.name == "credential_logging":
                return _credential_logging_suggestion_for(finding.description)
            return rule.suggestion
    return None


def _match_text(finding: Finding) -> str:
    raw_text = " ".join(
        [
            finding.id,
            finding.title,
            finding.tool,
            finding.description,
            finding.recommendation,
        ]
    ).lower()
    spaced_text = re.sub(r"[^a-z0-9*+=]+", " ", raw_text)
    return f"{raw_text} {spaced_text}"


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _credential_logging_suggestion_for(description: str) -> PatchSuggestion:
    if "STRIPE_API_KEY" in description or "JWT_SECRET" in description:
        return PatchSuggestion(
            patch_before='logger.info("Starting app with STRIPE_API_KEY=%s and JWT_SECRET=%s", STRIPE_API_KEY, JWT_SECRET)',
            patch_after='logger.info("Starting app")',
            remediation_explanation=CREDENTIAL_LOGGING_SUGGESTION.remediation_explanation,
        )
    if "Login attempt" in description:
        return PatchSuggestion(
            patch_before='logger.info("Login attempt username=%s password=%s api_key=%s", username, password, api_key)',
            patch_after='logger.info("Login attempt username=%s", username)',
            remediation_explanation=CREDENTIAL_LOGGING_SUGGESTION.remediation_explanation,
        )
    if "Issued JWT token" in description:
        return PatchSuggestion(
            patch_before='logger.info("Issued JWT token=%s signed_with=%s", token, JWT_SECRET)',
            patch_after='logger.info("Issued JWT token for user_id=%s", user_id)',
            remediation_explanation=CREDENTIAL_LOGGING_SUGGESTION.remediation_explanation,
        )
    if "Registered user" in description:
        return PatchSuggestion(
            patch_before='logger.info("Registered user username=%s email=%s password=%s", username, email, password)',
            patch_after='logger.info("Registered user username=%s email=%s", username, email)',
            remediation_explanation=CREDENTIAL_LOGGING_SUGGESTION.remediation_explanation,
        )
    return CREDENTIAL_LOGGING_SUGGESTION
