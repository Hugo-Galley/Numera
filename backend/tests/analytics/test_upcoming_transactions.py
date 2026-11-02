"""Transactions à venir : saisies futures dans la projection de trésorerie et le calendrier.

Les récurrences ne sont générées que le jour J ; une saisie manuelle datée dans le futur est une
vraie ligne en base. La projection les additionne, sans double compter une échéance déjà saisie.
"""
from datetime import datetime

import pytest
from freezegun import freeze_time

from app.domain.reports import flag_possible_duplicates
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.schemas.insight import ProjectionEvent
from app.services.budget.balances import recalculate_running_balances

NOW = "2026-03-10 12:00:00"


def _tx(client, account_id, day, type_, amount, merchant="x", month=3):
    payload = {"account_id": account_id, "date": f"2026-{month:02d}-{day:02d}T00:00:00", "type": type_,
               "merchant": merchant, "amount": amount}
    response = client.post("/transactions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
def account_id(client):
    with freeze_time(NOW):
        account = client.post("/accounts", json={"name": "Courant", "type": "courant", "currency": "EUR"}).json()["id"]
        _tx(client, account, 1, "Solde Initial", 1000.0)
        _tx(client, account, 5, "Entree", 500.0, "Salaire")
        _tx(client, account, 8, "Sortie", 100.0, "Courses")
        yield account


def _projection(client, account_id=None, days=30):
    params = {"days": days}
    if account_id:
        params["account_id"] = account_id
    return client.get("/analytics/cashflow-projection", params=params).json()


def _netflix(db_session, account_id) -> RecurringTransaction:
    rd = RecurringTransaction(account_id=account_id, name="Netflix", type="Sortie", amount=15.0, currency="EUR",
                              frequency="monthly", day_of_month=15, start_date=datetime(2026, 1, 15), is_active=True)
    db_session.add(rd)
    db_session.commit()
    return rd


def test_future_entry_is_a_scheduled_event_and_moves_the_projected_balance(client, account_id):
    with freeze_time(NOW):
        _tx(client, account_id, 20, "Sortie", 200.0, "Loyer")
        data = _projection(client, account_id)
    scheduled = [e for e in data["events"] if e["type"] == "scheduled"]
    assert [(e["name"], e["amount"], e["is_income"], e["date"][:10]) for e in scheduled] == [("Loyer", 200.0, False, "2026-03-20")]
    assert scheduled[0]["transaction_id"] is not None
    assert data["current_balance"] == 1400.0
    assert data["projected_balance"] == 1200.0


def test_future_income_adds_to_the_projected_balance(client, account_id):
    with freeze_time(NOW):
        _tx(client, account_id, 25, "Entree", 300.0, "Prime")
        data = _projection(client, account_id)
    assert data["projected_balance"] == 1700.0


def test_past_and_today_transactions_are_not_upcoming(client, account_id):
    with freeze_time(NOW):
        _tx(client, account_id, 10, "Sortie", 30.0, "Aujourd'hui")
        data = _projection(client, account_id)
    assert [e for e in data["events"] if e["type"] == "scheduled"] == []
    assert data["current_balance"] == 1370.0


def test_entry_beyond_the_horizon_is_not_listed(client, account_id):
    with freeze_time(NOW):
        _tx(client, account_id, 5, "Sortie", 80.0, "Lointain", month=7)
        data = _projection(client, account_id, days=30)
    assert [e for e in data["events"] if e["type"] == "scheduled"] == []


def test_entered_occurrence_of_a_recurrence_is_not_counted_twice(client, db_session, account_id):
    with freeze_time(NOW):
        rd = _netflix(db_session, account_id)
        # Ligne liée à la récurrence, comme la crée le moteur de génération (l'API de saisie ne pose pas ce lien)
        db_session.add(Transaction(account_id=account_id, date=datetime(2026, 3, 15), month_label="2026-03", type="Sortie",
                                   merchant="Netflix", amount=15.0, original_amount=15.0, currency="EUR",
                                   running_balance=0.0, recurring_transaction_id=rd.id))
        db_session.commit()
        recalculate_running_balances(db_session, account_id)
        db_session.commit()
        data = _projection(client, account_id)
    netflix = [e for e in data["events"] if e["name"] == "Netflix"]
    assert [e["type"] for e in netflix] == ["scheduled"]
    assert data["projected_balance"] == 1385.0


def test_manual_entry_close_to_a_recurrence_is_flagged_as_possible_duplicate(client, db_session, account_id):
    with freeze_time(NOW):
        _netflix(db_session, account_id)
        _tx(client, account_id, 16, "Sortie", 15.0, "Netflix")
        data = _projection(client, account_id)
    netflix = [e for e in data["events"] if e["name"] == "Netflix"]
    assert sorted(e["type"] for e in netflix) == ["recurring", "scheduled"]
    assert all(e["possible_duplicate"] for e in netflix)


def test_unrelated_entries_are_not_flagged(client, db_session, account_id):
    with freeze_time(NOW):
        _netflix(db_session, account_id)
        _tx(client, account_id, 16, "Sortie", 90.0, "Garagiste")
        data = _projection(client, account_id)
    assert not any(e["possible_duplicate"] for e in data["events"])


def test_global_view_includes_scheduled_entries(client, account_id):
    with freeze_time(NOW):
        _tx(client, account_id, 20, "Sortie", 200.0, "Loyer")
        data = _projection(client)
    assert data["projected_balance"] == 1200.0
    assert any(e["type"] == "scheduled" for e in data["events"])


def test_calendar_marks_future_real_transactions_as_upcoming(client, account_id):
    with freeze_time(NOW):
        _tx(client, account_id, 20, "Sortie", 200.0, "Loyer")
        events = client.get("/analytics/calendar", params={"month": 3, "year": 2026, "account_id": account_id}).json()["events"]
    flags = {e["name"]: e["is_upcoming"] for e in events if not e["is_projected"]}
    assert flags["Loyer"] is True
    assert flags["Courses"] is False


def test_flag_possible_duplicates_is_pure():
    events = [
        ProjectionEvent(date="2026-03-15T00:00:00", name="Netflix", amount=15.0, type="recurring", is_income=False),
        ProjectionEvent(date="2026-03-17T00:00:00", name="netflix", amount=15.0, type="scheduled", is_income=False),
        ProjectionEvent(date="2026-03-17T00:00:00", name="Autre", amount=15.0, type="scheduled", is_income=True),
        ProjectionEvent(date="2026-04-30T00:00:00", name="Loin", amount=15.0, type="scheduled", is_income=False),
    ]
    flag_possible_duplicates(events)
    assert [e.possible_duplicate for e in events] == [True, True, False, False]
