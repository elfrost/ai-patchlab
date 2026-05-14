"""HTML signature extractor."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fingerprint.models import HtmlSignature

TEMPLATE_EXTENSIONS: tuple[str, ...] = (
    ".html",
    ".htm",
    ".jsx",
    ".tsx",
    ".vue",
    ".astro",
    ".svelte",
)

_META_GENERATOR_PATTERN = re.compile(
    r"<meta\s+[^>]*name\s*=\s*[\"']generator[\"'][^>]*content\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_CLASS_TOKEN_PATTERN = re.compile(r"^[a-z][a-z0-9-]{6,}$")
_CLASS_ATTR_PATTERN = re.compile(r'class\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
_DATA_ATTR_PATTERN = re.compile(
    r"(data-[a-z][a-z0-9-]{2,})\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_COMMENT_PATTERN = re.compile(r"<!--(.*?)-->", re.DOTALL)
_CAPITALIZED_WORD_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9_-]{2,}\b")

MAX_SIGNATURES = 24


def _iter_template_files(repo_root: Path) -> list[Path]:
    """Return template files in deterministic order, skipping vendor folders."""
    skip_parts = {"node_modules", ".git", "dist", "build", "out", ".next", ".cache"}
    found: list[Path] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEMPLATE_EXTENSIONS:
            continue
        if any(part in skip_parts for part in path.parts):
            continue
        found.append(path)
    return found


def _safe_read(path: Path) -> str:
    """Read text with replacement for invalid bytes."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def extract_html_signatures(repo_root: Path) -> tuple[HtmlSignature, ...]:
    """Extract distinctive HTML signatures from template files.

    Pulled from `*.html`, `*.htm`, `*.jsx`, `*.tsx`, `*.vue`, `*.astro`,
    `*.svelte` files. Returns deterministic results: signatures are sorted and
    capped at ``MAX_SIGNATURES``.
    """
    files = _iter_template_files(repo_root)

    meta_generators: set[str] = set()
    class_counts: Counter[str] = Counter()
    data_attrs: set[tuple[str, str]] = set()
    comment_word_counts: Counter[str] = Counter()
    files_seen_by_class: dict[str, set[Path]] = {}

    for path in files:
        text = _safe_read(path)
        if not text:
            continue

        for match in _META_GENERATOR_PATTERN.finditer(text):
            value = match.group(1).strip()
            if value:
                meta_generators.add(value)

        for match in _CLASS_ATTR_PATTERN.finditer(text):
            for token in match.group(1).split():
                token = token.strip()
                if _CLASS_TOKEN_PATTERN.match(token):
                    class_counts[token] += 1
                    files_seen_by_class.setdefault(token, set()).add(path)

        for match in _DATA_ATTR_PATTERN.finditer(text):
            attr, value = match.group(1).lower(), match.group(2).strip()
            if value:
                data_attrs.add((attr, value))

        for match in _COMMENT_PATTERN.finditer(text):
            for word in _CAPITALIZED_WORD_PATTERN.findall(match.group(1)):
                comment_word_counts[word] += 1

    signatures: list[HtmlSignature] = []

    for value in sorted(meta_generators):
        signatures.append(HtmlSignature(kind="meta-generator", pattern=value, weight="high"))

    for word, count in sorted(comment_word_counts.items()):
        if count >= 2:
            signatures.append(HtmlSignature(kind="comment", pattern=word, weight="high"))

    for token, _count in sorted(class_counts.items()):
        if len(files_seen_by_class.get(token, set())) >= 2:
            signatures.append(HtmlSignature(kind="class", pattern=token, weight="medium"))

    for attr, value in sorted(data_attrs):
        signatures.append(
            HtmlSignature(
                kind="data-attr",
                pattern=f'{attr}="{value}"',
                weight="medium",
            )
        )

    return tuple(signatures[:MAX_SIGNATURES])
