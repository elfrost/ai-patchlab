"""Tests for the centralized confidence rules."""

from __future__ import annotations

import pytest

from scanner.confidence import (
    META_FINDING_KINDS,
    confidence_for_ai_review_record,
    confidence_for_dependency_vulnerability,
    confidence_for_gitleaks_finding,
    confidence_for_meta_finding,
    confidence_for_placeholder,
    confidence_for_semgrep_finding,
    confidence_for_trivy_misconfiguration,
    confidence_for_trivy_vulnerability,
)
from scanner.models import CONFIDENCES


class TestMetaFindings:
    """Cross-cutting infrastructure findings emitted by every scanner."""

    @pytest.mark.parametrize(
        "kind",
        ["not-installed", "disabled", "not-configured", "no-supported-manifest", "no-findings"],
    )
    def test_certain_tool_states_are_high(self, kind: str) -> None:
        assert confidence_for_meta_finding(kind) == "high"

    @pytest.mark.parametrize(
        "kind",
        ["scan-error", "json-parse-error", "command-error"],
    )
    def test_failure_states_are_medium(self, kind: str) -> None:
        assert confidence_for_meta_finding(kind) == "medium"

    def test_unknown_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported meta finding kind"):
            confidence_for_meta_finding("totally-unknown")

    def test_all_known_kinds_are_listed_in_meta_finding_kinds(self) -> None:
        for kind in [
            "not-installed",
            "disabled",
            "not-configured",
            "no-supported-manifest",
            "no-findings",
            "scan-error",
            "json-parse-error",
            "command-error",
        ]:
            assert kind in META_FINDING_KINDS


class TestSemgrep:
    def test_semgrep_findings_are_medium(self) -> None:
        assert confidence_for_semgrep_finding() == "medium"


class TestGitleaks:
    def test_gitleaks_findings_are_high(self) -> None:
        assert confidence_for_gitleaks_finding() == "high"


class TestTrivy:
    def test_named_cve_is_high(self) -> None:
        assert confidence_for_trivy_vulnerability("CVE-2024-12345") == "high"

    def test_lowercase_cve_is_high(self) -> None:
        assert confidence_for_trivy_vulnerability("cve-2024-12345") == "high"

    def test_non_cve_id_is_medium(self) -> None:
        assert confidence_for_trivy_vulnerability("trivy-vulnerability") == "medium"

    def test_ghsa_id_is_medium(self) -> None:
        # Trivy advisory ids that aren't CVE-prefixed get medium today.
        assert confidence_for_trivy_vulnerability("GHSA-aaaa-bbbb-cccc") == "medium"

    def test_empty_id_is_medium(self) -> None:
        assert confidence_for_trivy_vulnerability("") == "medium"

    def test_misconfiguration_is_medium(self) -> None:
        assert confidence_for_trivy_misconfiguration() == "medium"


class TestDependencyVulnerability:
    def test_cve_id_is_high(self) -> None:
        assert confidence_for_dependency_vulnerability("CVE-2024-99999") == "high"

    def test_ghsa_id_is_high(self) -> None:
        assert confidence_for_dependency_vulnerability("GHSA-xxxx-yyyy-zzzz") == "high"

    def test_pysec_id_is_high(self) -> None:
        assert confidence_for_dependency_vulnerability("PYSEC-2024-1") == "high"

    def test_fallback_id_is_medium(self) -> None:
        assert confidence_for_dependency_vulnerability("pip-audit-finding") == "medium"

    def test_empty_id_is_medium(self) -> None:
        assert confidence_for_dependency_vulnerability("") == "medium"


class TestAiReview:
    def test_ai_review_records_default_to_medium(self) -> None:
        assert confidence_for_ai_review_record() == "medium"


class TestPlaceholder:
    def test_placeholders_are_low(self) -> None:
        assert confidence_for_placeholder() == "low"


class TestReturnValueDomain:
    """Every rule must return a value accepted by Finding.confidence."""

    @pytest.mark.parametrize(
        "kind",
        [
            "not-installed",
            "disabled",
            "not-configured",
            "no-supported-manifest",
            "no-findings",
            "scan-error",
            "json-parse-error",
            "command-error",
        ],
    )
    def test_meta_finding_returns_valid_confidence(self, kind: str) -> None:
        assert confidence_for_meta_finding(kind) in CONFIDENCES

    def test_scanner_rules_return_valid_confidences(self) -> None:
        assert confidence_for_semgrep_finding() in CONFIDENCES
        assert confidence_for_gitleaks_finding() in CONFIDENCES
        assert confidence_for_trivy_vulnerability("CVE-1") in CONFIDENCES
        assert confidence_for_trivy_vulnerability("other") in CONFIDENCES
        assert confidence_for_trivy_misconfiguration() in CONFIDENCES
        assert confidence_for_dependency_vulnerability("CVE-1") in CONFIDENCES
        assert confidence_for_dependency_vulnerability("pip-audit-finding") in CONFIDENCES
        assert confidence_for_ai_review_record() in CONFIDENCES
        assert confidence_for_placeholder() in CONFIDENCES
