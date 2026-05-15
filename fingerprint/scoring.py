"""Bounded weighted scoring for fingerprint match signals."""

from __future__ import annotations

from fingerprint.models import MatchSignal, band_for_score

WEIGHT_VALUES: dict[str, float] = {
    "high": 0.45,
    "medium": 0.20,
    "low": 0.05,
}


def score_signals(signals: tuple[MatchSignal, ...] | list[MatchSignal]) -> float:
    """Return a bounded weighted score in ``[0.0, 1.0]``.

    Each signal contributes its weight (``high=0.45``, ``medium=0.20``,
    ``low=0.05``). The total is clamped at ``1.0``. An empty signal list
    scores ``0.0``.
    """
    if not signals:
        return 0.0
    total = 0.0
    for signal in signals:
        total += WEIGHT_VALUES.get(signal.weight, 0.0)
    return min(1.0, total)


__all__ = ("WEIGHT_VALUES", "band_for_score", "score_signals")
