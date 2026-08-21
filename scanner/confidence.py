"""Centralized confidence rules for scanner findings.

Confidence reflects how sure AI PatchLab is that a finding is real and
actionable. The rules below are the single source of truth for every
scanner adapter; never inline a `confidence=` magic string in
`scanner/scanners/*` or `scanner/scanners/common.py`.

Three confidence levels (see `scanner.models.CONFIDENCES`):
- `high`   - certain about the state (named CVE/GHSA, named secret rule,
             confirmed tool state such as not-installed / disabled).
- `medium` - rule fired but the verdict depends on environment, on
             untrusted external output, or on a failure we can't classify
             precisely (scan-error / parse-error / command-error).
- `low`    - placeholder adapters that don't run a real scanner yet.
"""

from __future__ import annotations

META_FINDING_KINDS = (
    "not-installed",
    "partial-coverage",
    "disabled",
    "not-configured",
    "no-supported-manifest",
    "no-findings",
    "scan-error",
    "json-parse-error",
    "command-error",
)

_CERTAIN_META_KINDS = frozenset(
    {
        "not-installed",
        "partial-coverage",
        "disabled",
        "not-configured",
        "no-supported-manifest",
        "no-findings",
    }
)

_FAILURE_META_KINDS = frozenset(
    {
        "scan-error",
        "json-parse-error",
        "command-error",
    }
)

_NAMED_DEPENDENCY_ADVISORY_PREFIXES = ("CVE-", "GHSA-", "PYSEC-")

# Semgrep rules whose hits are dominated by non-actionable results across the
# public scan series - either outright false positives, or true-but-low-signal
# posture nits that have never once been the real finding of a scan. Matched as
# substrings against the full check_id, so the rule-path segment is enough.
#
# Findings from these rules are emitted at `low` confidence: they stay in the
# report (a low-signal rule is not always wrong) but drop out of the "Top
# Findings" block, which ranks on severity then confidence.
#
# Counts below were measured over the 87 reports in `reports/`, covering 6,796
# Semgrep findings. Together these rules are ~47% of all Semgrep output.
_HIGH_FALSE_POSITIVE_SEMGREP_RULES = frozenset(
    {
        # 378 hits / 36 repos. Fires on any logging call near a secret-shaped
        # variable name, even when no secret is logged.
        "logger-credential-leak",
        # --- the SQL-identifier cluster: 1,802 hits / 26.5% of all output ---
        # These fire when *any* part of a query string is interpolated. In the
        # series the data is bound in every confirmed case and only identifiers
        # (table/column/PRAGMA names) are formatted in, which is not injectable
        # by an end user. Real only when a VALUE is interpolated, which the rule
        # cannot distinguish. Worst observed case: 157 hits in a project with no
        # SQLAlchemy dependency at all (stdlib sqlite3 PRAGMA statements).
        "sqlalchemy-execute-raw-query",  # 1,040 hits / 36 repos
        "formatted-sql-query",  # 376 hits / 33 repos
        "avoid-sqlalchemy-text",  # 278 hits / 26 repos
        "asyncpg-sqli",  # 108 hits / 6 repos
        # 1,341 hits / 40 repos - 20% of all Semgrep output on its own. A real
        # supply-chain hygiene recommendation (pin actions to a commit SHA), but
        # never the finding a maintainer needed to hear in 83 scans.
        "github-actions-mutable-action-tag",
    }
)

# Gitleaks rules that name a specific provider's credential format. A match is
# a strong signal because the format itself is distinctive.
_NAMED_SECRET_GITLEAKS_RULES = frozenset(
    {
        "aws-access-token",
        "algolia-api-key",
        "discord-client-id",
        "dropbox-api-token",
        "gcp-api-key",
        "github-pat",
        "jwt",
        "linkedin-client-id",
        "private-key",
        "slack-user-token",
        "slack-webhook-url",
        "stripe-access-token",
    }
)

# Substrings that mark a matched "secret" as documentation rather than a
# credential. Measured tier: `generic-api-key` alone is 1,126 of the 1,326
# Gitleaks hits in the series (85%), across 52 repositories, and hand review
# found the overwhelming majority to be placeholders in .env.example files,
# README snippets, i18n strings, and test fixtures.
# Quote characters stripped before the repeated-character mask check.
_QUOTE_CHARS = "\"'`"

