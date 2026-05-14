"""Python dependency vulnerability scanner integration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scanner.confidence import (
    confidence_for_dependency_vulnerability,
    confidence_for_meta_finding,
)
from scanner.models import Finding
from scanner.recommendations import enrich_findings
from scanner.remediation import apply_patch_suggestions
from scanner.tools.pip_audit_runner import (
    PipAuditInput,
    PipAuditResult,
    find_pip_audit_input,
    run_pip_audit,
)


def scan_dependencies(repo_path: Path, reports_dir: Path) -> list[Finding]:
    """Run pip-audit and map dependency vulnerabilities into the normalized schema."""
    audit_input = find_pip_audit_input(repo_path)
    if audit_input is None:
        return [
            Finding(
                id="dependency-scan-no-supported-manifest",
                tool="dependency-scan",
                severity="info",
                title="No supported Python dependency manifest found",
                description="No requirements.txt, requirements/*.txt, pyproject.toml, or pylock.*.toml file was found for dependency auditing.",
                file=str(repo_path),
                line=None,
                recommendation="Add a supported Python dependency manifest or skip dependency auditing for this repository.",
                confidence=confidence_for_meta_finding("no-supported-manifest"),
            )
        ]

    raw_report_path = reports_dir / "raw" / "pip-audit.json"
    result = run_pip_audit(
        repo_path=repo_path,
        raw_report_path=raw_report_path,
        audit_input=audit_input,
    )

    if not result.installed:
        return [
            Finding(
                id="pip-audit-not-installed",
                tool="dependency-scan",
                severity="info",
                title="pip-audit is not installed",
                description="pip-audit was not found as a command or Python module, so Python dependency vulnerability scanning was skipped.",
                file=str(audit_input.display_path),
                line=None,
                recommendation="Install pip-audit with `python -m pip install pip-audit` and re-run the scan from PowerShell.",
                confidence=confidence_for_meta_finding("not-installed"),
            )
        ]

    try:
        dependencies = _read_pip_audit_dependencies(raw_report_path)
    except json.JSONDecodeError:
        return [
            Finding(
                id="pip-audit-json-parse-error",
                tool="dependency-scan",
                severity="info",
                title="pip-audit JSON output could not be parsed",
                description=f"The raw pip-audit report at {raw_report_path} is not valid JSON.",
                file=str(audit_input.display_path),
                line=None,
                recommendation="Re-run pip-audit and inspect the raw JSON report for truncation or invalid output.",
                confidence=confidence_for_meta_finding("json-parse-error"),
            )
        ]

    findings = _map_pip_audit_dependencies(dependencies, result)
    if result.returncode not in {0, 1, None} and not findings:
        return [
            Finding(
                id="pip-audit-scan-error",
                tool="dependency-scan",
                severity="info",
                title="pip-audit scan did not complete successfully",
                description=_format_scan_error(result.stderr or result.stdout),
                file=str(audit_input.display_path),
                line=None,
                recommendation="Review the pip-audit error output, fix the dependency scanner setup, and re-run the scan.",
                confidence=confidence_for_meta_finding("scan-error"),
            )
        ]

    return apply_patch_suggestions(enrich_findings(findings))


def _read_pip_audit_dependencies(raw_report_path: Path) -> list[dict[str, Any]]:
    """Read pip-audit dependency records from disk."""
    if not raw_report_path.exists():
        return []

    raw_text = raw_report_path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw_text:
        return []

    data = json.loads(raw_text)
    if isinstance(data, list):
        return [record for record in data if isinstance(record, dict)]

    if isinstance(data, dict):
        dependencies = data.get("dependencies") or data.get("results") or []
        if isinstance(dependencies, list):
            return [record for record in dependencies if isinstance(record, dict)]

    return []


def _map_pip_audit_dependencies(
    dependencies: list[dict[str, Any]],
    result: PipAuditResult,
) -> list[Finding]:
    """Map pip-audit dependency records into normalized findings."""
    findings: list[Finding] = []
    for dependency in dependencies:
        vulns = dependency.get("vulns") or dependency.get("vulnerabilities") or []
        if not isinstance(vulns, list):
            continue

        for vuln in vulns:
            if isinstance(vuln, dict):
                findings.append(_map_pip_audit_vulnerability(dependency, vuln, result))

    return findings


def _map_pip_audit_vulnerability(
    dependency: dict[str, Any],
    vuln: dict[str, Any],
    result: PipAuditResult,
) -> Finding:
    """Map one pip-audit vulnerability into the AI PatchLab schema."""
    package_name = _get_string(dependency, "name", "package", default="unknown-package")
    installed_version = _get_string(dependency, "version", default="unknown-version")
    vulnerability_id = _get_string(vuln, "id", "vulnerability_id", default="pip-audit-finding")
    aliases = _get_string_list(vuln, "aliases")
    fix_versions = _get_string_list(vuln, "fix_versions", "fixes")
    description = _get_string(
        vuln,
        "description",
        default=f"{package_name} {installed_version} has a known vulnerability.",
    )

    return Finding(
        id=_stable_id("dependency-scan", package_name, installed_version, vulnerability_id),
        tool="dependency-scan",
        severity=_dependency_severity(vulnerability_id, aliases, fix_versions),
        title=f"Vulnerable dependency: {package_name} {vulnerability_id}",
        description=_append_dependency_context(
            description,
            package_name=package_name,
            installed_version=installed_version,
            vulnerability_id=vulnerability_id,
            aliases=aliases,
        ),
        file=_finding_file(result.audit_input),
        line=None,
        recommendation=_dependency_recommendation(
            package_name=package_name,
            fix_versions=fix_versions,
            vulnerability_id=vulnerability_id,
        ),
        confidence=confidence_for_dependency_vulnerability(vulnerability_id),
    )


def _dependency_severity(
    vulnerability_id: str,
    aliases: list[str],
    fix_versions: list[str],
) -> str:
    """Infer a normalized severity from pip-audit metadata."""
    identifiers = [vulnerability_id, *aliases]
    if fix_versions and any(identifier.startswith(("CVE-", "GHSA-")) for identifier in identifiers):
        return "high"
    if fix_versions:
        return "medium"
    return "medium"


def _dependency_recommendation(
    *,
    package_name: str,
    fix_versions: list[str],
    vulnerability_id: str,
) -> str:
    """Build remediation guidance for a vulnerable dependency."""
    if fix_versions:
        return (
            f"Upgrade {package_name} to a fixed version: {', '.join(fix_versions)}. "
            f"Review advisory {vulnerability_id} before release."
        )
    return (
        f"Review advisory {vulnerability_id} for {package_name}; upgrade, remove, or mitigate "
        "the affected dependency when a fix is available."
    )


def _append_dependency_context(
    description: str,
    *,
    package_name: str,
    installed_version: str,
    vulnerability_id: str,
    aliases: list[str],
) -> str:
    """Append package context to a dependency vulnerability description."""
    context = [
        f"Package: {package_name}",
        f"installed: {installed_version}",
        f"advisory: {vulnerability_id}",
    ]
    if aliases:
        context.append(f"aliases: {', '.join(aliases)}")
    return f"{description} ({'; '.join(context)})"


def _finding_file(audit_input: PipAuditInput | None) -> str:
    """Return the best file path for findings generated from pip-audit."""
    if audit_input is None:
        return ""
    return str(audit_input.display_path)


def _get_string(record: dict[str, Any], *keys: str, default: str) -> str:
    """Return the first non-empty string value for the given keys."""
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return default


def _get_string_list(record: dict[str, Any], *keys: str) -> list[str]:
    """Return the first string list value for the given keys."""
    for key in keys:
        value = record.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if value is not None and str(value).strip():
            return [str(value)]
    return []


def _stable_id(*parts: str) -> str:
    """Build a stable finding ID from non-empty values."""
    safe_parts = [re.sub(r"[^A-Za-z0-9_.:-]+", "-", part.strip()) for part in parts if part.strip()]
    return "-".join(safe_parts)


def _format_scan_error(output: str) -> str:
    """Keep scanner error text short enough for the report."""
    output = output.strip()
    if not output:
        return "pip-audit returned an error without additional output."
    return output[:500]
