"""Indexer: clone a seed repo and persist a deterministic fingerprint."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fingerprint.config import FingerprintConfig
from fingerprint.extractors.favicon import extract_favicon
from fingerprint.extractors.html_signatures import extract_html_signatures
from fingerprint.extractors.static_assets import extract_static_assets
from fingerprint.git_seeds import SeedEntry
from fingerprint.models import AssetFingerprint, RepoFingerprint
from scanner.git_source import GitCloneError, cloned_repo


def index_seed(seed: SeedEntry, config: FingerprintConfig) -> RepoFingerprint:
    """Index a single seed entry into a `RepoFingerprint`.

    Clones the seed via `scanner.git_source.cloned_repo` (shallow, temp dir,
    cleanup on exit), runs every extractor, and returns the assembled
    fingerprint. Clone failures produce an empty `RepoFingerprint` with the
    failure recorded under ``notes`` — the indexer never raises.
    """
    indexed_at = datetime.now(UTC).isoformat()
    try:
        with cloned_repo(seed.repo_url) as clone:
            return _build_fingerprint(seed, clone.repo_path, config, indexed_at)
    except GitCloneError as exc:
        return RepoFingerprint(
            slug=seed.slug,
            repo_url=seed.repo_url,
            indexed_at=indexed_at,
            assets=(),
            html_signatures=(),
            notable_paths=seed.notable_paths,
            notes=f"clone-failed: {exc}",
        )


def _build_fingerprint(
    seed: SeedEntry,
    repo_root: Path,
    config: FingerprintConfig,
    indexed_at: str,
) -> RepoFingerprint:
    """Run extractors against a cloned repo and return the fingerprint."""
    favicon = extract_favicon(repo_root)
    static_assets = extract_static_assets(repo_root, config)
    assets: tuple[AssetFingerprint, ...] = (favicon, *static_assets) if favicon else static_assets

    html_signatures = extract_html_signatures(repo_root)

    return RepoFingerprint(
        slug=seed.slug,
        repo_url=seed.repo_url,
        indexed_at=indexed_at,
        assets=assets,
        html_signatures=html_signatures,
        notable_paths=seed.notable_paths,
    )


def write_fingerprint(fingerprint: RepoFingerprint, db_dir: Path) -> Path:
    """Persist a fingerprint as JSON under ``db_dir/<slug>.json``."""
    db_dir.mkdir(parents=True, exist_ok=True)
    target = db_dir / f"{fingerprint.slug}.json"
    target.write_text(
        json.dumps(fingerprint.to_dict(), indent=2),
        encoding="utf-8",
    )
    return target


def load_fingerprints(db_dir: Path) -> tuple[RepoFingerprint, ...]:
    """Load all fingerprint JSON files from ``db_dir``.

    Skips malformed entries silently so a partial DB does not crash the
    matcher. Returns an empty tuple when the directory does not exist.
    """
    if not db_dir.is_dir():
        return ()

    fingerprints: list[RepoFingerprint] = []
    for path in sorted(db_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        try:
            fingerprints.append(_fingerprint_from_dict(data))
        except (ValueError, TypeError):
            continue
    return tuple(fingerprints)


def _fingerprint_from_dict(data: dict[str, object]) -> RepoFingerprint:
    """Rebuild a `RepoFingerprint` from its JSON form."""
    from fingerprint.models import AssetFingerprint, HtmlSignature

    raw_assets = data.get("assets") or []
    assets: list[AssetFingerprint] = []
    if isinstance(raw_assets, list):
        for record in raw_assets:
            if isinstance(record, dict):
                assets.append(
                    AssetFingerprint(
                        relative_path=str(record.get("relative_path", "")),
                        sha256=str(record.get("sha256", "")),
                        byte_size=int(record.get("byte_size", 0)),
                        kind=str(record.get("kind", "other")),
                    )
                )

    raw_signatures = data.get("html_signatures") or []
    signatures: list[HtmlSignature] = []
    if isinstance(raw_signatures, list):
        for record in raw_signatures:
            if isinstance(record, dict):
                signatures.append(
                    HtmlSignature(
                        kind=str(record.get("kind", "")),
                        pattern=str(record.get("pattern", "")),
                        weight=str(record.get("weight", "low")),
                    )
                )

    raw_notable = data.get("notable_paths") or []
    notable_paths: tuple[str, ...] = ()
    if isinstance(raw_notable, list):
        notable_paths = tuple(str(item) for item in raw_notable if str(item).strip())

    return RepoFingerprint(
        slug=str(data.get("slug", "")),
        repo_url=str(data.get("repo_url", "")),
        indexed_at=str(data.get("indexed_at", "")),
        assets=tuple(assets),
        html_signatures=tuple(signatures),
        notable_paths=notable_paths,
        notes=str(data.get("notes", "")),
    )
