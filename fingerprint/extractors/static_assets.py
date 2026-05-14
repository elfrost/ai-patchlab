"""Static asset extractor."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fingerprint.config import FingerprintConfig
from fingerprint.models import AssetFingerprint

ASSET_FOLDERS: tuple[str, ...] = ("public", "static", "assets", "dist")
ASSET_EXTENSIONS: tuple[str, ...] = (".css", ".js", ".png", ".svg", ".woff2")
MAX_ASSETS_INDEXED = 12

_KIND_BY_EXT = {
    ".css": "css",
    ".js": "js",
    ".png": "image",
    ".svg": "image",
    ".woff2": "other",
}


def extract_static_assets(
    repo_root: Path,
    config: FingerprintConfig,
) -> tuple[AssetFingerprint, ...]:
    """Hash up to ``MAX_ASSETS_INDEXED`` distinctive static assets.

    Walks ``public/``, ``static/``, ``assets/``, ``dist/`` (whichever exist) in
    deterministic order, picks files with conventional asset extensions, and
    hashes each one with SHA-256. Files larger than ``config.max_bytes_per_asset``
    are skipped (consistent with the matcher's per-asset bytes cap).
    """
    candidates: list[Path] = []
    for folder in ASSET_FOLDERS:
        base = repo_root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in ASSET_EXTENSIONS:
                candidates.append(path)

    fingerprints: list[AssetFingerprint] = []
    seen: set[str] = set()
    for path in candidates:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > config.max_bytes_per_asset:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        relative = path.relative_to(repo_root).as_posix()
        fingerprints.append(
            AssetFingerprint(
                relative_path=relative,
                sha256=digest,
                byte_size=len(data),
                kind=_KIND_BY_EXT.get(path.suffix.lower(), "other"),
            )
        )
        if len(fingerprints) >= MAX_ASSETS_INDEXED:
            break

    return tuple(fingerprints)
