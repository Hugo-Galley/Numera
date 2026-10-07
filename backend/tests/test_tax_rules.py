"""Calculs fiscaux purs : aucun accès base de données."""
from datetime import date

import pytest

from app.core.tax import (
    PeeLot, av_status, livret_a_status, livret_jeune_status, pea_status, pee_status, per_deduction_ceiling, per_status,
    years_between,
)
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


def test_livret_jeune_has_its_own_ceiling_and_never_calls_overflow_an_irregularity():
    ok = livret_jeune_status(900.0, RULES)
    assert ok["ceiling"] == 1_600.0
    assert ok["remaining"] == pytest.approx(700.0)
    over = livret_jeune_status(1_650.0, RULES)
    assert over["remaining"] == 0.0
    assert any("intérêts" in a for a in over["alerts"])


def test_livret_a_overflow_alert_mentions_capitalised_interest():
    assert any("intérêts" in a for a in livret_a_status(RULES.livret_a_ceiling + 10.0, RULES)["alerts"])


PEE_TODAY = date(2026, 10, 7)


def test_pee_splits_blocked_and_available_and_finds_next_unlock():
    lots = [
        PeeLot(date(2019, 3, 1), 1_000.0, False),
        PeeLot(date(2024, 6, 1), 500.0, False),
        PeeLot(date(2026, 2, 1), 300.0, False),
    ]
    status = pee_status(lots, 0.0, 40_000.0, PEE_TODAY, RULES)
    assert status["total_contributed"] == 1_800.0
    assert status["available"] == 1_000.0
    assert status["blocked"] == 800.0
    assert status["next_unlock_date"] == "2029-06-01"


def test_pee_withdrawals_consume_the_oldest_lots_first():
    lots = [PeeLot(date(2019, 3, 1), 1_000.0, False), PeeLot(date(2024, 6, 1), 500.0, False)]
    status = pee_status(lots, 400.0, 40_000.0, PEE_TODAY, RULES)
    assert status["available"] == 600.0
    assert status["blocked"] == 500.0
    assert status["total_contributed"] == 1_500.0   # cumul des versements ; bloqué + disponible = encours après retraits


def test_pee_voluntary_cap_is_a_quarter_of_gross_salary_and_excludes_employer_contributions():
    lots = [
        PeeLot(date(2026, 2, 1), 2_000.0, False),
        PeeLot(date(2026, 3, 1), 3_000.0, True),   # abondement de l'employeur
        PeeLot(date(2025, 12, 1), 9_000.0, False),  # année précédente
    ]
    status = pee_status(lots, 0.0, 40_000.0, PEE_TODAY, RULES)
    assert status["ceiling"] == pytest.approx(10_000.0)
    assert status["current"] == 2_000.0
    assert status["remaining"] == pytest.approx(8_000.0)


def test_pee_without_gross_salary_has_no_ceiling_and_says_why():
    status = pee_status([PeeLot(date(2026, 2, 1), 100.0, False)], 0.0, 0.0, PEE_TODAY, RULES)
    assert status["ceiling"] is None and status["remaining"] is None
    assert any("salaire brut" in a.lower() for a in status["alerts"])


def test_pee_over_the_voluntary_ceiling_alerts():
    status = pee_status([PeeLot(date(2026, 2, 1), 12_000.0, False)], 0.0, 40_000.0, PEE_TODAY, RULES)
    assert status["remaining"] == 0.0
    assert any("plafond" in a.lower() for a in status["alerts"])


def test_pee_with_no_contribution_is_empty_not_an_error():
    status = pee_status([], 0.0, 40_000.0, PEE_TODAY, RULES)
    assert status["total_contributed"] == 0.0 and status["next_unlock_date"] is None
