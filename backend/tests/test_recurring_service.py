"""Récurrences : génération idempotente, occurrences et règles pures, erreurs du service."""
import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.errors import BusinessRuleError, NotFoundError
from app.domain.finance import get_recurring_occurrences
from app.domain.recurring import investment_leg_type
from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.schemas.recurring_transaction import RecurringTransactionCreate
from app.services import recurring_transactions as service
from app.services.recurring import generate_recurring_transactions


def _rule(**overrides):
    data = dict(start_date=datetime(2026, 1, 10), end_date=None, frequency="monthly", day_of_month=None,
                excluded_months=None)
    data.update(overrides)
    return SimpleNamespace(**data)


def test_occurrences_respect_end_date_and_excluded_months():
    rule = _rule(end_date=datetime(2026, 5, 1), excluded_months="3")
    dates = get_recurring_occurrences(rule, datetime(2026, 1, 1), datetime(2026, 12, 31))
    assert dates == [datetime(2026, 1, 10), datetime(2026, 2, 10), datetime(2026, 4, 10)]


def test_monthly_first_occurrence_waits_for_day_of_month():
    rule = _rule(start_date=datetime(2026, 1, 20), day_of_month=16)
    assert get_recurring_occurrences(rule, datetime(2026, 1, 1), datetime(2026, 3, 1)) == [datetime(2026, 2, 16)]


def test_quarterly_and_unknown_frequency():
    quarterly = _rule(frequency="quarterly")
    assert get_recurring_occurrences(quarterly, datetime(2026, 1, 1), datetime(2026, 8, 1)) == [
        datetime(2026, 1, 10), datetime(2026, 4, 10), datetime(2026, 7, 10)]
    assert get_recurring_occurrences(_rule(frequency="hourly"), datetime(2026, 1, 1), datetime(2026, 3, 1)) == [
        datetime(2026, 1, 10)]


def test_investment_leg_type_rules():
    assert investment_leg_type("Achat", "investissement", True, False) == (True, "versement")
    assert investment_leg_type("Sortie", "courant", True, False) == (True, "versement")
    assert investment_leg_type("Sortie", "courant", True, True) == (False, "versement")
    assert investment_leg_type("Entree", "assurance_vie", False, False) == (True, "versement")
    assert investment_leg_type("Sortie", "courant", False, False) == (False, "versement")


def test_generation_is_idempotent(db_session):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    db_session.add(RecurringTransaction(
        account_id=account.id, name="Netflix", type="Sortie", amount=13.49, currency="EUR", frequency="monthly",
        start_date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=70),
        is_active=True, auto_generate=True))
    db_session.commit()

    first = asyncio.run(generate_recurring_transactions(db_session))
    assert first >= 2
    assert asyncio.run(generate_recurring_transactions(db_session)) == 0
    assert db_session.query(Transaction).count() == first


def test_transfer_to_same_account_is_rejected(db_session):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    payload = RecurringTransactionCreate(account_id=account.id, name="Épargne", type="Sortie", amount=100.0,
                                         frequency="monthly", start_date=datetime(2026, 1, 1),
                                         transfer_to_account_id=account.id)
    with pytest.raises(BusinessRuleError, match="Source and destination accounts must differ"):
        asyncio.run(service.create_recurring_transaction(db_session, payload))


def test_unknown_recurrence_is_not_found(db_session):
    with pytest.raises(NotFoundError, match="Recurring transaction not found"):
        service.delete_recurring_transaction(db_session, 1)
