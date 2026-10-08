import asyncio
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.recurring import generate_recurring_transactions
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction


def accounts(db: Session, dest_type="epargne", dest_currency="EUR"):
    a = Account(name="Principal", type="courant", currency="EUR", active=True)
    b = Account(name="Destination", type=dest_type, currency=dest_currency, active=True)
    db.add_all([a, b])
    db.commit()
    return a, b


def recurring(db, src, dest_id, **kw):
    r = RecurringTransaction(
        account_id=src.id, name="Épargne mensuelle", type="Sortie", amount=500.0, currency="EUR",
        frequency="monthly", day_of_month=5, start_date=datetime.now() - timedelta(days=75),
        is_active=True, auto_generate=True, transfer_to_account_id=dest_id, **kw,
    )
    db.add(r)
    db.commit()
    return r


def test_transfer_recurrence_creates_both_legs_linked(db_session: Session):
    main, livret = accounts(db_session)
    rd = recurring(db_session, main, livret.id)

    assert asyncio.run(generate_recurring_transactions(db_session)) >= 2

    sorties = db_session.query(Transaction).filter_by(account_id=main.id, type="Sortie").all()
    entrees = db_session.query(Transaction).filter_by(account_id=livret.id, type="Entree").all()
    assert len(sorties) == len(entrees) >= 2
    for s in sorties:
        e = db_session.get(Transaction, s.linked_transaction_id)
        assert e.account_id == livret.id and e.linked_transaction_id == s.id
        assert s.is_transfer and e.is_transfer
        assert s.link_origin == e.link_origin == "recurring"
        assert e.amount == 500.0 and e.recurring_transaction_id == rd.id
    # soldes recalculés des deux côtés
    assert max(e.running_balance for e in entrees) == 500.0 * len(entrees)

    before = db_session.query(Transaction).count()
    asyncio.run(generate_recurring_transactions(db_session))
    assert db_session.query(Transaction).count() == before  # idempotent


def test_transfer_recurrence_to_investment_account_creates_versement(db_session: Session):
    main, broker = accounts(db_session, dest_type="investissement")
    recurring(db_session, main, broker.id)
    asyncio.run(generate_recurring_transactions(db_session))

    versements = db_session.query(InvestmentTransaction).filter_by(account_id=broker.id, type="versement").all()
    assert versements
    for v in versements:
        s = db_session.get(Transaction, v.linked_transaction_id)
        assert s.linked_investment_transaction_id == v.id and v.link_origin == "recurring"


def test_transfer_recurrence_validation(client, db_session: Session):
    main, livret = accounts(db_session)
    base = {"account_id": main.id, "name": "x", "type": "Sortie", "amount": 10, "frequency": "monthly",
            "day_of_month": 1, "start_date": "2026-01-01T00:00:00"}
    assert client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": livret.id}).status_code == 200
    assert client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": main.id}).status_code == 422
    assert client.post("/recurring-transactions/", json={**base, "type": "Entree", "transfer_to_account_id": livret.id}).status_code == 422
    assert client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": 999}).status_code == 404
