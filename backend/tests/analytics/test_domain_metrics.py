"""Calculs purs des métriques : agrégats par tag, ligne du kpi-history, épargne à une date, calendrier."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.domain.metrics import daily_balances, kpi_row, net_flow, savings_at, tag_totals, variation_pct

RATES = {"EUR": 1.0, "USD": 2.0}


def test_tag_totals_converts_sums_and_sorts():
    rows = [
        SimpleNamespace(id=1, name="Vacances", color=None, currency="EUR", total=10.0),
        SimpleNamespace(id=2, name="Cadeaux", color="#f00", currency="USD", total=50.0),
        SimpleNamespace(id=1, name="Vacances", color=None, currency="USD", total=40.0),
    ]
    assert tag_totals(rows, RATES) == [
        {"id": 1, "name": "Vacances", "color": None, "total_eur": 30.0},
        {"id": 2, "name": "Cadeaux", "color": "#f00", "total_eur": 25.0},
    ]


def test_net_flow_and_variation():
    assert net_flow({"Entree": 100.0, "Interets": 5.0, "Sortie": 30.0}) == 75.0
    assert variation_pct(75.0, 50.0) == 50.0
    assert variation_pct(10.0, 0.0) is None


def test_kpi_row_global_view_only_subtracts_categorized_investments():
    row = kpi_row(2026, 5, rev=2000.0, inte=10.0, dep=1500.0, inv=500.0, cat_inv=200.0, epargne=8000.0, account_view=False)
    assert row["depenses_reelles"] == 1300.0
    assert row["taux_epargne"] == 35.0
    assert row["label"] == "5/2026"
    assert kpi_row(2026, 5, 0.5, 0.0, 10.0, 0.0, 0.0, 0.0, account_view=True)["taux_epargne"] is None


def test_savings_at_takes_last_value_before_end_in_eur():
    events = {1: [(datetime(2026, 1, 1), 0, 100.0), (datetime(2026, 3, 1), 0, 300.0)], 2: [(datetime(2026, 4, 1), 0, 50.0)]}
    accounts = {1: SimpleNamespace(currency="USD"), 2: SimpleNamespace(currency="EUR")}
    assert savings_at(events, datetime(2026, 2, 1), accounts, RATES) == pytest.approx(50.0)
    assert savings_at(events, datetime(2026, 5, 1), accounts, RATES) == pytest.approx(200.0)


def test_daily_balances_syncs_real_running_balance_and_projects_recurrences():
    events = [
        {"date": "2026-06-02T00:00:00", "account_id": 1, "type": "Sortie", "amount": 30.0, "is_projected": False, "running_balance": 70.0},
        {"date": "2026-06-03T00:00:00", "account_id": 1, "type": "Entree", "amount": 100.0, "is_projected": True},
    ]
    result = daily_balances(
        events, {1: 100.0}, {1: "EUR"}, RATES,
        sim_start=datetime(2026, 6, 1), start_month=datetime(2026, 6, 1), end_month=datetime(2026, 6, 4), account_id=None,
    )
    assert [d["balance"] for d in result] == [100.0, 70.0, 170.0]
