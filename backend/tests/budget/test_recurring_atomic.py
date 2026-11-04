"""Génération récurrente : positions et soldes recalculés avant le commit d'une règle."""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.services.budget import recurring
from app.services.budget.recurring import generate_recurring_transactions


def _rule(db, account, name):
    db.add(RecurringTransaction(
        account_id=account.id, name=name, type="Sortie", amount=10.0, currency="EUR", frequency="monthly",
        start_date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=40),
        is_active=True, auto_generate=True))


def test_error_during_recalculation_leaves_no_committed_transaction(db_session, monkeypatch):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    _rule(db_session, account, "Netflix")
    db_session.commit()

    def boom(*_a, **_k):
        raise RuntimeError("recalcul impossible")

    monkeypatch.setattr(recurring, "recalculate_running_balances", boom)
    asyncio.run(generate_recurring_transactions(db_session))

    fresh = sessionmaker(bind=db_session.get_bind())()
    assert fresh.query(Transaction).count() == 0
    assert fresh.query(RecurringTransaction).one().last_generated_date is None


def test_failing_rule_does_not_block_the_others(db_session, monkeypatch):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    _rule(db_session, account, "Mauvaise")
    _rule(db_session, account, "Bonne")
    db_session.commit()

    real = recurring._generate_rule

    async def flaky(db, rd, now, run):
        if rd.name == "Mauvaise":
            raise RuntimeError("règle cassée")
        await real(db, rd, now, run)

    monkeypatch.setattr(recurring, "_generate_rule", flaky)
    assert asyncio.run(generate_recurring_transactions(db_session)) >= 1

    names = {t.merchant for t in sessionmaker(bind=db_session.get_bind())().query(Transaction)}
    assert names == {"Bonne"}