_PLACEHOLDER_SECRET_MARKERS = (
    "your-",
    "your_",
    "yourapi",
    "yourtoken",
    "changeme",
    "change-me",
    "change_me",
    "placeholder",
    "example",
    "dummy",
    "sample",
    "insert-",
    "insert_",
    "replace-me",
    "replace_me",
    "replaceme",
    "<",
    "xxxx",
    "test-",
    "test_",
    "-test-",
    "sk-test",
    "todo",
    "fake",
    "notreal",
    "redacted",
)


def confidence_for_meta_finding(kind: str) -> str:
    """Confidence for cross-cutting infrastructure / error findings.

    Args:
        kind: One of `META_FINDING_KINDS`.

    Returns:
        `"high"` when we are certain about the tool state
        (not-installed, disabled, not-configured, no-supported-manifest,
        no-findings). `"medium"` when something failed and we cannot
        classify the failure precisely (scan-error, json-parse-error,
        command-error).

    Raises:
        ValueError: If `kind` is not a recognized meta finding kind.
    """
    if kind in _CERTAIN_META_KINDS:
        return "high"
    if kind in _FAILURE_META_KINDS:
        return "medium"
    raise ValueError(f"Unsupported meta finding kind: {kind}")


def confidence_for_semgrep_finding(check_id: str = "") -> str:
    """Confidence for a Semgrep finding, keyed on its rule (`check_id`).

    Most Semgrep findings are `medium` (rule-based, moderate false-positive
    rate). Rules listed in `_HIGH_FALSE_POSITIVE_SEMGREP_RULES` - those that
    have fired almost exclusively on false positives across the public scan
    series - are downgraded to `low` so curation can deprioritize them.

    Args:
        check_id: The Semgrep rule id (e.g.
            `python.lang.security.audit.logging.logger-credential-leak`).
            Defaults to empty, which yields `medium`.
    """
    if any(rule in check_id for rule in _HIGH_FALSE_POSITIVE_SEMGREP_RULES):
        return "low"
    return "medium"


def confidence_for_gitleaks_finding(rule_id: str = "", secret: str = "") -> str:
    """Confidence for a Gitleaks hit, keyed on the rule and the matched text.

    Three tiers, in priority order:

    - `low`    - the matched text looks like documentation: a placeholder, a
                 template value, or an obviously masked string. This wins over
                 the rule tier, because a provider-format placeholder
                 (`ghp_xxxxxxxx`) is still a placeholder.
    - `high`   - a rule naming a specific provider's credential format, or the
                 legacy no-argument call.
    - `medium` - everything else, which in practice means `generic-api-key`:
                 85% of the series' Gitleaks volume and mostly non-credentials,
                 but entropy-based, so not safe to call low on the rule alone.

    Args:
        rule_id: The Gitleaks rule id (e.g. `generic-api-key`, `github-pat`).
        secret: The matched text. Used only to classify the hit - it is never
            written to a finding.
    """
    if secret and _looks_like_placeholder(secret):
        return "low"
    if not rule_id or rule_id in _NAMED_SECRET_GITLEAKS_RULES:
        return "high"
    return "medium"


def _looks_like_placeholder(secret: str) -> bool:
    """Whether a matched secret is documentation rather than a credential."""
    candidate = secret.strip().lower()
    if not candidate:
        return False
    if any(marker in candidate for marker in _PLACEHOLDER_SECRET_MARKERS):
        return True
    # A single repeated character (xxxxxxxx, ........, 00000000) is a mask, not
    # a credential. Guard on length so short real values are not swept up.
    stripped = candidate.strip(_QUOTE_CHARS)
    return len(stripped) >= 6 and len(set(stripped)) == 1


def confidence_for_trivy_vulnerability(vulnerability_id: str) -> str:
    """Named CVE advisories are high confidence; other ids are medium."""
    if vulnerability_id and vulnerability_id.upper().startswith("CVE-"):
        return "high"
    return "medium"


def confidence_for_trivy_misconfiguration() -> str:
    """Trivy misconfigurations depend on the target environment."""
    return "medium"


def confidence_for_dependency_vulnerability(vulnerability_id: str) -> str:
    """Named pip-audit advisories (CVE/GHSA/PYSEC) are high; fallback id is medium."""
    if not vulnerability_id:
        return "medium"
    upper_id = vulnerability_id.upper()
    if any(upper_id.startswith(prefix) for prefix in _NAMED_DEPENDENCY_ADVISORY_PREFIXES):
        return "high"
    return "medium"


def confidence_for_ai_review_record() -> str:
    """Untrusted external AI review records default to medium."""
    return "medium"


def confidence_for_placeholder() -> str:
    """Placeholder scanner adapters that haven't been wired to a real tool."""
    return "low"
