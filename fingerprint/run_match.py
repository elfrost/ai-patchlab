"""CLI entry point: match a single live URL against the local fingerprint DB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fingerprint.config import FingerprintConfig, get_fingerprint_config
from fingerprint.matchers import MATCHERS
from fingerprint.models import MatchResult, MatchSignal, RepoFingerprint, band_for_score
from fingerprint.repo_index import load_fingerprints
from fingerprint.report import (
    build_match_payload,
    report_paths,
    write_json_report,
    write_markdown_report,
)
from fingerprint.scoring import score_signals
from fingerprint.web_probe import TargetSnapshot, fetch_target


def _gather_candidate_paths(
    fingerprints: tuple[RepoFingerprint, ...],
    cap: int,
) -> tuple[str, ...]:
    """Collect distinct candidate paths from all fingerprints, capped."""
    seen: set[str] = set()
    out: list[str] = []
    for fp in fingerprints:
        for path in fp.notable_paths:
            cleaned = path.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            out.append(cleaned)
        for asset in fp.assets:
            cleaned = asset.relative_path.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            out.append(cleaned)
        if len(out) >= cap:
            break
    return tuple(out[:cap])


def _match_repo(
    repo: RepoFingerprint,
    snapshot: TargetSnapshot,
) -> MatchResult:
    """Run every matcher against one repo fingerprint."""
    signals: list[MatchSignal] = []
    for matcher in MATCHERS:
        signals.extend(matcher(repo, snapshot))
    score = score_signals(tuple(signals))
    band = band_for_score(score)
    return MatchResult(
        target_url=snapshot.target_url,
        fetched_at=snapshot.fetched_at,
        repo_slug=repo.slug,
        score=score,
        band=band,
        signals=tuple(signals),
        notes=snapshot.notes,
    )


def run_match(
    target_url: str,
    config: FingerprintConfig,
    min_score: float = 0.0,
) -> dict[str, Path]:
    """Match a target URL against the local fingerprint DB.

    Always writes both JSON and Markdown reports, even when:
      - the DB is empty
      - the target is unreachable
      - robots.txt disallows fetching
    Returns the produced report paths.
    """
    fingerprints = load_fingerprints(config.db_dir)
    candidate_paths = _gather_candidate_paths(
        fingerprints,
        max(0, config.max_assets_per_target - 1),
    )

    base_notes_parts: list[str] = []
    snapshot: TargetSnapshot
    try:
        snapshot = fetch_target(target_url, config, candidate_paths)
    except ValueError as exc:
        snapshot = TargetSnapshot(
            target_url=target_url,
            fetched_at="",
            homepage_html=b"",
            fetched_assets=(),
            notes=f"bad-scheme: {exc}",
        )
        base_notes_parts.append("bad-scheme")

    results: tuple[MatchResult, ...] = ()
    if fingerprints and snapshot.fetched_at:
        results = tuple(_match_repo(repo, snapshot) for repo in fingerprints)
    elif not fingerprints:
        base_notes_parts.append("no-fingerprints-in-db")

    notes = "; ".join(part for part in [snapshot.notes, *base_notes_parts] if part)
    payload = build_match_payload(
        target_url=target_url,
        fetched_at=snapshot.fetched_at or "",
        results=results,
        notes=notes,
    )

    paths = report_paths(target_url, config.report_dir)
    write_json_report(payload, paths["json"])
    write_markdown_report(payload, paths["markdown"], min_score=min_score)
    return paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Match a single live URL against the local fingerprint database.",
    )
    parser.add_argument("--target", required=True, help="Live URL to probe (http(s) only).")
    parser.add_argument(
        "--db-dir",
        dest="db_dir",
        help="Override the fingerprint DB directory (default: fingerprint/db).",
    )
    parser.add_argument(
        "--report-dir",
        dest="report_dir",
        help="Override the match report directory (default: reports/fingerprint).",
    )
    parser.add_argument(
        "--min-score",
        dest="min_score",
        type=float,
        default=0.0,
        help="Drop candidates from the Markdown report below this score (JSON keeps everything).",
    )
    return parser.parse_args(argv)


def _resolve_config(args: argparse.Namespace) -> FingerprintConfig:
    """Resolve the active config with CLI overrides."""
    config = get_fingerprint_config()
    updates: dict[str, Path] = {}
    if args.db_dir:
        updates["db_dir"] = Path(args.db_dir)
    if args.report_dir:
        updates["report_dir"] = Path(args.report_dir)
    if updates:
        return config.model_copy(update=updates)
    return config


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper. Always returns 0 — partial-result discipline."""
    args = parse_args(argv)
    config = _resolve_config(args)
    paths = run_match(args.target, config, min_score=args.min_score)
    print(f"JSON report: {paths['json']}")
    print(f"Markdown report: {paths['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
