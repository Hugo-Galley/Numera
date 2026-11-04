"""Règle 12 : `end` d'une période et `end_of_today()` sont des bornes **exclusives** (lues avec `<`).

Une transaction datée du 1er du mois suivant, ou de demain, ne compte ni dans le mois qui se termine
ni dans un solde « à ce jour ».
"""
import asyncio
from datetime import datetime

from freezegun import freeze_time

from app.models.account import Account
from app.services.comptes.wealth import account_values

NOW = "2026-03-10 12:00:00"


def _account(client, name="Courant", type_="courant"):
    return client.post("/accounts", json={"name": name, "type": type_, "currency": "EUR"}).json()["id"]


def _tx(client, account_id, date, type_, amount, merchant="x", category_id=None):
    body = {"account_id": account_id, "date": date, "type": type_, "merchant": merchant, "amount": amount}
    if category_id:
        body["category_id"] = category_id
    response = client.post("/transactions", json=body)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _month_boundary_account(client, type_="courant"):
    account_id = _account(client, type_=type_)
    _tx(client, account_id, "2026-02-01T00:00:00", "Solde Initial", 1000.0)
    _tx(client, account_id, "2026-03-01T00:00:00", "Entree", 2000.0, "Salaire")  # 1er jour du mois suivant
    return account_id


def test_wealth_of_a_past_month_excludes_the_first_day_of_the_next_month(db_session, client):
    with freeze_time(NOW):
        account_id = _month_boundary_account(client)
        accounts = db_session.query(Account).all()
        values = asyncio.run(account_values(db_session, accounts, datetime(2026, 3, 1)))
    assert values[account_id].value == 1000.0


def test_wealth_by_default_counts_everything_dated_today(db_session, client):
    with freeze_time(NOW):
        account_id = _account(client)
        _tx(client, account_id, "2026-03-01T00:00:00", "Solde Initial", 1000.0)
        _tx(client, account_id, "2026-03-10T18:00:00", "Sortie", 40.0)  # plus tard dans la journée
        accounts = db_session.query(Account).all()
        values = asyncio.run(account_values(db_session, accounts))
    assert values[account_id].value == 960.0


def test_budget_of_a_past_month_excludes_the_next_months_first_day(client):
    with freeze_time(NOW):
        _month_boundary_account(client)
        budget = client.get("/analytics/budget", params={"month": 2, "year": 2026}).json()
    assert budget["solde_actuel"] == 1000.0


def test_budget_of_an_account_in_a_past_month_excludes_the_next_months_first_day(client):
    with freeze_time(NOW):
        account_id = _month_boundary_account(client)
        budget = client.get("/analytics/budget", params={"month": 2, "year": 2026, "account_id": account_id}).json()
    assert budget["solde_actuel"] == 1000.0


def test_month_ending_today_is_not_the_current_period(client):
    """Le jour de la borne (1er mars), février est passé : le salaire du jour appartient à mars."""
    with freeze_time("2026-03-01 08:00:00"):
        account_id = _month_boundary_account(client)
        global_view = client.get("/analytics/budget", params={"month": 2, "year": 2026}).json()
        account_view = client.get("/analytics/budget", params={"month": 2, "year": 2026, "account_id": account_id}).json()
    assert global_view["solde_actuel"] == 1000.0
    assert account_view["solde_actuel"] == 1000.0


def test_savings_in_kpi_history_exclude_the_next_months_first_day(client):
    with freeze_time(NOW):
        account_id = _month_boundary_account(client, type_="epargne")
        _tx(client, account_id, "2026-02-10T00:00:00", "Sortie", 10.0)  # un mois février non vide
        rows = client.get("/analytics/kpi-history", params={"months_count": 3}).json()
    february = next(row for row in rows if row["month"] == 2 or row.get("label", "").startswith("2026-02"))
    assert february["epargne"] == 990.0


def test_budget_alerts_annual_total_stops_today(client):
    with freeze_time(NOW):
        account_id = _account(client)
        category = client.post("/categories", json={"name": "Loisirs", "type": "depense", "annual_limit": 1000.0}).json()
        _tx(client, account_id, "2026-03-05T00:00:00", "Sortie", 100.0, "Cine", category["id"])
        _tx(client, account_id, "2026-09-05T00:00:00", "Sortie", 300.0, "Concert", category["id"])  # à venir
        alerts = client.get("/analytics/budget-alerts", params={"month": 3, "year": 2026}).json()
    assert next(a for a in alerts if a["category_id"] == category["id"])["annual_spent"] == 100.0


def test_savings_goal_ignores_upcoming_transactions(client):
    with freeze_time(NOW):
        account_id = _account(client, "Livret", "epargne")
        _tx(client, account_id, "2026-03-05T00:00:00", "Entree", 100.0, "Vacances")
        _tx(client, account_id, "2026-03-20T00:00:00", "Entree", 400.0, "Vacances")  # à venir
        client.post("/goals", json={"name": "Vacances", "target_amount": 1000, "keyword": "vacances"})
        goal = client.get("/goals").json()[0]
    assert goal["current_amount"] == 100.0
