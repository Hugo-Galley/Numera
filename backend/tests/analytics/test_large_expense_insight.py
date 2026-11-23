"""Insight « Grosse dépense isolée » : ni les charges récurrentes, ni un seuil effondré en début de mois."""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction


def _account(db: Session) -> Account:
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db.add(acc)
    db.commit()
    return acc


def _tx(db: Session, acc: Account, day: datetime, tx_type: str, merchant: str, amount: float, **extra: object) -> Transaction:
    tx = Transaction(account_id=acc.id, date=day, month_label="x", type=tx_type, merchant=merchant, amount=amount,
                     original_amount=amount, currency="EUR", running_balance=0.0, **extra)
    db.add(tx)
    return tx


def _large_expenses(client: TestClient, month: int, year: int) -> list[dict]:
    data = client.get("/analytics/insights", params={"month": month, "year": year}).json()
    return [i for i in data["insights"] if i["key"].startswith("large-expense-")]


def test_rent_linked_to_a_recurrence_is_not_a_large_expense(client: TestClient, db_session: Session):
    acc = _account(db_session)
    rent = RecurringTransaction(account_id=acc.id, name="Loyer", type="Sortie", amount=890.0, frequency="monthly",
                                day_of_month=2, start_date=datetime(2026, 1, 1), is_active=True)
    db_session.add(rent)
    db_session.commit()
    _tx(db_session, acc, datetime(2026, 5, 1), "Entree", "Salaire", 2000.0)
    _tx(db_session, acc, datetime(2026, 5, 2), "Sortie", "Foncia — Loyer", 890.0,
        is_recurring=True, recurring_transaction_id=rent.id)
    db_session.commit()

    assert _large_expenses(client, 5, 2026) == []


def test_expense_repeated_every_month_is_not_a_large_expense(client: TestClient, db_session: Session):
    """Même marchand, montant proche, dans les mois précédents : charge habituelle, même sans récurrence saisie."""
    acc = _account(db_session)
    for month in (2, 3, 4, 5):
        _tx(db_session, acc, datetime(2026, month, 1), "Entree", "Salaire", 2000.0)
        _tx(db_session, acc, datetime(2026, month, 3), "Sortie", "Foncia — Loyer", 890.0 + month)
    db_session.commit()

    assert _large_expenses(client, 5, 2026) == []


def test_one_off_expense_is_still_a_large_expense(client: TestClient, db_session: Session):
    acc = _account(db_session)
    _tx(db_session, acc, datetime(2026, 5, 1), "Entree", "Salaire", 2000.0)
    _tx(db_session, acc, datetime(2026, 5, 14), "Sortie", "Apple Store", 1499.0)
    db_session.commit()

    keys = [i["description"] for i in _large_expenses(client, 5, 2026)]
    assert len(keys) == 1 and "Apple Store" in keys[0]


def test_threshold_uses_recent_average_income_when_month_has_no_income_yet(client: TestClient, db_session: Session):
    """Mois en cours avant le salaire : le seuil suit le revenu moyen des 3 mois précédents (6 000 € → 600 €)."""
    acc = _account(db_session)
    for month in (2, 3, 4):
        _tx(db_session, acc, datetime(2026, month, 1), "Entree", "Salaire", 6000.0)
    _tx(db_session, acc, datetime(2026, 5, 10), "Sortie", "Darty", 550.0)
    db_session.commit()

    assert _large_expenses(client, 5, 2026) == []
