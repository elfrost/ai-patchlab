"""Fetch a single live target safely.

Synchronous `httpx.Client` only. One target per invocation. Validates the URL
scheme (http/https only), honours `robots.txt` for the configured user agent,
caps bytes per asset and total asset count, and never follows links beyond the
seeded candidate paths.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from fingerprint.config import FingerprintConfig

ALLOWED_SCHEMES = ("http", "https")
MAX_REDIRECTS = 3


@dataclass(frozen=True)
class FetchedAsset:
    """One asset fetched from the target."""

    url: str
    sha256: str
    byte_size: int
    truncated: bool
    status: int


@dataclass(frozen=True)
class TargetSnapshot:
    """The result of probing a single target URL."""

    target_url: str
    fetched_at: str
    homepage_html: bytes
    fetched_assets: tuple[FetchedAsset, ...]
    notes: str


def _validate_scheme(url: str) -> None:
    """Reject schemes outside http/https with a `ValueError`."""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError(
            f"unsupported URL scheme {parsed.scheme!r}; only {ALLOWED_SCHEMES} are allowed"
        )
    if not parsed.netloc:
        raise ValueError(f"URL must include a host; got {url!r}")


def _origin(url: str) -> str:
    """Return the scheme://host[:port] origin for a URL."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"cannot derive origin from {url!r}")
    return f"{parsed.scheme}://{parsed.netloc}"


def _robots_allows(
    client: httpx.Client,
    origin: str,
    user_agent: str,
    target_path: str,
) -> bool:
    """Return True when robots.txt allows the target path for the user agent.

    A missing/unreachable robots.txt is treated as "allowed" — same default
    as most well-behaved scanners.
    """
    robots_url = urljoin(origin + "/", "robots.txt")
    parser = RobotFileParser()
    try:
        response = client.get(
            robots_url,
            timeout=httpx.Timeout(connect=1.0, read=2.0, write=2.0, pool=2.0),
        )
    except httpx.RequestError:
        return True
    if response.status_code >= 400:
        return True
    parser.parse(response.text.splitlines())
    target = target_path or "/"
    return parser.can_fetch(user_agent, target)


def _read_capped(response: httpx.Response, max_bytes: int) -> tuple[bytes, bool]:
    """Read at most ``max_bytes`` from a streaming response."""
    buffer = bytearray()
    truncated = False
    for chunk in response.iter_bytes():
        if not chunk:
            continue
        remaining = max_bytes - len(buffer)
        if remaining <= 0:
            truncated = True
            break
        if len(chunk) > remaining:
            buffer.extend(chunk[:remaining])
            truncated = True
            break
        buffer.extend(chunk)
    return bytes(buffer), truncated


def _fetch_one(
    client: httpx.Client,
    url: str,
    max_bytes: int,
) -> tuple[bytes, bool, int] | None:
    """Fetch one URL with byte cap and redirect limit. Returns None on error."""
    try:
        with client.stream("GET", url) as response:
            body, truncated = _read_capped(response, max_bytes)
            return body, truncated, response.status_code
    except httpx.RequestError:
        return None
    except httpx.HTTPError:
        return None


def fetch_target(
    url: str,
    config: FingerprintConfig,
    candidate_paths: tuple[str, ...],
    transport: httpx.BaseTransport | None = None,
) -> TargetSnapshot:
    """Fetch the homepage and a small allowlist of asset paths for ``url``.

    Args:
        url: HTTP or HTTPS target URL. Other schemes raise ``ValueError``.
        config: Active fingerprint configuration.
        candidate_paths: Repo-relative asset paths to try fetching from the
            same origin (e.g. ``("public/favicon.ico", "assets/main.css")``).
        transport: Optional `httpx.BaseTransport` for tests (use
            `httpx.MockTransport`). Production callers leave this `None`.

    Returns:
        A `TargetSnapshot` with the homepage HTML (possibly truncated), each
        fetched asset's hash, and a `notes` field describing any termination
        condition (`"bad-scheme"`, `"robots-disallowed"`, `"homepage-truncated"`,
        etc.).
    """
    _validate_scheme(url)
    fetched_at = datetime.now(UTC).isoformat()

    timeout = httpx.Timeout(
        connect=config.fetch_total_timeout_seconds,
        read=config.fetch_read_timeout_seconds,
        write=config.fetch_read_timeout_seconds,
        pool=config.fetch_read_timeout_seconds,
    )
    headers = {"User-Agent": config.user_agent, "Accept": "*/*"}

    client_kwargs: dict[str, object] = {
        "timeout": timeout,
        "headers": headers,
        "follow_redirects": True,
        "max_redirects": MAX_REDIRECTS,
    }
    if transport is not None:
        client_kwargs["transport"] = transport

    with httpx.Client(**client_kwargs) as client:
        origin = _origin(url)
        path = urlparse(url).path or "/"

        if not _robots_allows(client, origin, config.user_agent, path):
            return TargetSnapshot(
                target_url=url,
                fetched_at=fetched_at,
                homepage_html=b"",
                fetched_assets=(),
                notes="robots-disallowed",
            )

        notes_parts: list[str] = []
        homepage = _fetch_one(client, url, config.max_bytes_per_asset)
        homepage_html = b""
        if homepage is None:
            notes_parts.append("homepage-fetch-failed")
        else:
            body, truncated, status = homepage
            if status >= 400:
                notes_parts.append(f"homepage-status-{status}")
            else:
                homepage_html = body
                if truncated:
                    notes_parts.append("homepage-truncated")

        fetched: list[FetchedAsset] = []
        seen_urls: set[str] = set()
        remaining = max(0, config.max_assets_per_target - 1)
        for path_candidate in _normalize_candidates(candidate_paths):
            if remaining <= 0:
                break
            asset_url = urljoin(origin + "/", path_candidate.lstrip("/"))
            if asset_url in seen_urls or asset_url == url:
                continue
            seen_urls.add(asset_url)
            result = _fetch_one(client, asset_url, config.max_bytes_per_asset)
            if result is None:
                continue
            body, truncated, status = result
            digest = hashlib.sha256(body).hexdigest()
            fetched.append(
                FetchedAsset(
                    url=asset_url,
                    sha256=digest,
                    byte_size=len(body),
                    truncated=truncated,
                    status=status,
                )
            )
            remaining -= 1

        notes = "; ".join(notes_parts) if notes_parts else "ok"
        return TargetSnapshot(
            target_url=url,
            fetched_at=fetched_at,
            homepage_html=homepage_html,
            fetched_assets=tuple(fetched),
            notes=notes,
        )


def _normalize_candidates(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Deduplicate candidate paths while preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for path in paths:
        cleaned = path.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return tuple(out)
