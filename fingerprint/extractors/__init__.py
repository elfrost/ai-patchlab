"""Fingerprint extractor registry.

Each extractor is a pure function: it takes a `repo_root: Path` (and the active
config when bytes caps matter) and returns deterministic data. No subprocess,
no network. The registry tuple is the canonical list of extractors that run
when indexing a seeded repo.
"""

from collections.abc import Callable
from pathlib import Path

from fingerprint.config import FingerprintConfig
from fingerprint.extractors.favicon import extract_favicon
from fingerprint.extractors.html_signatures import extract_html_signatures
from fingerprint.extractors.static_assets import extract_static_assets
from fingerprint.models import AssetFingerprint, HtmlSignature

FaviconExtractor = Callable[[Path], AssetFingerprint | None]
StaticAssetsExtractor = Callable[[Path, FingerprintConfig], tuple[AssetFingerprint, ...]]
HtmlSignaturesExtractor = Callable[[Path], tuple[HtmlSignature, ...]]

__all__ = (
    "extract_favicon",
    "extract_html_signatures",
    "extract_static_assets",
)
