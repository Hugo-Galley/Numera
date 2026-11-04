"""Virements récurrents dans la projection « À venir » et le calendrier (constat 11 de l'audit)."""
from datetime import datetime

import pytest
from freezegun import freeze_time

from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction

NOW = "2026-06-10 12:00:00"


def _account(db, name, type_, balance, currency="EUR") -> Account:
    acc = Account(name=name, type=type_, currency=currency, active=True)
    db.add(acc)
    db.flush()
    db.add(Transaction(account_id=acc.id, date=datetime(2026, 6, 1), month_label="2026-06", type="Solde Initial",
                       merchant="Init", amount=balance, original_amount=balance, currency=currency,
                       running_balance=balance))
    db.commit()
    return acc


@pytest.fixture
def setup(client, db_session):
    # Routes construites à la première requête : à faire hors freeze_time (datetime factice)
    client.get("/analytics/cashflow-projection")
    client.get("/analytics/calendar?month=6&year=2026")
    courant = _account(db_session, "Courant", "courant", 2000.0)
    livret = _account(db_session, "Livret", "epargne", 1000.0)
    rd = RecurringTransaction(account_id=courant.id, name="Epargne", type="Sortie", amount=300.0, currency="EUR",
                              frequency="monthly", day_of_month=20, start_date=datetime(2026, 1, 20),
                              is_active=True, auto_generate=True, transfer_to_account_id=livret.id)
    db_session.add(rd)
    db_session.commit()
    return courant, livret, rd


def test_account_projection_counts_incoming_recurring_transfer(client, setup):
    _, livret, _ = setup
    with freeze_time(NOW):
        data = client.get("/analytics/cashflow-projection", params={"days": 30, "account_id": livret.id}).json()
    assert data["current_balance"] == 1000.0
    assert [e["amount"] for e in data["events"] if e["is_income"]] == [300.0]
    assert data["projected_balance"] == 1300.0


def test_incoming_transfer_uses_the_credit_day_and_destination_currency(client, db_session, setup):
    _, livret, rd = setup
    livret.currency = "USD"
    rd.transfer_credit_day = 25
    db_session.commit()
    with freeze_time(NOW):
        data = client.get("/analytics/cashflow-projection", params={"days": 30, "account_id": livret.id}).json()
    incoming = [e for e in data["events"] if e["is_income"]]
    assert len(incoming) == 1
    assert incoming[0]["date"].startswith("2026-06-25")
    assert incoming[0]["amount"] != 300.0  # converti EUR -> USD


def test_global_projection_ignores_internal_transfer(client, setup):
    with freeze_time(NOW):
        data = client.get("/analytics/cashflow-projection", params={"days": 30}).json()
    assert data["projected_balance"] == data["current_balance"]


def test_calendar_account_view_shows_incoming_transfer(client, setup):
    _, livret, _ = setup
    with freeze_time(NOW):
        data = client.get(f"/analytics/calendar?month=6&year=2026&account_id={livret.id}").json()
    incoming = [e for e in data["events"] if e["is_projected"]]
    assert [(e["type"], e["amount"], e["account_id"]) for e in incoming] == [("Entree", 300.0, livret.id)]
    assert data["daily_balances"][-1]["balance"] == 1300.0


def test_calendar_global_view_does_not_count_the_transfer(client, setup):
    with freeze_time(NOW):
        data = client.get("/analytics/calendar?month=6&year=2026").json()
    assert data["daily_balances"][-1]["balance"] == 3000.0
