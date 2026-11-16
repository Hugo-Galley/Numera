"""XIRR, TWR et échantillonnage de la courbe d'un compte titres (sans base)."""
from datetime import date, datetime

import pytest

from app.domain.performance import twr, xirr
from app.domain.portfolio import reconciliation_line, sample_days


def test_xirr_doubling_in_one_year():
    assert xirr([(date(2025, 1, 1), -100.0), (date(2026, 1, 1), 200.0)]) == pytest.approx(1.0, abs=1e-6)


def test_twr_ignores_flows():
    assert twr([(date(2025, 1, 1), 100.0, 0.0), (date(2025, 2, 1), 210.0, 100.0)]) == pytest.approx(0.1)


def test_sample_days_includes_bounds_and_extra():
    days = sample_days(date(2025, 1, 1), date(2025, 1, 20), {date(2025, 1, 3), date(2024, 12, 1)})
    assert days == [date(2025, 1, 1), date(2025, 1, 3), date(2025, 1, 8), date(2025, 1, 15), date(2025, 1, 20)]


def test_reconciliation_line_flags_gap_above_threshold():
    line = reconciliation_line(datetime(2026, 1, 5, 10), 1000.0, 1030.0)
    assert (line["gap"], line["gap_pct"], line["flagged"]) == (30.0, 3.0, True)
    assert reconciliation_line(datetime(2026, 1, 5), 0.0, 10.0)["flagged"] is False


def test_xirr_one_year_ten_percent():
    flows = [(date(2025, 1, 1), -100.0), (date(2026, 1, 1), 110.0)]
    assert xirr(flows) == pytest.approx(0.10, abs=1e-4)


def test_xirr_needs_both_signs():
    assert xirr([(date(2025, 1, 1), -100.0)]) is None
    assert xirr([(date(2025, 1, 1), 100.0), (date(2025, 6, 1), 50.0)]) is None


def test_xirr_weights_late_deposit_less_than_simple_return():
    # 100 investis un an, 100 de plus à mi-parcours, 230 à la fin
    flows = [(date(2025, 1, 1), -100.0), (date(2025, 7, 2), -100.0), (date(2026, 1, 1), 230.0)]
    rate = xirr(flows)
    assert 0.18 < rate < 0.40


def test_twr_ignores_deposit_timing():
    # 100 → 110 (+10 %), puis dépôt de 100 et valeur 220 : avant dépôt 120 sur 110 (+9,09 %) ⇒ +20 % cumulé
    points = [(date(2025, 1, 1), 100.0, 0.0), (date(2025, 2, 1), 110.0, 0.0), (date(2025, 3, 1), 220.0, 100.0)]
    assert twr(points) == pytest.approx(0.20, abs=1e-6)


# ─── Valeur et plus-value latente ───────────────────────────────────────────


# ─── Pire baisse (max drawdown) ─────────────────────────────────────────────

def test_max_drawdown_measures_peak_to_trough_on_flow_neutral_index():
    from app.domain.performance import max_drawdown

    # 100 → 120 (pic) → 90 (creux, −25 %) → 130 (récupéré le 4 avril)
    points = [
        (date(2025, 1, 1), 100.0, 0.0), (date(2025, 2, 1), 120.0, 0.0), (date(2025, 3, 1), 90.0, 0.0),
        (date(2025, 4, 1), 130.0, 0.0), (date(2025, 5, 1), 117.0, 0.0),
    ]
    result = max_drawdown(points)
    assert result["max_drawdown_pct"] == pytest.approx(-25.0)
    assert result["peak_date"] == date(2025, 2, 1)
    assert result["trough_date"] == date(2025, 3, 1)
    assert result["recovery_date"] == date(2025, 4, 1)
    assert result["current_drawdown_pct"] == pytest.approx(-10.0)  # 117 sous le pic 130


def test_max_drawdown_is_not_hidden_by_a_deposit():
    from app.domain.performance import max_drawdown

    # −50 % puis gros versement : la valeur brute remonte, l'indice reste au creux
    points = [(date(2025, 1, 1), 100.0, 0.0), (date(2025, 2, 1), 50.0, 0.0), (date(2025, 3, 1), 1050.0, 1000.0)]
    result = max_drawdown(points)
    assert result["max_drawdown_pct"] == pytest.approx(-50.0)
    assert result["recovery_date"] is None
    assert result["current_drawdown_pct"] == pytest.approx(-50.0)


def test_max_drawdown_none_without_history_and_zero_when_always_rising():
    from app.domain.performance import max_drawdown

    assert max_drawdown([(date(2025, 1, 1), 100.0, 0.0)]) is None
    rising = max_drawdown([(date(2025, 1, 1), 100.0, 0.0), (date(2025, 2, 1), 110.0, 0.0)])
    assert rising["max_drawdown_pct"] == 0.0 and rising["trough_date"] is None and rising["current_drawdown_pct"] == 0.0


def test_combine_points_sums_accounts_and_treats_a_late_account_as_a_deposit():
    from app.domain.performance import combine_points, twr

    a = [(date(2025, 1, 1), 100.0, 0.0), (date(2025, 1, 15), 110.0, 0.0)]
    b = [(date(2025, 1, 8), 50.0, 0.0), (date(2025, 1, 15), 55.0, 0.0)]  # compte ouvert plus tard
    combined = combine_points([a, b])
    assert combined == [
        (date(2025, 1, 1), 100.0, 0.0),
        (date(2025, 1, 8), 150.0, 50.0),  # a reporté à 100, b entre comme un versement
        (date(2025, 1, 15), 165.0, 0.0),
    ]
    assert twr(combined) == pytest.approx(0.10)
