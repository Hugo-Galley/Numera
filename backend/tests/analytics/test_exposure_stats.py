"""Statistiques pures du modèle de sur-exposition : rendements hebdomadaires, corrélation, tracking error, cosinus."""

from datetime import date, timedelta

import pytest

from app.domain.exposure.stats import (
    correlation,
    cosine,
    overlap,
    tracking_error,
    weekly_returns,
    weighted_returns,
)


def _series(start: date, closes: list[float]) -> list[tuple[date, float]]:
    return [(start + timedelta(weeks=i), c) for i, c in enumerate(closes)]


def _alternating_closes(n: int) -> list[float]:
    return [100 * (1.01 if i % 2 else 0.99) ** i for i in range(n)]


def test_weekly_returns_uses_last_close_of_each_week():
    monday = date(2025, 1, 6)
    r = weekly_returns([(monday, 100.0), (monday + timedelta(days=4), 110.0), (monday + timedelta(days=7), 121.0)])
    assert r == {date(2025, 1, 17): pytest.approx(0.10)}


def test_weekly_returns_ignores_input_order():
    monday = date(2025, 1, 6)
    r = weekly_returns([(monday + timedelta(days=7), 121.0), (monday + timedelta(days=4), 110.0), (monday, 100.0)])
    assert r == {date(2025, 1, 17): pytest.approx(0.10)}


def test_weekly_returns_skips_week_after_a_gap():
    # semaines 2, 3 puis 5 : la semaine 5 n'a pas de semaine précédente connue
    r = weekly_returns([(date(2025, 1, 10), 100.0), (date(2025, 1, 17), 110.0), (date(2025, 1, 31), 99.0)])
    assert r == {date(2025, 1, 17): pytest.approx(0.10)}


def test_weekly_returns_keys_are_iso_fridays_across_year_end():
    # 2024-12-30 est en semaine ISO 1 de 2025 ; la semaine précédente est la 52 de 2024
    r = weekly_returns([(date(2024, 12, 27), 100.0), (date(2024, 12, 30), 105.0)])
    assert r == {date(2025, 1, 3): pytest.approx(0.05)}


def test_weekly_returns_empty_or_single_week():
    assert weekly_returns([]) == {}
    assert weekly_returns([(date(2025, 1, 6), 100.0)]) == {}


def test_correlation_identical_is_one_and_needs_52_weeks():
    a = weekly_returns(_series(date(2024, 1, 5), _alternating_closes(60)))
    assert correlation(a, a) == pytest.approx(1.0)
    short = dict(list(a.items())[:51])
    assert correlation(short, short) is None


def test_correlation_opposite_is_minus_one():
    a = weekly_returns(_series(date(2024, 1, 5), _alternating_closes(60)))
    b = {d: -v for d, v in a.items()}
    assert correlation(a, b) == pytest.approx(-1.0)


def test_correlation_none_when_variance_is_zero():
    weeks = [date(2024, 1, 5) + timedelta(weeks=i) for i in range(60)]
    flat = dict.fromkeys(weeks, 0.01)
    other = {d: 0.01 * (i % 3) for i, d in enumerate(weeks)}
    assert correlation(flat, other) is None


def test_correlation_uses_common_keys_only():
    a = weekly_returns(_series(date(2024, 1, 5), _alternating_closes(60)))
    extra = dict(a)
    extra[date(2030, 1, 4)] = 5.0
    assert correlation(a, extra) == pytest.approx(1.0)


def test_tracking_error_zero_for_same_index_and_high_for_other():
    a = weekly_returns(_series(date(2024, 1, 5), _alternating_closes(60)))
    b = {d: v + (0.01 if i % 2 else -0.01) for i, (d, v) in enumerate(sorted(a.items()))}
    assert tracking_error(a, a) == pytest.approx(0.0)
    assert tracking_error(a, b) == pytest.approx(0.072, abs=0.005)


def test_tracking_error_needs_52_common_weeks():
    a = weekly_returns(_series(date(2024, 1, 5), _alternating_closes(60)))
    short = dict(list(a.items())[:51])
    assert tracking_error(short, a) is None


def test_cosine():
    assert cosine({"x": 1.0}, {"x": 2.0}) == pytest.approx(1.0)
    assert cosine({"x": 1.0}, {"y": 1.0}) == 0.0
    assert cosine({}, {"x": 1.0}) == 0.0
    assert cosine({"x": 0.0}, {"x": 1.0}) == 0.0
    assert cosine({"x": 1.0, "y": 1.0}, {"x": 1.0}) == pytest.approx(2**-0.5)


def test_weighted_returns_only_common_weeks():
    d1, d2 = date(2025, 1, 10), date(2025, 1, 17)
    assert weighted_returns({"A": {d1: 0.1, d2: 0.2}, "B": {d1: 0.3}}, {"A": 3.0, "B": 1.0}) == {d1: pytest.approx(0.15)}


def test_weighted_returns_ignores_unweighted_series_and_zero_weights():
    d1, d2 = date(2025, 1, 10), date(2025, 1, 17)
    series = {"A": {d1: 0.1, d2: 0.2}, "B": {d1: 0.3}, "C": {d1: 0.5}}
    assert weighted_returns(series, {"A": 1.0, "C": 0.0}) == {d1: pytest.approx(0.1), d2: pytest.approx(0.2)}
    assert weighted_returns(series, {}) == {}
    assert weighted_returns(series, {"Z": 1.0}) == {}


def test_weighted_returns_leaves_out_funds_without_enough_history():
    """Un fonds acheté récemment ne réduit pas le cœur à ses quelques semaines : il en est exclu."""
    start = date(2024, 1, 5)
    long = {start + timedelta(weeks=i): 0.01 * (i % 3) for i in range(60)}
    short = {start + timedelta(weeks=i): 0.05 for i in range(50, 60)}

    core = weighted_returns({"A": long, "B": short}, {"A": 1.0, "B": 1.0})

    assert core == pytest.approx(long)


def test_overlap_separates_a_us_index_from_a_world_index():
    """Le cosinus voit S&P 500 et World presque identiques (l'USA domine) ; le recouvrement, non."""
    sp500 = {"USA": 100.0}
    world = {"USA": 72.0, "JPN": 5.5, "GBR": 3.5, "CAN": 3.0, "FRA": 2.8, "CHE": 2.5, "DEU": 2.3, "AUS": 1.8}

    assert cosine(sp500, world) > 0.95
    assert overlap(sp500, world) == pytest.approx(72.0 / sum(world.values()))
    assert overlap(world, {k: v * 2 for k, v in world.items()}) == pytest.approx(1.0)
    assert overlap({}, world) == 0.0
