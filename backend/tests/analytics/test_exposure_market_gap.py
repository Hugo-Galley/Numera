"""Écarts au marché par dimension et score de diversification relatif (spec 2026-11-27, § 4 et § 5)."""

import pytest

from app.domain.diversity import CASH_LABEL
from app.domain.etf_normalize import UNKNOWN_LABEL
from app.domain.exposure.market_gap import (
    EXCLUDED_LABELS,
    DimensionGap,
    GapRow,
    dimension_gap,
    is_overweight,
    market_score,
)


def _row(portfolio_pct: float, market_pct: float) -> GapRow:
    return GapRow(
        name="X",
        portfolio_pct=portfolio_pct,
        market_pct=market_pct,
        market_pct_is_upper_bound=False,
        gap_pts=portfolio_pct - market_pct,
    )


def test_excluded_labels() -> None:
    assert frozenset({UNKNOWN_LABEL, CASH_LABEL, "Autres"}) == EXCLUDED_LABELS


def test_identical_to_market_scores_100() -> None:
    gap = dimension_gap({"USA": 600, "JPN": 400}, {"USA": 60, "JPN": 40})

    assert gap.active_share_pct == 0.0
    assert gap.covered_pct == pytest.approx(100.0)
    assert market_score([gap]) == 100.0


def test_nothing_in_common_scores_0() -> None:
    gap = dimension_gap({"Crypto-actifs": 10}, {"USA": 60, "JPN": 40})

    assert gap.active_share_pct == pytest.approx(100.0)
    assert market_score([gap]) == 0.0


def test_excluded_labels_removed_both_sides_then_renormalized() -> None:
    gap = dimension_gap(
        {"USA": 49, UNKNOWN_LABEL: 14, "JPN": 37},
        {"USA": 64, "Autres": 10, "JPN": 26},
    )

    assert gap.covered_pct == pytest.approx(86.0)
    usa = next(r for r in gap.rows if r.name == "USA")
    assert usa.portfolio_pct == pytest.approx(56.98, abs=0.01)
    assert usa.market_pct == pytest.approx(71.11, abs=0.01)
    assert usa.market_pct_is_upper_bound is False
    assert usa.gap_pts == pytest.approx(56.98 - 71.11, abs=0.02)
    assert {r.name for r in gap.rows} == {"USA", "JPN"}
    # ½ Σ |w − b| : |56.98 − 71.11| + |43.02 − 28.89| = 28.26 → 14.13
    assert gap.active_share_pct == pytest.approx(14.13, abs=0.02)


def test_cash_excluded() -> None:
    gap = dimension_gap({"USA": 80, CASH_LABEL: 20}, {"USA": 100})

    assert gap.covered_pct == pytest.approx(80.0)
    assert gap.active_share_pct == 0.0
    assert [r.name for r in gap.rows] == ["USA"]


def test_rows_sorted_by_gap_descending() -> None:
    gap = dimension_gap({"A": 50, "B": 30, "C": 20}, {"A": 30, "B": 30, "C": 40})

    assert [r.name for r in gap.rows] == ["A", "B", "C"]
    assert [r.gap_pts for r in gap.rows] == pytest.approx([20.0, 0.0, -20.0])


def test_name_only_in_market_gets_zero_portfolio() -> None:
    gap = dimension_gap({"USA": 100}, {"USA": 60, "JPN": 40})

    jpn = next(r for r in gap.rows if r.name == "JPN")
    assert jpn.portfolio_pct == 0.0
    assert jpn.market_pct == pytest.approx(40.0)
    assert gap.active_share_pct == pytest.approx(40.0)


def test_absent_from_market_without_floor_is_zero() -> None:
    gap = dimension_gap({"Apple": 50, "Nvidia": 50}, {"Apple": 100})

    nvidia = next(r for r in gap.rows if r.name == "Nvidia")
    assert nvidia.market_pct == 0.0
    assert nvidia.market_pct_is_upper_bound is False


def test_absent_from_partial_market_gets_floor_as_upper_bound() -> None:
    gap = dimension_gap(
        {"Apple": 40, "Air Liquide": 60},
        {"Apple": 60, "Microsoft": 39.2, "Nvidia": 0.8},
        market_floor=0.8,
    )

    air_liquide = next(r for r in gap.rows if r.name == "Air Liquide")
    assert air_liquide.market_pct == pytest.approx(0.8)
    assert air_liquide.market_pct_is_upper_bound is True
    assert air_liquide.gap_pts == pytest.approx(59.2)
    apple = next(r for r in gap.rows if r.name == "Apple")
    assert apple.market_pct_is_upper_bound is False


def test_floor_is_renormalized_like_the_market() -> None:
    # Top holdings connus à 50 % : le marché est doublé à la renormalisation, la borne aussi
    gap = dimension_gap({"Apple": 50, "Air Liquide": 50}, {"Apple": 40, "Nvidia": 10}, market_floor=10)

    air_liquide = next(r for r in gap.rows if r.name == "Air Liquide")
    assert air_liquide.market_pct == pytest.approx(20.0)


def test_empty_portfolio() -> None:
    gap = dimension_gap({UNKNOWN_LABEL: 100}, {"USA": 100})

    assert gap.covered_pct == 0.0
    assert gap.active_share_pct == 0.0
    assert gap.rows == ()


def test_empty_market_is_nothing_in_common() -> None:
    gap = dimension_gap({"USA": 100}, {"Autres": 100})

    assert gap.active_share_pct == 100.0


@pytest.mark.parametrize(
    ("portfolio_pct", "market_pct", "expected"),
    [
        (38, 25, True),
        (6, 4.5, False),  # ratio 1,33
        (12, 0, True),
        (7, 3, False),  # +4 pts seulement
    ],
)
def test_is_overweight(portfolio_pct: float, market_pct: float, expected: bool) -> None:
    assert is_overweight(_row(portfolio_pct, market_pct)) is expected


def test_market_score_averages_dimensions() -> None:
    gaps = [DimensionGap(active_share_pct=a, covered_pct=100.0, rows=()) for a in (10.0, 20.0, 33.33)]

    assert market_score(gaps) == 78.9


def test_market_score_without_dimension_is_neutral() -> None:
    assert market_score([]) == 50.0


def test_dimension_without_comparable_holdings_is_left_out_of_the_score() -> None:
    """Composition inconnue (tout en « Non renseigné ») : la dimension n'informe pas, elle ne vaut pas 100."""
    unknown = dimension_gap({UNKNOWN_LABEL: 100}, {"USA": 100})
    known = DimensionGap(active_share_pct=40.0, covered_pct=80.0, rows=())

    assert market_score([unknown, known]) == 60.0
    assert market_score([unknown, unknown]) == 50.0
