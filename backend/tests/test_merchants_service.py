"""Services marchands et règles de catégorisation, sans HTTP."""
from datetime import datetime

import pytest

from app.core.errors import ConflictError, NotFoundError
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.categorization_rule import CategorizationRule
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.merchant import MerchantAliasCreate, MerchantCreate
from app.services import categorization_rules as rule_service
from app.services import merchants as merchant_service


def _tx(db, account, merchant, running_balance=-10.0):
    date = datetime(2026, 10, 1)
    tx = Transaction(account_id=account.id, date=date, month_label=month_label_from_date(date), type="Sortie",
                     merchant=merchant, amount=10.0, original_amount=10.0, currency="EUR",
                     running_balance=running_balance)
    db.add(tx)
    db.commit()
    return tx


def _account(db):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db.add(account)
    db.commit()
    return account


def test_create_merchant_links_existing_transactions(db_session):
    account = _account(db_session)
    first, second = _tx(db_session, account, "CB CARREFOUR 12"), _tx(db_session, account, "CB CARREFOUR 12")
    merchant = merchant_service.create_merchant(
        db_session, MerchantCreate(name="Carrefour", aliases=["CB CARREFOUR 12"]))
    db_session.expire_all()
    for tx in (first, second):
        refreshed = db_session.get(Transaction, tx.id)
        assert refreshed.merchant_id == merchant.id
        assert refreshed.merchant == "CB CARREFOUR 12"  # libellé bancaire intact


def test_duplicate_alias_is_conflict(db_session):
    merchant = merchant_service.create_merchant(db_session, MerchantCreate(name="Lidl", aliases=["LIDL"]))
    with pytest.raises(ConflictError, match="Cet alias existe déjà"):
        merchant_service.add_alias(db_session, merchant.id, MerchantAliasCreate(label="LIDL"))


def test_unknown_merchant_is_not_found(db_session):
    with pytest.raises(NotFoundError, match="Merchant not found"):
        merchant_service.get_merchant(db_session, 1)


def test_apply_rules_categorizes_and_keeps_balances(db_session):
    account = _account(db_session)
    category = Category(name="Courses", type="depense")
    db_session.add(category)
    db_session.commit()
    tx = _tx(db_session, account, "CARREFOUR MARKET", running_balance=-10.0)
    db_session.add(CategorizationRule(pattern="carrefour", category_id=category.id))
    db_session.commit()

    assert rule_service.apply_rules_to_transactions(db_session) == {"modified_count": 1}
    db_session.expire_all()
    refreshed = db_session.get(Transaction, tx.id)
    assert refreshed.category_id == category.id
    assert refreshed.running_balance == -10.0
