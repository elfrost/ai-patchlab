"""Match repo-side asset hashes against fetched target assets."""

from __future__ import annotations

from fingerprint.models import MatchSignal, RepoFingerprint
from fingerprint.web_probe import TargetSnapshot


def match_asset_hashes(
    repo: RepoFingerprint,
    snapshot: TargetSnapshot,
) -> list[MatchSignal]:
    """Return one signal per repo asset whose SHA-256 matches a fetched asset.

    Favicons are weighted ``high``; every other asset kind contributes
    ``medium``. Truncated fetched assets are excluded — their hash represents
    only a prefix of the real bytes and would be misleading.
    """
    if not repo.assets or not snapshot.fetched_assets:
        return []

    fetched_by_hash = {
        asset.sha256: asset for asset in snapshot.fetched_assets if not asset.truncated
    }
    if not fetched_by_hash:
        return []

    signals: list[MatchSignal] = []
    for asset in repo.assets:
        match = fetched_by_hash.get(asset.sha256)
        if match is None:
            continue
        weight = "high" if asset.kind == "favicon" else "medium"
        signals.append(
            MatchSignal(
                kind="asset-hash",
                detail=f"{asset.kind} SHA-256 match for {asset.relative_path}",
                weight=weight,
            )
        )
    return signals
