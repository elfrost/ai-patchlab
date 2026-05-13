"""Trivy scanner integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scanner.models import Finding
from scanner.recommendations import enrich_findings
from scanner.remediation import apply_patch_suggestions
from scanner.tools.trivy_runner import run_trivy

TRIVY_SEVERITY_MAP = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "UNKNOWN": "info",
}


def scan_trivy(repo_path: Path, reports_dir: Path) -> list[Finding]:
    """Run Trivy and map JSON findings into the normalized schema."""
    raw_report_path = reports_dir / "raw" / "trivy.json"
    result = run_trivy(repo_path=repo_path, raw_report_path=raw_report_path)

    if not result.installed:
        return [
            Finding(
                id="trivy-not-installed",
                tool="trivy",
                severity="info",
                title="Trivy is not installed",
                description="Trivy was not found on PATH, so filesystem vulnerability and misconfiguration scanning was skipped.",
                file=str(repo_path),
                line=None,
                recommendation="Install Trivy, ensure it is available on PATH, and re-run the scan from PowerShell.",
                confidence="high",
            )
        ]

    try:
        results = _read_trivy_results(raw_report_path)
    except json.JSONDecodeError:
        return [
            Finding(
                id="trivy-json-parse-error",
                tool="trivy",
                severity="info",
                title="Trivy JSON output could not be parsed",
                description=f"The raw Trivy report at {raw_report_path} is not valid JSON.",
                file=str(repo_path),
                line=None,
                recommendation="Re-run Trivy and inspect the raw JSON report for truncation or invalid output.",
                confidence="medium",
            )
        ]

    findings = _map_trivy_results(results)
    if result.returncode not in {0, None} and not findings:
        return [
            Finding(
                id="trivy-scan-error",
                tool="trivy",
                severity="info",
                title="Trivy scan did not complete successfully",
                description=_format_scan_error(result.stderr or result.stdout),
                file=str(repo_path),
                line=None,
                recommendation="Review the Trivy error output, fix the scanner setup, and re-run the scan.",
                confidence="medium",
            )
        ]

    return apply_patch_suggestions(enrich_findings(findings))


def _read_trivy_results(raw_report_path: Path) -> list[dict[str, Any]]:
    """Read Trivy JSON result groups from disk."""
    if not raw_report_path.exists():
        return []

    raw_text = raw_report_path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw_text:
        return []

    data = json.loads(raw_text)
    if isinstance(data, dict):
        results = data.get("Results") or []
        if isinstance(results, list):
            return [record for record in results if isinstance(record, dict)]
    return []


def _map_trivy_results(results: list[dict[str, Any]]) -> list[Finding]:
    """Map Trivy result groups into normalized findings."""
    findings: list[Finding] = []
    for result in results:
        findings.extend(_map_vulnerabilities(result))
        findings.extend(_map_misconfigurations(result))
    return findings


def _map_vulnerabilities(result: dict[str, Any]) -> list[Finding]:
    """Map Trivy vulnerability records from a result group."""
    vulnerabilities = result.get("Vulnerabilities")
    if not isinstance(vulnerabilities, list):
        return []

    target = _get_string(result, "Target", default="")
    findings: list[Finding] = []
    for record in vulnerabilities:
        if not isinstance(record, dict):
            continue

        vulnerability_id = _get_string(record, "VulnerabilityID", default="trivy-vulnerability")
        package_name = _get_string(record, "PkgName", default="unknown-package")
        installed_version = _get_string(record, "InstalledVersion", default="")
        fixed_version = _get_string(record, "FixedVersion", default="")
        primary_url = _get_string(record, "PrimaryURL", default="")
        title = _get_string(record, "Title", default=vulnerability_id)
        description = _get_string(
            record,
            "Description",
            default=_package_summary(package_name, installed_version, vulnerability_id),
        )

        findings.append(
            Finding(
                id=_stable_id(
                    "trivy-vuln",
                    vulnerability_id,
                    package_name,
                    target,
                    installed_version,
                ),
                tool="trivy",
                severity=_map_severity(_get_string(record, "Severity", default="UNKNOWN")),
                title=title,
                description=_append_package_context(
                    description,
                    package_name=package_name,
                    installed_version=installed_version,
                    fixed_version=fixed_version,
                    primary_url=primary_url,
                ),
                file=target,
                line=None,
                recommendation=_vulnerability_recommendation(
                    package_name=package_name,
                    fixed_version=fixed_version,
                    primary_url=primary_url,
                ),
                confidence="high" if vulnerability_id.upper().startswith("CVE-") else "medium",
            )
        )

    return findings


def _map_misconfigurations(result: dict[str, Any]) -> list[Finding]:
    """Map Trivy misconfiguration records from a result group."""
    misconfigurations = result.get("Misconfigurations")
    if not isinstance(misconfigurations, list):
        return []

    target = _get_string(result, "Target", default="")
    findings: list[Finding] = []
    for record in misconfigurations:
        if not isinstance(record, dict):
            continue

        cause_metadata = record.get("CauseMetadata")
        if not isinstance(cause_metadata, dict):
            cause_metadata = {}

        rule_id = _get_string(record, "ID", "AVDID", default="trivy-misconfiguration")
        line = _get_int(cause_metadata, "StartLine", "EndLine")
        title = _get_string(record, "Title", default=rule_id)
        description = _get_string(
            record,
            "Description",
            default=_get_string(record, "Message", default="Trivy detected a misconfiguration."),
        )

        findings.append(
            Finding(
                id=_stable_id("trivy-misconfig", rule_id, target, str(line or 0)),
                tool="trivy",
                severity=_map_severity(_get_string(record, "Severity", default="UNKNOWN")),
                title=title,
                description=description,
                file=_misconfiguration_file(cause_metadata, target),
                line=line,
                recommendation=_misconfiguration_recommendation(record),
                confidence="medium",
            )
        )

    return findings


def _map_severity(raw_severity: str) -> str:
    """Normalize Trivy severity values."""
    return TRIVY_SEVERITY_MAP.get(raw_severity.upper(), "info")


def _vulnerability_recommendation(
    *, package_name: str, fixed_version: str, primary_url: str
) -> str:
    """Build remediation guidance for a vulnerable package."""
    if fixed_version:
        recommendation = f"Upgrade {package_name} to fixed version {fixed_version}."
    else:
        recommendation = (
            f"Review the advisory for {package_name} and upgrade, remove, or mitigate the "
            "affected package."
        )

    if primary_url:
        recommendation = f"{recommendation} Advisory: {primary_url}"
    return recommendation


def _misconfiguration_recommendation(record: dict[str, Any]) -> str:
    """Build remediation guidance for a misconfiguration."""
    resolution = _get_string(record, "Resolution", default="")
    if resolution:
        return resolution

    message = _get_string(record, "Message", default="")
    if message:
        return message

    return "Review the IaC, Dockerfile, or configuration file and apply the Trivy policy guidance."


def _misconfiguration_file(cause_metadata: dict[str, Any], target: str) -> str:
    """Choose the most useful file path for a Trivy misconfiguration."""
    resource = _get_string(cause_metadata, "Resource", default="")
    if _is_path_like_resource(resource):
        return resource
    return target


def _is_path_like_resource(resource: str) -> bool:
    """Return whether a Trivy resource value appears to be a file path."""
    if not resource or resource in {"-", "unknown"}:
        return False
    return (
        "/" in resource
        or "\\" in resource
        or resource in {"Dockerfile", "Containerfile"}
        or Path(resource).suffix != ""
    )


def _append_package_context(
    description: str,
    *,
    package_name: str,
    installed_version: str,
    fixed_version: str,
    primary_url: str,
) -> str:
    """Append package context to a vulnerability description."""
    context = [f"Package: {package_name}"]
    if installed_version:
        context.append(f"installed: {installed_version}")
    if fixed_version:
        context.append(f"fixed: {fixed_version}")
    if primary_url:
        context.append(f"advisory: {primary_url}")
    return f"{description} ({'; '.join(context)})"


def _package_summary(package_name: str, installed_version: str, vulnerability_id: str) -> str:
    """Build a fallback vulnerability summary."""
    if installed_version:
        return f"{package_name} {installed_version} is affected by {vulnerability_id}."
    return f"{package_name} is affected by {vulnerability_id}."


def _stable_id(*parts: str) -> str:
    """Build a stable finding ID from non-empty values."""
    safe_parts = [part.strip().replace(" ", "-") for part in parts if part.strip()]
    return "-".join(safe_parts)


def _get_string(record: dict[str, Any], *keys: str, default: str) -> str:
    """Return the first non-empty string value for the given keys."""
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return default


def _get_int(record: dict[str, Any], *keys: str) -> int | None:
    """Return the first integer value for the given keys."""
    for key in keys:
        value = record.get(key)
        if value in {None, ""}:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _format_scan_error(output: str) -> str:
    """Keep scanner error text short enough for the report."""
    output = output.strip()
    if not output:
        return "Trivy returned an error without additional output."
    return output[:500]
