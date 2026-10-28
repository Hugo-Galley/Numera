"""Service des comptes : solde affiché, erreurs métier, règles de mise à jour (sans passer par HTTP)."""
from datetime import datetime

import pytest

from app.core.errors import NotFoundError
from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.transaction import Transaction
from app.schemas.account import AccountUpdate
from app.services import accounts as service


def _account(db, name="Principal", is_main=False):
    acc = Account(name=name, type="courant", currency="EUR", active=True, is_main=is_main)
    db.add(acc)
    db.commit()
    return acc


def _tx(db, account, running_balance, date):
    db.add(Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type="Entree",
        merchant="x", amount=10.0, original_amount=10.0, currency="EUR", running_balance=running_balance,
    ))
    db.commit()


def test_account_balance_prefers_snapshot_newer_than_last_transaction(db_session):
    acc = _account(db_session)
    _tx(db_session, acc, 100.0, datetime(2026, 9, 1))
    db_session.add(BalanceSnapshot(account_id=acc.id, date=datetime(2026, 9, 15), current_value=250.0))
    db_session.commit()
    assert service.account_balance(db_session, acc.id) == 250.0


def test_account_balance_falls_back_to_last_running_balance(db_session):
    acc = _account(db_session)
    db_session.add(BalanceSnapshot(account_id=acc.id, date=datetime(2026, 8, 1), current_value=250.0))
    _tx(db_session, acc, 100.0, datetime(2026, 9, 1))
    _tx(db_session, acc, 140.0, datetime(2026, 9, 2))
    assert service.account_balance(db_session, acc.id) == 140.0


def test_account_balance_is_zero_without_history(db_session):
    assert service.account_balance(db_session, _account(db_session).id) == 0.0


def test_get_account_unknown_raises_structured_not_found(db_session):
    with pytest.raises(NotFoundError) as exc:
        service.get_account(db_session, 999)
    assert exc.value.to_content() == {
        "detail": {"code": "account_not_found", "detail": "Account not found", "context": {"account_id": 999}}}


def test_setting_main_account_clears_previous_main(db_session):
    first = _account(db_session, "A", is_main=True)
    second = _account(db_session, "B")
    service.update_account(db_session, second.id, AccountUpdate(is_main=True))
    db_session.refresh(first)
    assert first.is_main is False and second.is_main is True


def test_archive_account_deactivates_without_deleting(db_session):
    acc = _account(db_session)
    service.archive_account(db_session, acc.id)
    db_session.expire_all()
    assert db_session.get(Account, acc.id).active is False
