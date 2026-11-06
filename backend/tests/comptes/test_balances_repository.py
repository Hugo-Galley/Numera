"""Lectures de dernière valeur connue : bornes exclusives, ordre date puis id, version par lot identique à l'unitaire."""
from datetime import datetime

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.transaction import Transaction
from app.repositories.comptes import balances


def _tx(account_id, when, balance):
    return Transaction(
        account_id=account_id, date=when, month_label=when.strftime("%Y-%m"), type="Entree", merchant="M",
        amount=1.0, original_amount=1.0, currency="EUR", running_balance=balance,
    )


def _setup(db):
    a = Account(name="A", type="courant", currency="EUR", active=True)
    b = Account(name="B", type="epargne", currency="EUR", active=False)
    db.add_all([a, b])
    db.flush()
    db.add_all([
        _tx(a.id, datetime(2026, 1, 1), 10.0), _tx(a.id, datetime(2026, 2, 1), 20.0), _tx(a.id, datetime(2026, 2, 1), 25.0),
        _tx(b.id, datetime(2026, 3, 1), 99.0),
        BalanceSnapshot(account_id=a.id, date=datetime(2026, 1, 15), current_value=111.0),
        BalanceSnapshot(account_id=a.id, date=datetime(2026, 3, 1), current_value=222.0),
    ])
    db.commit()
    return a, b


def test_before_bound_is_exclusive(db_session):
    a, _ = _setup(db_session)

    assert balances.latest_transaction(db_session, a.id, before=datetime(2026, 2, 1)).running_balance == 10.0
    assert balances.latest_transaction(db_session, a.id, before=datetime(2026, 2, 1, 0, 0, 1)).running_balance == 25.0
    assert balances.latest_snapshot(db_session, a.id, before=datetime(2026, 3, 1)).current_value == 111.0
    assert balances.latest_snapshot(db_session, a.id).current_value == 222.0


def test_batch_versions_match_single_lookups(db_session):
    a, b = _setup(db_session)
    before = datetime(2026, 3, 1)

    txs = balances.latest_balances_by_account(db_session, [a.id, b.id], before)
    snaps = balances.latest_snapshots_by_account(db_session, [a.id, b.id], before)

    assert set(txs) == {a.id} and txs[a.id].running_balance == 25.0  # b : sa seule transaction est à la borne (exclue)
    assert set(snaps) == {a.id} and snaps[a.id].current_value == 111.0
    assert balances.latest_balances_by_account(db_session, [a.id, b.id])[b.id].running_balance == 99.0
    assert balances.latest_balances_by_account(db_session, []) == {}


def test_batch_versions_use_one_query_each(db_session, measure_queries):
    a, b = _setup(db_session)
    ids = [a.id, b.id]  # lus avant la mesure : l'objet expiré par le commit se recharge

    _, queries = measure_queries(lambda: (
        balances.latest_balances_by_account(db_session, ids),
        balances.latest_snapshots_by_account(db_session, ids),
    ))

    assert queries == 2


def test_active_accounts_excludes_archived_and_orders(db_session):
    a, _ = _setup(db_session)

    assert [x.id for x in balances.active_accounts(db_session)] == [a.id]
