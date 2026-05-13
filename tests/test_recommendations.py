"""Tests for deterministic recommendation enrichment."""

import pytest

from scanner.models import Finding
from scanner.recommendations import (
    CREDENTIAL_LOGGING_RECOMMENDATION,
    GITHUB_PAT_RECOMMENDATION,
    MISSING_INTEGRITY_RECOMMENDATION,
    NON_LITERAL_IMPORT_RECOMMENDATION,
    SECRET_RECOMMENDATION,
    SQL_INJECTION_RECOMMENDATION,
    SUBPROCESS_SHELL_RECOMMENDATION,
    UNSAFE_FORMATSTRING_RECOMMENDATION,
    WILDCARD_CORS_RECOMMENDATION,
    enrich_finding,
)


def _finding(rule: str, title: str, tool: str = "semgrep") -> Finding:
    return Finding(
        id=rule,
        tool=tool,
        severity="high",
        title=title,
        description="Scanner detected a security issue.",
        file="src/app.py",
        line=10,
        recommendation="Review the scanner rule guidance.",
        confidence="medium",
    )


@pytest.mark.parametrize(
    ("finding", "recommendation"),
    [
        (
            _finding(
                "gitleaks-stripe-api-key", "Potential secret detected: Stripe API key", "gitleaks"
            ),
            SECRET_RECOMMENDATION,
        ),
        (
            _finding("gitleaks-github-pat", "Potential secret detected: GitHub PAT", "gitleaks"),
            GITHUB_PAT_RECOMMENDATION,
        ),
        (
            _finding("python.sql-injection.raw-sql", "Possible SQL injection through raw SQL"),
            SQL_INJECTION_RECOMMENDATION,
        ),
        (
            _finding("python.subprocess-shell-true", "subprocess call uses shell=True"),
            SUBPROCESS_SHELL_RECOMMENDATION,
        ),
        (
            _finding("javascript.cors-wildcard-origin", "Wildcard CORS origin"),
            WILDCARD_CORS_RECOMMENDATION,
        ),
        (
            _finding("python.credential-logging", "Credential logging detected"),
            CREDENTIAL_LOGGING_RECOMMENDATION,
        ),
        (
            _finding("html.security.audit.missing-integrity.missing-integrity", "Missing SRI"),
            MISSING_INTEGRITY_RECOMMENDATION,
        ),
        (
            _finding("python.lang.security.audit.non-literal-import.non-literal-import", "Import"),
            NON_LITERAL_IMPORT_RECOMMENDATION,
        ),
        (
            _finding(
                "javascript.lang.security.audit.unsafe-formatstring.unsafe-formatstring",
                "Unsafe format string",
            ),
            UNSAFE_FORMATSTRING_RECOMMENDATION,
        ),
    ],
)
def test_enrich_finding_replaces_generic_recommendations(
    finding: Finding, recommendation: str
) -> None:
    enriched = enrich_finding(finding)

    assert enriched.recommendation == recommendation
    assert {key: value for key, value in enriched.to_dict().items() if key != "recommendation"} == {
        key: value for key, value in finding.to_dict().items() if key != "recommendation"
    }


def test_enrich_finding_keeps_unknown_recommendation() -> None:
    finding = _finding("python.best-practice.timeout", "Request without timeout")

    assert enrich_finding(finding) is finding


@pytest.mark.parametrize(
    ("rule", "title", "description"),
    [
        ("python.logger-credential", "Hardcoded secret", "Scanner detected a security issue."),
        ("python.credential-disclosure", "Token disclosure", "Scanner detected a security issue."),
        ("python.secret", "Token was logged", "Scanner detected a security issue."),
        ("python.secret", "Sensitive token logging", "Scanner detected a security issue."),
        ("python.secret", "Logger call includes secret", "Scanner detected a security issue."),
    ],
)
def test_logging_recommendations_take_priority(rule: str, title: str, description: str) -> None:
    finding = Finding(
        id=rule,
        tool="semgrep",
        severity="high",
        title=title,
        description=description,
        file="src/app.py",
        line=10,
        recommendation="Review the scanner rule guidance.",
        confidence="medium",
    )

    assert enrich_finding(finding).recommendation == CREDENTIAL_LOGGING_RECOMMENDATION
