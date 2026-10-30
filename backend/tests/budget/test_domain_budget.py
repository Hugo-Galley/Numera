"""Formules pures du budget : conversion EUR, taux d'épargne, jours écoulés, alertes de plafond."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.domain.budget import budget_alert, elapsed_days, savings_rate, sort_alerts, spending_by_category, to_eur

RATES = {"EUR": 1.0, "USD": 1.08}


def test_to_eur_sums_per_currency():
    assert to_eur({"EUR": 100, "USD": 108}, RATES) == pytest.approx(200.0)


def test_to_eur_accepts_query_rows_and_unknown_currency_counts_at_par():
    assert to_eur([("EUR", 10.0), ("CHF", 5.0)], RATES) == pytest.approx(15.0)


def test_savings_rate_zero_income_is_zero():
    assert savings_rate(0.0, 500.0) == 0.0


def test_savings_rate_is_capped():
    assert savings_rate(1000.0, 250.0) == pytest.approx(75.0)
    assert savings_rate(100.0, 1000.0) == -100.0


def test_elapsed_days_stops_at_tomorrow_and_is_at_least_one():
    now = datetime(2026, 6, 15, 10)
    assert elapsed_days(datetime(2026, 6, 1), datetime(2026, 7, 1), now) == 15
    assert elapsed_days(datetime(2026, 5, 1), datetime(2026, 6, 1), now) == 31
    assert elapsed_days(datetime(2026, 7, 1), datetime(2026, 8, 1), now) == 1


def test_spending_by_category_converts_and_accumulates():
    rows = [(1, "EUR", 10.0), (1, "USD", 10.8), (2, "EUR", 5.0)]
    assert spending_by_category(rows, RATES) == pytest.approx({1: 20.0, 2: 5.0})


def test_budget_alert_ratios_and_sort():
    food = SimpleNamespace(id=1, name="Courses", icon=None, color=None, monthly_limit=200.0, annual_limit=None)
    fun = SimpleNamespace(id=2, name="Loisirs", icon=None, color=None, monthly_limit=None, annual_limit=100.0)
    a = budget_alert(food, 150.004, 900.0)
    b = budget_alert(fun, 0.0, 120.0)
    assert (a.monthly_spent, a.monthly_ratio, a.annual_ratio) == (150.0, 150.004 / 200.0, None)
    assert b.annual_ratio == pytest.approx(1.2)
    assert [alert.category_id for alert in sort_alerts([a, b])] == [2, 1]
