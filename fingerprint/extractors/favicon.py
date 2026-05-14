"""Favicon extractor."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fingerprint.models import AssetFingerprint

FAVICON_CANDIDATES: tuple[str, ...] = (
    "public/favicon.ico",
    "public/favicon.png",
    "public/favicon.svg",
    "static/favicon.ico",
    "static/favicon.png",
    "assets/favicon.ico",
    "favicon.ico",
    "favicon.png",
    "favicon.svg",
)


def extract_favicon(repo_root: Path) -> AssetFingerprint | None:
    """Return the first favicon found, hashed with SHA-256.

    Walks a small ordered allowlist of conventional favicon paths and stops at
    the first hit. Returns ``None`` when none exist.
    """
    for relative in FAVICON_CANDIDATES:
        candidate = repo_root / relative
        if candidate.is_file():
            data = candidate.read_bytes()
            return AssetFingerprint(
                relative_path=relative,
                sha256=hashlib.sha256(data).hexdigest(),
                byte_size=len(data),
                kind="favicon",
            )
    return None
