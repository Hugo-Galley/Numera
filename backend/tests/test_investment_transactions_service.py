"""Service des opérations d'investissement : erreurs métier levées sans passer par HTTP."""
import asyncio
from datetime import datetime

import pytest

from app.core.errors import BusinessRuleError, ConflictError
from app.models.account import Account
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.schemas.investment import InvestmentTransactionCreate
from app.services import investment_transactions as service

BASELINE = datetime(2026, 1, 10, 12, 0)


@pytest.fixture()
def pea(db_session) -> Account:
    account = Account(name="PEA", type="investissement", currency="EUR", holdings_baseline_date=BASELINE)
    db_session.add(account)
    db_session.flush()
    db_session.add(HoldingBaselineItem(account_id=account.id, baseline_date=BASELINE, ticker="CW8.PA",
                                       asset_name="MSCI World", quantity=5, buy_price_avg=400.0, currency="EUR"))
    db_session.commit()
    return account


def _create(db, account_id: int, **fields):
    payload = InvestmentTransactionCreate(account_id=account_id, date=fields.pop("date", datetime(2026, 2, 1)), **fields)
    return asyncio.run(service.create_transaction(db, payload))


def test_trade_before_baseline_is_rejected(db_session, pea):
    with pytest.raises(BusinessRuleError) as exc:
        _create(db_session, pea.id, type="achat", amount=800.0, ticker="CW8.PA", quantity=2, date=datetime(2026, 1, 5))
    assert exc.value.detail.startswith("Opération sur CW8.PA antérieure au Point Zéro")


def test_dividend_requires_ticker(db_session, pea):
    with pytest.raises(BusinessRuleError, match="rattaché à un titre"):
        _create(db_session, pea.id, type="dividende", amount=10.0)


def test_reinvested_purchase_cannot_be_deleted(db_session, pea):
    dividend = _create(db_session, pea.id, type="dividende", amount=20.0, ticker="CW8.PA", quantity=0.05, reinvested=True)
    purchase = db_session.query(InvestmentTransaction).filter_by(reinvest_of_id=dividend.id).one()
    with pytest.raises(ConflictError):
        asyncio.run(service.delete_transaction(db_session, purchase.id))
    assert db_session.get(InvestmentTransaction, purchase.id) is not None
