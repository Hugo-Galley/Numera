"""Coût des abonnements : une seule définition, sans virement interne ni alimentation d'épargne."""
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time import now_local
from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction


def _accounts(db: Session) -> tuple[Account, Account]:
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    livret = Account(name="Livret A", type="epargne", currency="EUR", active=True)
    db.add_all([courant, livret])
    db.commit()
    return courant, livret


def _recurring(db: Session, acc: Account, name: str, amount: float, **extra: object) -> RecurringTransaction:
    rec = RecurringTransaction(account_id=acc.id, name=name, type="Sortie", amount=amount, frequency="monthly",
                               day_of_month=3, start_date=now_local() - timedelta(days=60), is_active=True, **extra)
    db.add(rec)
    return rec


def _out(db: Session, acc: Account, days_ago: int, merchant: str, amount: float, **extra: object) -> None:
    db.add(Transaction(account_id=acc.id, date=now_local() - timedelta(days=days_ago), month_label="x", type="Sortie",
                       merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
                       **extra))


def test_total_monthly_is_the_confirmed_subscriptions_total(client: TestClient, db_session: Session):
    """Tableau de bord et Échéances lisent le même chiffre : les abonnements détectés n'y entrent pas."""
    courant, _ = _accounts(db_session)
    _recurring(db_session, courant, "Netflix", 15.99)
    for days_ago in (10, 40):
        _out(db_session, courant, days_ago, "Spotify", 9.99)
    db_session.commit()

    data = client.get("/analytics/subscriptions").json()

    assert any(s["name"] == "Spotify" and s["status"] == "potential" for s in data["subscriptions"])
    assert data["total_monthly"] == data["totals_by_kind"]["subscriptions"]["monthly"] == 15.99
    assert data["total_annual"] == data["totals_by_kind"]["subscriptions"]["annual"]


def test_internal_transfers_are_never_detected_as_subscriptions(client: TestClient, db_session: Session):
    courant, _ = _accounts(db_session)
    for days_ago in (10, 40):
        _out(db_session, courant, days_ago, "Virement PEA", 300.0, is_transfer=True)
    db_session.commit()

    data = client.get("/analytics/subscriptions").json()

    assert all(s["name"] != "Virement PEA" for s in data["subscriptions"])


def test_recurring_transfer_to_savings_is_not_a_subscription(client: TestClient, db_session: Session):
    """« Virement Livret A » : alimentation d'épargne (onglet investissements), jamais une charge."""
    courant, livret = _accounts(db_session)
    _recurring(db_session, courant, "Virement Livret A", 200.0, transfer_to_account_id=livret.id)
    _recurring(db_session, courant, "Netflix", 15.99)
    db_session.commit()

    data = client.get("/analytics/subscriptions").json()
    transfer = next(s for s in data["subscriptions"] if s["name"] == "Virement Livret A")

    assert transfer["kind"] == "investments"
    assert data["totals_by_kind"]["subscriptions"]["monthly"] == 15.99
    reste = client.get("/analytics/reste-a-vivre").json()
    assert reste["charges_essentielles"] + reste["charges_non_essentielles"] == 15.99
