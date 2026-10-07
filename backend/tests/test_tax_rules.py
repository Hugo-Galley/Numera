"""Calculs fiscaux purs : aucun accès base de données."""
from datetime import date

import pytest

from app.core.tax import av_status, livret_a_status, pea_status, per_deduction_ceiling, per_status, years_between
from app.core.tax_rules import rules_for

TODAY = date(2026, 10, 7)
RULES = rules_for(2026)


def test_rules_for_unknown_year_falls_back_to_nearest_known():
    assert rules_for(2099).year == 2026
    assert rules_for(1990).year == 2025


def test_years_between_is_calendar_aware():
    assert years_between(date(2021, 10, 7), date(2026, 10, 7)) == pytest.approx(5.0, abs=0.01)
    assert years_between(date(2021, 10, 8), date(2026, 10, 7)) < 5.0


def test_pea_remaining_room_and_percentage():
    status = pea_status(60_000.0, date(2019, 3, 15), [], TODAY, RULES)
    assert status["current"] == 60_000.0
    assert status["ceiling"] == RULES.pea_ceiling
    assert status["remaining"] == pytest.approx(RULES.pea_ceiling - 60_000.0)
    assert status["used_pct"] == pytest.approx(60_000.0 / RULES.pea_ceiling * 100.0)
    assert status["milestone_years"] == 5
    assert status["milestone_reached"] is True
    assert status["alerts"] == []


def test_pea_over_ceiling_never_negative_and_alerts():
    status = pea_status(RULES.pea_ceiling + 1_000.0, date(2019, 3, 15), [], TODAY, RULES)
    assert status["remaining"] == 0.0
    assert any("plafond" in a.lower() for a in status["alerts"])


def test_pea_withdrawal_before_five_years_alerts():
    status = pea_status(10_000.0, date(2024, 1, 10), [date(2025, 6, 1)], TODAY, RULES)
    assert status["milestone_reached"] is False
    assert any("5 ans" in a for a in status["alerts"])


def test_pea_withdrawal_after_five_years_is_fine():
    status = pea_status(10_000.0, date(2019, 1, 10), [date(2025, 6, 1)], TODAY, RULES)
    assert status["alerts"] == []


def test_pea_without_opening_date_does_not_crash():
    status = pea_status(10_000.0, None, [], TODAY, RULES)
    assert status["age_years"] is None
    assert status["milestone_reached"] is None
    assert any("date d'ouverture" in a.lower() for a in status["alerts"])


def test_per_ceiling_is_ten_percent_bounded_by_floor_and_cap():
    assert per_deduction_ceiling(0.0, RULES) == RULES.per_floor
    assert per_deduction_ceiling(1_000_000.0, RULES) == RULES.per_ceiling
    middle = (RULES.per_floor + RULES.per_ceiling) / 2 / RULES.per_rate
    assert per_deduction_ceiling(middle, RULES) == pytest.approx(middle * RULES.per_rate)


def test_per_status_tax_saving_is_contribution_times_tmi():
    status = per_status(3_000.0, 40_000.0, 30.0, RULES)
    deductible = min(3_000.0, status["ceiling"])
    assert status["current"] == 3_000.0
    assert status["estimated_tax_saving"] == pytest.approx(deductible * 0.30)
    assert status["remaining"] == pytest.approx(status["ceiling"] - 3_000.0)


def test_per_contribution_above_ceiling_only_deducts_the_ceiling():
    status = per_status(100_000.0, 40_000.0, 30.0, RULES)
    assert status["remaining"] == 0.0
    assert status["estimated_tax_saving"] == pytest.approx(status["ceiling"] * 0.30)
    assert status["alerts"]


def test_livret_a_room_and_overflow():
    ok = livret_a_status(10_000.0, RULES)
    assert ok["remaining"] == pytest.approx(RULES.livret_a_ceiling - 10_000.0)
    over = livret_a_status(RULES.livret_a_ceiling + 500.0, RULES)
    assert over["remaining"] == 0.0
    assert over["used_pct"] == pytest.approx((RULES.livret_a_ceiling + 500.0) / RULES.livret_a_ceiling * 100.0)


def test_av_milestone_and_allowance_by_household():
    single = av_status(date(2017, 5, 1), "single", TODAY, RULES)
    couple = av_status(date(2017, 5, 1), "couple", TODAY, RULES)
    assert single["milestone_years"] == 8
    assert single["milestone_reached"] is True
    assert single["allowance"] == RULES.av_allowance_single
    assert couple["allowance"] == RULES.av_allowance_couple


def test_av_before_eight_years_not_reached():
    status = av_status(date(2022, 5, 1), "single", TODAY, RULES)
    assert status["milestone_reached"] is False
    assert status["age_years"] == pytest.approx(4.4, abs=0.1)


def test_pfu_rates_follow_the_official_calendar():
    # LFSS 2026, art. 12 : CSG 9,2 % -> 10,6 % dès les revenus 2025 pour les revenus du patrimoine (plus-values),
    # mais seulement à compter du 1.1.2026 pour les produits de placement (dividendes).
    assert rules_for(2025).pfu_rate_dividends == pytest.approx(0.30)
    assert rules_for(2025).pfu_rate_gains == pytest.approx(0.314)
    assert rules_for(2026).pfu_rate_dividends == pytest.approx(0.314)
    assert rules_for(2026).pfu_rate_gains == pytest.approx(0.314)
