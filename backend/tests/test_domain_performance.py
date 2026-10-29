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
