"""Une transaction datée dans le futur ne compte qu'à sa date : ni solde, ni KPI, ni patrimoine avant.

`running_balance` reste calculé dans l'ordre chronologique (la ligne future est la dernière) ;
seules les lectures « courantes » ignorent ce qui est postérieur à aujourd'hui.
"""
import asyncio

import pytest
from freezegun import freeze_time

from app.models.account import Account
from app.services.comptes.wealth import account_values

NOW = "2026-03-10 12:00:00"


def _account(client, name="Courant", type_="courant"):
    return client.post("/accounts", json={"name": name, "type": type_, "currency": "EUR"}).json()["id"]


def _tx(client, account_id, day, type_, amount, merchant="x", month=3):
    response = client.post("/transactions", json={"account_id": account_id, "date": f"2026-{month:02d}-{day:02d}T00:00:00",
                                                  "type": type_, "merchant": merchant, "amount": amount})
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
def account_with_future_expense(client):
    with freeze_time(NOW):
        account_id = _account(client)
        _tx(client, account_id, 1, "Solde Initial", 1000.0)
        _tx(client, account_id, 5, "Entree", 500.0, "Salaire")
        _tx(client, account_id, 8, "Sortie", 100.0, "Courses")
        _tx(client, account_id, 20, "Sortie", 200.0, "Loyer")  # dans 10 jours
        yield account_id


def test_future_transaction_keeps_chronological_running_balance(client, account_with_future_expense):
    with freeze_time(NOW):
        rows = client.get("/transactions", params={"account_id": account_with_future_expense}).json()
    items = rows["items"] if isinstance(rows, dict) else rows
    balances = {item["merchant"]: item["running_balance"] for item in items}
    assert balances["Courses"] == 1400.0
    assert balances["Loyer"] == 1200.0


def test_future_transaction_does_not_change_account_balance(client, account_with_future_expense):
    with freeze_time(NOW):
        balance = client.get(f"/accounts/{account_with_future_expense}").json()["balance"]
    assert balance == 1400.0


def test_account_balance_includes_transaction_dated_today(client):
    with freeze_time(NOW):
        account_id = _account(client)
        _tx(client, account_id, 1, "Solde Initial", 1000.0)
        _tx(client, account_id, 10, "Sortie", 50.0)  # aujourd'hui, minuit
        assert client.get(f"/accounts/{account_id}").json()["balance"] == 950.0


def test_balance_follows_the_calendar(client, account_with_future_expense):
    with freeze_time("2026-03-21 08:00:00"):
        balance = client.get(f"/accounts/{account_with_future_expense}").json()["balance"]
    assert balance == 1200.0


def test_budget_month_excludes_future_transactions(client, account_with_future_expense):
    with freeze_time(NOW):
        budget = client.get("/analytics/budget", params={"month": 3, "year": 2026}).json()
    assert budget["depenses_totales"] == 100.0
    assert budget["revenus_totaux"] == 500.0
    assert budget["solde_actuel"] == 1400.0


def test_budget_of_the_account_excludes_future_transactions(client, account_with_future_expense):
    with freeze_time(NOW):
        budget = client.get("/analytics/budget", params={"month": 3, "year": 2026,
                                                         "account_id": account_with_future_expense}).json()
    assert budget["depenses_totales"] == 100.0
    assert budget["solde_actuel"] == 1400.0


def test_expenses_by_category_exclude_future_transactions(client, account_with_future_expense):
    with freeze_time(NOW):
        data = client.get("/analytics/expenses-by-category", params={"month": 3, "year": 2026}).json()
    assert data["total"] == 100.0


def test_wealth_excludes_future_transactions(db_session, client, account_with_future_expense):
    with freeze_time(NOW):
        accounts = db_session.query(Account).all()
        values = asyncio.run(account_values(db_session, accounts))
    assert values[account_with_future_expense].value == 1400.0


def test_cashflow_projection_starts_from_todays_balance(client, account_with_future_expense):
    with freeze_time(NOW):
        projection = client.get("/analytics/cashflow-projection", params={"account_id": account_with_future_expense}).json()
    assert projection["current_balance"] == 1400.0


def test_a_later_import_row_in_the_past_still_chains_after_the_future_one(client, account_with_future_expense):
    """Insérer une ligne passée recalcule tout : la ligne future garde sa place chronologique."""
    with freeze_time(NOW):
        _tx(client, account_with_future_expense, 9, "Sortie", 50.0, "Cafe")
        items = client.get("/transactions", params={"account_id": account_with_future_expense}).json()
        items = items["items"] if isinstance(items, dict) else items
        balances = {item["merchant"]: item["running_balance"] for item in items}
        assert balances["Loyer"] == 1150.0
        assert client.get(f"/accounts/{account_with_future_expense}").json()["balance"] == 1350.0


def test_period_bounds_stop_at_tomorrow_but_the_window_stays_whole(db_session):
    from datetime import datetime

    from app.services.budget import budget_period
    with freeze_time(NOW):
        assert budget_period.period_window(db_session, 2026, 3) == (datetime(2026, 3, 1), datetime(2026, 4, 1))
        assert budget_period.period_bounds(db_session, 2026, 3) == (datetime(2026, 3, 1), datetime(2026, 3, 11))
        # Un mois passé n'est pas touché
        assert budget_period.period_bounds(db_session, 2026, 2) == (datetime(2026, 2, 1), datetime(2026, 3, 1))


def test_default_budget_counts_a_transaction_dated_later_today(client):
    """Granularité au jour : une dépense du jour compte même si son heure n'est pas encore passée."""
    with freeze_time(NOW):
        account_id = _account(client)
        _tx(client, account_id, 1, "Solde Initial", 1000.0)
        client.post("/transactions", json={"account_id": account_id, "date": "2026-03-10T21:00:00", "type": "Sortie",
                                           "merchant": "Resto", "amount": 40.0})
        default_view = client.get("/analytics/budget").json()
        month_view = client.get("/analytics/budget", params={"month": 3, "year": 2026}).json()
    assert default_view["depenses_totales"] == month_view["depenses_totales"] == 40.0


def test_balance_curve_stops_at_today(client, account_with_future_expense):
    with freeze_time(NOW):
        points = client.get("/analytics/timeseries", params={"year": 2026, "account_id": account_with_future_expense}).json()["balance_points"]
    assert [p["running_balance"] for p in points] == [1000.0, 1500.0, 1400.0]


def test_transactions_list_flags_upcoming_rows(client, account_with_future_expense):
    with freeze_time(NOW):
        rows = client.get("/transactions", params={"account_id": account_with_future_expense}).json()
        created = client.post("/transactions", json={"account_id": account_with_future_expense, "date": "2026-03-10T09:00:00",
                                                     "type": "Sortie", "merchant": "Ce matin", "amount": 5.0}).json()
    items = rows["items"] if isinstance(rows, dict) else rows
    flags = {item["merchant"]: item["is_upcoming"] for item in items}
    assert flags == {"x": False, "Salaire": False, "Courses": False, "Loyer": True}
    assert created["is_upcoming"] is False
