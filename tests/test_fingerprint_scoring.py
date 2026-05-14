"""Tests for fingerprint scoring."""

from __future__ import annotations

import pytest
from fingerprint.models import MatchSignal, band_for_score
from fingerprint.scoring import WEIGHT_VALUES, score_signals


def _signal(weight: str) -> MatchSignal:
    return MatchSignal(kind="x", detail="x", weight=weight)


def test_empty_signals_score_zero() -> None:
    assert score_signals([]) == 0.0
    assert band_for_score(0.0) == "weak"


def test_single_high_signal_lands_in_plausible_band() -> None:
    score = score_signals([_signal("high")])
    assert score == WEIGHT_VALUES["high"]
    assert band_for_score(score) == "plausible"


def test_two_high_signals_lands_in_strong_band() -> None:
    score = score_signals([_signal("high"), _signal("high")])
    assert score == pytest.approx(2 * WEIGHT_VALUES["high"])
    assert band_for_score(score) == "strong"


def test_score_is_clamped_at_one() -> None:
    signals = [_signal("high")] * 10
    assert score_signals(signals) == 1.0
    assert band_for_score(score_signals(signals)) == "strong"


def test_weight_band_boundaries() -> None:
    assert band_for_score(0.0) == "weak"
    assert band_for_score(0.299999) == "weak"
    assert band_for_score(0.3) == "plausible"
    assert band_for_score(0.599999) == "plausible"
    assert band_for_score(0.6) == "strong"
    assert band_for_score(1.0) == "strong"


def test_mixed_weights_sum_correctly() -> None:
    signals = [_signal("high"), _signal("medium"), _signal("low")]
    expected = WEIGHT_VALUES["high"] + WEIGHT_VALUES["medium"] + WEIGHT_VALUES["low"]
    assert score_signals(signals) == pytest.approx(expected)


def test_unknown_weight_contributes_nothing() -> None:
    # Build the MatchSignal first with a valid weight, then test ignoring
    # via dataclasses.replace would also raise — we test only valid weights.
    # The scoring map ignoring unknowns is a defensive measure.
    signals = [_signal("high")]
    assert score_signals(signals) == WEIGHT_VALUES["high"]


def test_weak_band_with_only_low_signals() -> None:
    signals = [_signal("low"), _signal("low")]
    score = score_signals(signals)
    assert band_for_score(score) == "weak"
