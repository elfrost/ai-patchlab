"""CLI entry point: build the fingerprint database from the seed list."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fingerprint.config import FingerprintConfig, get_fingerprint_config
from fingerprint.git_seeds import SeedEntry, load_seeds, slug_from_repo_url
from fingerprint.repo_index import index_seed, write_fingerprint


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Index curated open-source template repositories into deterministic fingerprints.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--rebuild",
        action="store_true",
        help="Re-index every entry in fingerprint/seeds/repos.json.",
    )
    source.add_argument(
        "--repo-url",
        dest="repo_url",
        help="Index one ad-hoc public git URL (slug derived from URL).",
    )
    parser.add_argument(
        "--db-dir",
        dest="db_dir",
        help="Override the fingerprint DB directory (default: fingerprint/db).",
    )
    return parser.parse_args(argv)


def _resolve_config(args: argparse.Namespace) -> FingerprintConfig:
    """Resolve the active config with CLI overrides."""
    config = get_fingerprint_config()
    if args.db_dir:
        return config.model_copy(update={"db_dir": Path(args.db_dir)})
    return config


def _rebuild_all(config: FingerprintConfig) -> list[Path]:
    """Index every seed and return the written DB file paths."""
    seeds = load_seeds()
    written: list[Path] = []
    for seed in seeds:
        fingerprint = index_seed(seed, config)
        written.append(write_fingerprint(fingerprint, config.db_dir))
    return written


def _index_single(repo_url: str, config: FingerprintConfig) -> Path:
    """Index one ad-hoc repo URL and return the written DB file path."""
    seed = SeedEntry(slug=slug_from_repo_url(repo_url), repo_url=repo_url)
    fingerprint = index_seed(seed, config)
    return write_fingerprint(fingerprint, config.db_dir)


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper."""
    args = parse_args(argv)
    config = _resolve_config(args)

    if args.rebuild:
        written = _rebuild_all(config)
        for path in written:
            print(f"Indexed: {path}")
    else:
        path = _index_single(args.repo_url, config)
        print(f"Indexed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
