from datetime import date

import pytest

from app.domain.loans import (
    LoanTerms,
    Prepayment,
    build_schedule,
    monthly_payment,
    remaining_principal,
    simulate_prepayment,
)

TERMS = LoanTerms(principal=200_000, annual_rate_pct=3.6, duration_months=300, start_date=date(2025, 1, 5))


def test_monthly_payment_standard():
    assert monthly_payment(200_000, 3.6, 300) == pytest.approx(1012.01, abs=0.01)


def test_monthly_payment_zero_rate():
    assert monthly_payment(12_000, 0, 24) == 500.0


def test_schedule_ends_at_zero():
    rows = build_schedule(TERMS)
    assert len(rows) == 300
    assert rows[0].date == date(2025, 1, 5)
    assert rows[1].date == date(2025, 2, 5)
    assert rows[-1].remaining == 0
    assert sum(r.principal for r in rows) == pytest.approx(200_000, abs=0.01)


def test_schedule_end_of_month_start_date():
    rows = build_schedule(LoanTerms(1_000, 0, 3, date(2025, 1, 31)))
    assert [r.date for r in rows] == [date(2025, 1, 31), date(2025, 2, 28), date(2025, 3, 31)]


def test_zero_rate_schedule_has_no_interest():
    rows = build_schedule(LoanTerms(12_000, 0, 24, date(2025, 1, 1)))
    assert all(r.interest == 0 for r in rows)
    assert rows[-1].remaining == 0


def test_insurance_added_to_rows():
    rows = build_schedule(LoanTerms(12_000, 0, 24, date(2025, 1, 1), insurance_monthly=10))
    assert rows[0].insurance == 10


def test_remaining_principal_bounds():
    assert remaining_principal(TERMS, [], date(2024, 12, 1)) == 200_000
    assert remaining_principal(TERMS, [], date(2060, 1, 1)) == 0
    after_first = remaining_principal(TERMS, [], date(2025, 1, 5))
    assert after_first == pytest.approx(200_000 - (1012.01 - 600), abs=0.02)


def test_prepayment_reduce_duration():
    pp = [Prepayment(date(2030, 1, 10), 20_000, "reduce_duration")]
    rows = build_schedule(TERMS, pp)
    base = build_schedule(TERMS)
    assert len(rows) < 300
    assert rows[100].payment == base[100].payment
    assert rows[-1].remaining == 0
    assert any(r.prepayment == 20_000 for r in rows)


def test_prepayment_reduce_payment():
    pp = [Prepayment(date(2030, 1, 10), 20_000, "reduce_payment")]
    rows = build_schedule(TERMS, pp)
    base = build_schedule(TERMS)
    assert len(rows) == 300
    assert rows[100].payment < base[100].payment
    assert rows[-1].remaining == 0


def test_prepayment_exceeding_remaining_closes_loan():
    pp = [Prepayment(date(2026, 1, 10), 1_000_000, "reduce_duration")]
    rows = build_schedule(TERMS, pp)
    assert rows[-1].remaining == 0
    assert rows[-1].date == date(2026, 1, 5)
    assert all(r.remaining >= 0 and r.principal >= 0 for r in rows)
    assert rows[-1].prepayment < 1_000_000  # plafonné au capital restant
    assert remaining_principal(TERMS, pp, date(2027, 1, 1)) == 0


def test_simulate_prepayment():
    at = date(2030, 1, 10)
    sim = simulate_prepayment(TERMS, [], 20_000, at, "reduce_duration")
    crd = remaining_principal(TERMS, [], at)
    assert sim["interest_saved"] > 0
    assert sim["months_saved"] > 0
    assert sim["total_interest_after"] == pytest.approx(sim["total_interest_before"] - sim["interest_saved"], abs=0.01)
    assert sim["max_penalty"] == pytest.approx(min(20_000 * 0.036 / 12 * 6, 0.03 * crd), abs=0.01)


def test_simulate_reduce_payment_gives_new_payment():
    sim = simulate_prepayment(TERMS, [], 20_000, date(2030, 1, 10), "reduce_payment")
    assert sim["new_payment"] < 1012.01
    assert sim["months_saved"] == 0
