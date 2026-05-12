"""Deterministic recommendation enrichment for normalized findings."""

from __future__ import annotations

import re
from dataclasses import replace

from scanner.models import Finding

SECRET_RECOMMENDATION = (
    "Rotate the exposed secret, remove it from source code, move it to environment variables, "
    "and rewrite git history if committed."
)
GITHUB_PAT_RECOMMENDATION = (
    "Revoke the exposed GitHub personal access token, remove it from source code, move it to "
    "environment variables, and rewrite git history if committed."
)
SQL_INJECTION_RECOMMENDATION = (
    "Replace string-concatenated SQL with parameterized queries or SQLAlchemy ORM bindings."
)
SUBPROCESS_SHELL_RECOMMENDATION = (
    "Avoid shell=True. Pass command arguments as a list and validate/allowlist "
    "user-controlled input."
)
WILDCARD_CORS_RECOMMENDATION = (
    "Replace wildcard origins with an explicit allowlist of trusted frontend domains."
)
CREDENTIAL_LOGGING_RECOMMENDATION = (
    "Remove secrets/passwords/tokens from logs and add redaction for sensitive fields."
)


def enrich_findings(findings: list[Finding]) -> list[Finding]:
    """Return findings with only the recommendation field enriched."""
    return [enrich_finding(finding) for finding in findings]


def enrich_finding(finding: Finding) -> Finding:
    """Return a finding with a rule-based recommendation when a known pattern matches."""
    recommendation = recommend_for_finding(finding)
    if recommendation == finding.recommendation:
        return finding
    return replace(finding, recommendation=recommendation)


def recommend_for_finding(finding: Finding) -> str:
    """Choose the most specific deterministic recommendation for a finding."""
    text = _match_text(finding)

    if _is_credential_logging(text):
        return CREDENTIAL_LOGGING_RECOMMENDATION
    if _is_github_pat(text):
        return GITHUB_PAT_RECOMMENDATION
    if _is_secret_or_api_key(text):
        return SECRET_RECOMMENDATION
    if _is_sql_injection(text):
        return SQL_INJECTION_RECOMMENDATION
    if _is_subprocess_shell_true(text):
        return SUBPROCESS_SHELL_RECOMMENDATION
    if _is_wildcard_cors(text):
        return WILDCARD_CORS_RECOMMENDATION

    return finding.recommendation


def _match_text(finding: Finding) -> str:
    """Build searchable text from normalized rule, title, tool, and description fields."""
    raw_text = " ".join(
        [
            finding.id,
            finding.title,
            finding.tool,
            finding.description,
        ]
    ).lower()
    spaced_text = re.sub(r"[^a-z0-9*+=]+", " ", raw_text)
    return f"{raw_text} {spaced_text}"


def _is_github_pat(text: str) -> bool:
    return (
        "github pat" in text
        or "github personal access token" in text
        or ("github" in text and "personal access token" in text)
    )


def _is_secret_or_api_key(text: str) -> bool:
    return (
        "stripe" in text
        or "api key" in text
        or "apikey" in text
        or "secret key" in text
        or "sk_live" in text
        or "sk_test" in text
        or ("gitleaks" in text and "secret" in text)
    )


def _is_sql_injection(text: str) -> bool:
    return (
        "sql injection" in text
        or "sqli" in text
        or "raw sql" in text
        or "string concatenated sql" in text
        or "string-concatenated sql" in text
    )


def _is_subprocess_shell_true(text: str) -> bool:
    return "shell=true" in text or ("subprocess" in text and "shell true" in text)


def _is_wildcard_cors(text: str) -> bool:
    return (
        "wildcard cors" in text
        or "cors wildcard" in text
        or ("cors" in text and "wildcard" in text)
        or "access control allow origin *" in text
        or "allow origin *" in text
    )


def _is_credential_logging(text: str) -> bool:
    if any(
        pattern in text
        for pattern in (
            "logger-credential",
            "logger credential",
            "credential-disclosure",
            "credential disclosure",
            "logged",
            "logging",
            "logger call",
        )
    ):
        return True

    sensitive_terms = ("credential", "password", "secret", "token")
    logging_terms = (" log", "logging", "logger")
    return any(term in text for term in sensitive_terms) and any(
        term in text for term in logging_terms
    )
