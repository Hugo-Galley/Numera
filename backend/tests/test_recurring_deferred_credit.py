"""Virements récurrents à arrivée différée : débit le 29, crédit sur le PEA le 16 suivant."""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.services.recurring import generate_recurring_transactions, transfer_credit_date
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from tests.test_recurring_transfers import accounts, fake_market


def test_transfer_credit_date():
    assert transfer_credit_date(datetime(2026, 10, 29), None) == datetime(2026, 10, 29)
    assert transfer_credit_date(datetime(2026, 10, 29), 16) == datetime(2026, 11, 16)
    assert transfer_credit_date(datetime(2026, 10, 5), 16) == datetime(2026, 10, 16)
    assert transfer_credit_date(datetime(2026, 10, 16), 16) == datetime(2026, 10, 16)
    assert transfer_credit_date(datetime(2026, 12, 29), 16) == datetime(2027, 1, 16)
    assert transfer_credit_date(datetime(2026, 1, 31), 30) == datetime(2026, 2, 28)


def deferred_rule(db: Session, src: Account, dest: Account, **kw) -> RecurringTransaction:
    rd = RecurringTransaction(
        account_id=src.id, name="Alimentation PEA", type="Sortie", amount=400.0, currency="EUR",
        frequency="monthly", day_of_month=29, start_date=datetime.now() - timedelta(days=120),
        is_active=True, auto_generate=True, transfer_to_account_id=dest.id, transfer_credit_day=16, **kw,
    )
    db.add(rd)
    db.commit()
    return rd


def test_deferred_transfer_credits_on_arrival_day(db_session: Session, monkeypatch):
    fake_market(monkeypatch)
    main, pea = accounts(db_session, dest_type="investissement")
    rd = deferred_rule(db_session, main, pea, ticker="CW8.PA")

    asyncio.run(generate_recurring_transactions(db_session))
    now = datetime.now()

    sorties = db_session.query(Transaction).filter_by(account_id=main.id, type="Sortie").all()
    assert len(sorties) >= 3
    credited = 0
    for s in sorties:
        assert s.date.day == 29 or s.date.month == 2  # débit le 29 (fin février sinon)
        arrival = transfer_credit_date(s.date, 16)
        if arrival <= now:
            v = db_session.get(InvestmentTransaction, s.linked_investment_transaction_id)
            assert v.account_id == pea.id and v.date == arrival and v.amount == 400.0
            assert v.unit_price == 100.0 + 16  # achat au cours du jour d'arrivée
            assert v.recurring_transaction_id == rd.id and v.link_origin == "recurring"
            credited += 1
        else:
            assert s.linked_investment_transaction_id is None and not s.is_transfer  # en transit
            assert s.transfer_credit_due == arrival
    assert credited == db_session.query(InvestmentTransaction).filter_by(account_id=pea.id).count() >= 2

    before = db_session.query(InvestmentTransaction).count()
    asyncio.run(generate_recurring_transactions(db_session))
    assert db_session.query(InvestmentTransaction).count() == before  # idempotent


def test_deferred_transfer_credits_later_once_arrival_day_passes(db_session: Session):
    main, livret = accounts(db_session)
    rd = deferred_rule(db_session, main, livret)
    # Sortie générée avant son jour d'arrivée : rien n'est encore crédité
    debit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=40)
    s = Transaction(
        account_id=main.id, date=debit, month_label="x", type="Sortie", merchant=rd.name, amount=400.0,
        currency="EUR", original_amount=400.0, running_balance=0.0, is_recurring=True, recurring_transaction_id=rd.id,
        transfer_credit_due=transfer_credit_date(debit, 16),
    )
    rd.last_generated_date = datetime.now()
    rd.start_date = datetime.now()
    db_session.add(s)
    db_session.commit()

    asyncio.run(generate_recurring_transactions(db_session))

    db_session.refresh(s)
    e = db_session.get(Transaction, s.linked_transaction_id)
    assert e.account_id == livret.id and e.date == transfer_credit_date(debit, 16)
    assert e.running_balance == 400.0
    assert s.transfer_credit_due is None


def test_deleted_deferred_credit_is_not_created_again(db_session: Session):
    from app.services.transfers import release_partner

    main, livret = accounts(db_session)
    deferred_rule(db_session, main, livret)
    asyncio.run(generate_recurring_transactions(db_session))
    s = db_session.query(Transaction).filter(
        Transaction.account_id == main.id, Transaction.linked_transaction_id.isnot(None)
    ).first()
    entree = db_session.get(Transaction, s.linked_transaction_id)
    release_partner(db_session, entree)
    db_session.delete(entree)
    db_session.commit()

    asyncio.run(generate_recurring_transactions(db_session))
    db_session.refresh(s)
    assert s.linked_transaction_id is None


def test_deferred_credit_skipped_when_linked_meanwhile(db_session: Session):
    from app.services.transfers import link_pair

    main, livret = accounts(db_session)
    rd = deferred_rule(db_session, main, livret)
    rd.start_date = rd.last_generated_date = datetime.now()
    debit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=40)
    common = dict(month_label="x", amount=400.0, currency="EUR", original_amount=400.0, running_balance=0.0)
    s = Transaction(account_id=main.id, date=debit, type="Sortie", merchant=rd.name, recurring_transaction_id=rd.id,
                    transfer_credit_due=transfer_credit_date(debit, 16), **common)
    imported = Transaction(account_id=livret.id, date=debit + timedelta(days=17), type="Entree", merchant="VIR", **common)
    db_session.add_all([s, imported])
    db_session.flush()
    link_pair(db_session, s, imported, "regular", "manual")
    db_session.commit()

    asyncio.run(generate_recurring_transactions(db_session))
    db_session.refresh(s)
    assert s.transfer_credit_due is None and s.linked_transaction_id == imported.id
    assert db_session.query(Transaction).filter_by(account_id=livret.id).count() == 1


def test_credit_day_requires_transfer_destination(client, db_session: Session):
    main, livret = accounts(db_session)
    base = {"account_id": main.id, "name": "x", "type": "Sortie", "amount": 10, "frequency": "monthly",
            "day_of_month": 29, "start_date": "2026-01-01T00:00:00"}
    assert client.post("/recurring-transactions/", json={**base, "transfer_credit_day": 16}).status_code == 422
    assert client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": livret.id, "transfer_credit_day": 32}).status_code == 422
    r = client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": livret.id, "transfer_credit_day": 16})
    assert r.status_code == 200 and r.json()["transfer_credit_day"] == 16
