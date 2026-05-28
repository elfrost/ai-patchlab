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

# Semgrep rules with a track record of firing almost exclusively on false
# positives across the public scan series. Matched as substrings against the
# full check_id, so the short rule name is enough. Findings from these rules
# are emitted at `low` confidence so curation can deprioritize them while the
# signal is still kept in the report.
_HIGH_FALSE_POSITIVE_SEMGREP_RULES = frozenset(
    {
        # 6/6 false positives (honcho + five prior scans): fires on any logging
        # call near a secret-shaped variable name, even when no secret is logged.
        "logger-credential-leak",
    }
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


def confidence_for_gitleaks_finding() -> str:
    """Named Gitleaks rules and high-entropy matches have low false-positive rates."""
    return "high"


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
