"""Service de l'inventaire Point Zéro et rendement d'une position (erreurs métier, calcul pur)."""
import asyncio
from datetime import datetime

import pytest

from app.core.errors import BusinessRuleError, ConflictError
from app.domain.holdings import holding_returns
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.schemas.holding import PortfolioHoldingUpdate
from app.services.holdings import inventory


def test_holding_returns_include_dividends():
    figures = holding_returns(1.0, 120.0, 100.0, None, None, 5.0)
    assert (figures["gain_eur"], figures["gain_pct"]) == (20.0, 20.0)
    assert (figures["total_return_eur"], figures["total_return_pct"]) == (25.0, 25.0)


def test_holding_returns_falls_back_to_pru_at_current_rate():
    figures = holding_returns(10.0, 0.0, None, 100.0, 2.0, 0.0)
    assert figures["invested_eur"] == 500.0
    assert figures["gain_eur"] is None  # sans cours, pas de plus-value


@pytest.fixture()
def traded_holding(db_session) -> PortfolioHolding:
    account = Account(name="CTO", type="investissement", currency="EUR")
    db_session.add(account)
    db_session.flush()
    db_session.add(InvestmentTransaction(account_id=account.id, date=datetime(2026, 2, 1), type="achat", amount=200.0,
                                         currency="EUR", original_amount=200.0, ticker="CW8.PA", quantity=2, unit_price=100.0))
    holding = PortfolioHolding(account_id=account.id, ticker="CW8.PA", asset_name="MSCI World", quantity=2, currency="EUR")
    db_session.add(holding)
    db_session.commit()
    return holding


def test_update_quantity_without_baseline_is_rejected(db_session, traded_holding):
    with pytest.raises(BusinessRuleError, match="provient uniquement d'opérations"):
        asyncio.run(inventory.update_holding(db_session, traded_holding.id, PortfolioHoldingUpdate(quantity=3)))


def test_delete_holding_with_later_trade_conflicts(db_session, traded_holding):
    with pytest.raises(ConflictError):
        asyncio.run(inventory.delete_holding(db_session, traded_holding.id))
