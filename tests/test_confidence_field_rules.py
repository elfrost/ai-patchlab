"""Tests for the field-derived confidence rules.

Every rule downgraded here was measured across the public scan series, not
guessed. The counts in the comments of `scanner/confidence.py` come from
mining the 87 reports under `reports/`.
"""

from __future__ import annotations

import pytest

from scanner.confidence import (
    confidence_for_gitleaks_finding,
    confidence_for_semgrep_finding,
)


class TestSemgrepLowSignalRules:
    """The SQL-identifier cluster is 26% of all Semgrep output in the series."""

    @pytest.mark.parametrize(
        "check_id",
        [
            "python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query",
            "python.lang.security.audit.formatted-sql-query.formatted-sql-query",
            "python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text",
            "python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli",
        ],
    )
    def test_sql_identifier_cluster_is_low_confidence(self, check_id: str) -> None:
        assert confidence_for_semgrep_finding(check_id) == "low"

    def test_mutable_action_tag_is_low_confidence(self) -> None:
        check_id = (
            "yaml.github-actions.security.github-actions-mutable-action-tag."
            "github-actions-mutable-action-tag"
        )
        assert confidence_for_semgrep_finding(check_id) == "low"

    def test_logger_credential_leak_stays_low(self) -> None:
        """Pre-existing rule - guard against a regression while editing the set."""
        check_id = (
            "python.lang.security.audit.logging.logger-credential-leak."
            "python-logger-credential-disclosure"
        )
        assert confidence_for_semgrep_finding(check_id) == "low"

    @pytest.mark.parametrize(
        "check_id",
        [
            "python.lang.security.audit.eval-detected.eval-detected",
            "python.lang.security.audit.dangerous-subprocess-use.subprocess-shell-true",
            "javascript.express.security.audit.express-open-redirect",
            "",
        ],
    )
    def test_other_rules_keep_medium_confidence(self, check_id: str) -> None:
        assert confidence_for_semgrep_finding(check_id) == "medium"


class TestGitleaksPlaceholderTier:
    """`generic-api-key` is 85% of all Gitleaks hits and mostly placeholders."""

    @pytest.mark.parametrize(
        "rule_id",
        ["github-pat", "stripe-access-token", "aws-access-token", "slack-user-token"],
    )
    def test_named_provider_rules_stay_high(self, rule_id: str) -> None:
        assert confidence_for_gitleaks_finding(rule_id, "ghp_realtokenvalue1234567890") == "high"

    def test_generic_api_key_is_medium_not_high(self) -> None:
        assert confidence_for_gitleaks_finding("generic-api-key", "aX9f2Kdm41PqZ7") == "medium"

    @pytest.mark.parametrize(
        "secret",
        [
            "your-api-key-here",
            "YOUR_TOKEN",
            "xxxxxxxxxxxxxxxx",
            "<your-secret>",
            "changeme",
            "placeholder-value",
            "example-key-123",
            "dummy_secret",
            "sk-test-abcdefghijklmnop",
            "................",
            "REPLACE_ME",
            "insert-token-here",
        ],
    )
    def test_placeholder_shaped_secrets_are_low(self, secret: str) -> None:
        assert confidence_for_gitleaks_finding("generic-api-key", secret) == "low"

    def test_placeholder_shape_also_downgrades_a_named_rule(self) -> None:
        """A named rule matching an obvious placeholder is still a placeholder."""
        assert confidence_for_gitleaks_finding("github-pat", "ghp_xxxxxxxxxxxxxxxxxxxx") == "low"

    def test_no_secret_text_falls_back_to_the_rule_tier(self) -> None:
        assert confidence_for_gitleaks_finding("github-pat", "") == "high"
        assert confidence_for_gitleaks_finding("generic-api-key", "") == "medium"

    def test_default_call_still_works(self) -> None:
        """Backwards compatibility with the no-argument call shape."""
        assert confidence_for_gitleaks_finding() == "high"
