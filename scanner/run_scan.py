"""Command line entry point for AI PatchLab scans."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scanner.git_source import GitCloneError, cloned_repo
from scanner.models import Finding
from scanner.recommendations import enrich_findings
from scanner.remediation import apply_patch_suggestions
from scanner.report import write_reports
from scanner.scanners import SCANNERS


def collect_findings(repo_path: Path, reports_dir: Path) -> list[Finding]:
    """Run all configured scanners and return normalized findings."""
    findings: list[Finding] = []
    for scanner in SCANNERS:
        findings.extend(scanner(repo_path, reports_dir))
    return apply_patch_suggestions(enrich_findings(findings))


def run_scan(repo_path: Path, reports_dir: Path = Path("reports")) -> dict[str, Path]:
    """Validate input, run configured scanners, and write reports."""
    resolved_repo = repo_path.expanduser().resolve()
    if not resolved_repo.exists() or not resolved_repo.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {repo_path}")

    findings = collect_findings(resolved_repo, reports_dir)
    return write_reports(repo_path=resolved_repo, findings=findings, reports_dir=reports_dir)


def run_scan_from_url(url: str, reports_dir: Path = Path("reports")) -> dict[str, Path]:
    """Clone a public git URL into a temporary directory, then scan it.

    The temporary clone is removed when the function returns. The
    generated reports are written to `reports_dir` (which must live
    outside the clone).
    """
    with cloned_repo(url) as clone:
        return run_scan(clone.repo_path, reports_dir)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the AI PatchLab security scanner foundation.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo", help="Local repository path to scan.")
    source.add_argument(
        "--from-git-url",
        dest="from_git_url",
        help="Public git URL to shallow-clone into a temp directory and scan.",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory where security_report.json and security_report.md are written.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper."""
    args = parse_args(argv)
    reports_dir = Path(args.reports_dir)
    try:
        if args.from_git_url:
            report_paths = run_scan_from_url(args.from_git_url, reports_dir)
        else:
            report_paths = run_scan(Path(args.repo), reports_dir)
    except (ValueError, GitCloneError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"JSON report: {report_paths['json']}")
    print(f"Markdown report: {report_paths['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
