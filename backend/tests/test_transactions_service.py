"""Service des transactions : lecture et filtres, sans HTTP (et comparé à la route)."""
from datetime import datetime

import pytest

from app.core.errors import NotFoundError
from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.transaction_split import TransactionSplit
from app.repositories.transactions import TransactionFilters
from app.services import transactions as service


def _account(db, name, type_="courant"):
    account = Account(name=name, type=type_, currency="EUR", active=True)
    db.add(account)
    db.flush()
    return account


def _tx(db, account, merchant, date, amount=10.0, type_="Sortie", category_id=None):
    tx = Transaction(account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
                     merchant=merchant, amount=amount, original_amount=amount, currency="EUR",
                     running_balance=0.0, category_id=category_id)
    db.add(tx)
    db.flush()
    return tx


@pytest.fixture()
def data(db_session):
    db = db_session
    courant, tickets = _account(db, "Courant"), _account(db, "Tickets Restaurant")
    courses, maison = Category(name="Courses", type="depense"), Category(name="Maison", type="depense")
    db.add_all([courses, maison])
    db.flush()
    split = _tx(db, courant, "IKEA", datetime(2026, 10, 3), 100.0, category_id=courses.id)
    db.add_all([TransactionSplit(transaction_id=split.id, category_id=courses.id, amount=60.0),
                TransactionSplit(transaction_id=split.id, category_id=maison.id, amount=40.0)])
    _tx(db, courant, "CARREFOUR", datetime(2026, 10, 28), 30.0, category_id=courses.id)
    _tx(db, tickets, "BOULANGERIE", datetime(2026, 10, 5), 8.0)
    _tx(db, courant, "LOYER", datetime(2026, 9, 30), 700.0)
    db.commit()
    return {"courant": courant, "tickets": tickets, "courses": courses, "maison": maison, "split": split}


def test_budget_scope_excludes_ticket_restaurant_accounts(db_session, data):
    result = service.list_transactions(db_session, TransactionFilters(budget_scope=True), skip=0, limit=100)
    assert {tx.merchant for tx in result} == {"IKEA", "CARREFOUR", "LOYER"}


def test_category_filter_includes_split_parts(db_session, data):
    result = service.list_transactions(db_session, TransactionFilters(category_id=data["maison"].id), skip=0, limit=100)
    assert [tx.id for tx in result] == [data["split"].id]


@pytest.mark.parametrize("params", [
    {"budget_scope": "true"},
    {"category_id": "maison"},
    {"month": 10, "year": 2026, "period": "true"},
    {"search": "car", "min_amount": 5},
])
def test_service_matches_http_route(client, db_session, data, params):
    params = {k: (data[v].id if v in data else v) for k, v in params.items()}
    via_http = [row["id"] for row in client.get("/transactions", params=params).json()]
    filters = TransactionFilters(**{
        k: (v == "true" if v in ("true", "false") else v) for k, v in params.items()
    })
    via_service = [tx.id for tx in service.list_transactions(db_session, filters, skip=0, limit=100)]
    assert via_service == via_http and via_http


def test_unknown_transaction_candidates_is_not_found(db_session):
    import asyncio

    with pytest.raises(NotFoundError, match="Transaction not found"):
        asyncio.run(service.transfer_candidates(db_session, 999, days=15, amount_tolerance_pct=5.0, account_id=None))
