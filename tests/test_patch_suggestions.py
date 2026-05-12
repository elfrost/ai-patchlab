"""Tests for deterministic remediation patch suggestions."""

from pathlib import Path

import pytest

from scanner.models import Finding
from scanner.remediation.patch_suggestions import (
    CREDENTIAL_LOGGING_SUGGESTION,
    GITHUB_TOKEN_SUGGESTION,
    HARDCODED_SECRET_SUGGESTION,
    SQL_INJECTION_SUGGESTION,
    SUBPROCESS_SHELL_SUGGESTION,
    WILDCARD_CORS_SUGGESTION,
    PatchSuggestion,
    apply_patch_suggestion,
)
from scanner.report import build_report, write_markdown_report


def _finding(
    rule: str,
    title: str,
    tool: str = "semgrep",
    description: str = "Scanner detected a security issue.",
) -> Finding:
    return Finding(
        id=rule,
        tool=tool,
        severity="high",
        title=title,
        description=description,
        file="src/app.py",
        line=10,
        recommendation="Review the scanner rule guidance.",
        confidence="medium",
    )


@pytest.mark.parametrize(
    ("finding", "suggestion"),
    [
        (
            _finding("python.flask.cors-wildcard", "Wildcard CORS origin"),
            WILDCARD_CORS_SUGGESTION,
        ),
        (
            _finding("python.subprocess-shell-true", "subprocess call uses shell=True"),
            SUBPROCESS_SHELL_SUGGESTION,
        ),
        (
            _finding("python.sql-injection.raw-sql", "Possible SQL injection through raw SQL"),
            SQL_INJECTION_SUGGESTION,
        ),
        (
            _finding("gitleaks-generic-api-key", "Potential secret detected", "gitleaks"),
            HARDCODED_SECRET_SUGGESTION,
        ),
        (
            _finding("gitleaks-github-pat", "Potential secret detected: GitHub PAT", "gitleaks"),
            GITHUB_TOKEN_SUGGESTION,
        ),
        (
            _finding("python.credential-logging", "Credential logging detected"),
            CREDENTIAL_LOGGING_SUGGESTION,
        ),
    ],
)
def test_apply_patch_suggestion_adds_known_patch_fields(
    finding: Finding, suggestion: PatchSuggestion
) -> None:
    enriched = apply_patch_suggestion(finding)

    assert enriched.patch_before == suggestion.patch_before
    assert enriched.patch_after == suggestion.patch_after
    assert enriched.remediation_explanation == suggestion.remediation_explanation
    generated_fields = {"patch_before", "patch_after", "remediation_explanation"}
    assert {
        key: value for key, value in enriched.to_dict().items() if key not in generated_fields
    } == {key: value for key, value in finding.to_dict().items() if key not in generated_fields}


def test_apply_patch_suggestion_keeps_unknown_finding() -> None:
    finding = _finding("python.best-practice.timeout", "Request without timeout")

    assert apply_patch_suggestion(finding) is finding


@pytest.mark.parametrize(
    "rule",
    [
        "python.sqlalchemy-execute-raw-query",
        "python.formatted-sql-query",
    ],
)
def test_sql_rule_aliases_use_sql_patch_suggestion(rule: str) -> None:
    enriched = apply_patch_suggestion(_finding(rule, "Potential SQL injection"))

    assert enriched.patch_before == SQL_INJECTION_SUGGESTION.patch_before
    assert enriched.patch_after == SQL_INJECTION_SUGGESTION.patch_after
    assert (
        enriched.remediation_explanation
        == "Parameterized queries keep user input separate from SQL syntax and prevent injection."
    )


@pytest.mark.parametrize(
    ("rule", "title"),
    [
        ("python.logger-credential", "Hardcoded secret in logger"),
        ("python.credential-disclosure", "Token disclosure"),
        ("python.secret", "Sensitive token logging"),
    ],
)
def test_logging_patterns_take_priority_over_secret_patches(rule: str, title: str) -> None:
    enriched = apply_patch_suggestion(_finding(rule, title))

    assert enriched.patch_before == CREDENTIAL_LOGGING_SUGGESTION.patch_before
    assert enriched.patch_after == CREDENTIAL_LOGGING_SUGGESTION.patch_after


def test_github_pat_uses_github_token_patch_suggestion() -> None:
    enriched = apply_patch_suggestion(
        _finding("gitleaks-github-pat", "Potential secret detected: GitHub PAT", "gitleaks")
    )

    assert enriched.patch_before == 'GITHUB_TOKEN = "ghp_redacted"'
    assert enriched.patch_after == 'GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]'
    assert enriched.remediation_explanation == (
        "Revoke the exposed GitHub token, remove it from source code, and load it from "
        "environment variables or a secret manager."
    )


@pytest.mark.parametrize(
    ("description", "patch_before", "patch_after"),
    [
        (
            "Logger call logged STRIPE_API_KEY during startup.",
            'logger.info("Starting app with STRIPE_API_KEY=%s and JWT_SECRET=%s", STRIPE_API_KEY, JWT_SECRET)',
            'logger.info("Starting app")',
        ),
        (
            "Login attempt logged password and api key.",
            'logger.info("Login attempt username=%s password=%s api_key=%s", username, password, api_key)',
            'logger.info("Login attempt username=%s", username)',
        ),
        (
            "Issued JWT token was logged with signing secret.",
            'logger.info("Issued JWT token=%s signed_with=%s", token, JWT_SECRET)',
            'logger.info("Issued JWT token for user_id=%s", user_id)',
        ),
        (
            "Registered user logged password in application logs.",
            'logger.info("Registered user username=%s email=%s password=%s", username, email, password)',
            'logger.info("Registered user username=%s email=%s", username, email)',
        ),
    ],
)
def test_logging_patch_suggestion_uses_description_examples(
    description: str, patch_before: str, patch_after: str
) -> None:
    enriched = apply_patch_suggestion(
        _finding("python.logger-call", "Logger call includes secret", description=description)
    )

    assert enriched.patch_before == patch_before
    assert enriched.patch_after == patch_after
    assert (
        enriched.remediation_explanation
        == "Logs are often widely retained and searched. Remove sensitive fields and redact tokens, passwords, and secrets before logging."
    )


def test_markdown_report_includes_patch_suggestion(tmp_path: Path) -> None:
    finding = apply_patch_suggestion(
        _finding("python.subprocess-shell-true", "subprocess call uses shell=True")
    )
    report = build_report(repo_path=tmp_path, findings=[finding])
    report_path = tmp_path / "security_report.md"

    write_markdown_report(report, report_path)

    markdown = report_path.read_text(encoding="utf-8")
    assert "- Patch suggestion:" in markdown
    assert 'subprocess.run(f"git log {branch}", shell=True)' in markdown
    assert 'subprocess.run(["git", "log", branch], check=True)' in markdown
    assert "- Remediation explanation:" in markdown
