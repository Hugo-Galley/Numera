"""Positions (`portfolio_holdings`) et inventaire Point Zéro (`holding_baseline_items`)."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.holdings import TRADE_TYPES
from app.models.account import Account
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding


def account(db: Session, account_id: int) -> Account | None:
    return db.get(Account, account_id)


def baseline_items(db: Session, account_id: int, order_by_id: bool = False) -> list[HoldingBaselineItem]:
    query = db.query(HoldingBaselineItem).filter(HoldingBaselineItem.account_id == account_id)
    if order_by_id:
        query = query.order_by(HoldingBaselineItem.id)
    return query.all()


def baseline_item(db: Session, account_id: int, ticker: str) -> HoldingBaselineItem | None:
    return (
        db.query(HoldingBaselineItem)
        .filter(HoldingBaselineItem.account_id == account_id, HoldingBaselineItem.ticker == ticker)
        .first()
    )


def holdings_by_ticker(db: Session, account_id: int) -> dict[str, PortfolioHolding]:
    return {h.ticker: h for h in db.query(PortfolioHolding).filter(PortfolioHolding.account_id == account_id).all()}


def add_holding(db: Session, holding: PortfolioHolding) -> None:
    db.add(holding)


def delete_holding(db: Session, holding: PortfolioHolding) -> None:
    db.delete(holding)


def list_all(db: Session, account_id: int | None = None) -> list[PortfolioHolding]:
    """Positions (d'un compte ou de tous), par id."""
    query = db.query(PortfolioHolding)
    if account_id is not None:
        query = query.filter(PortfolioHolding.account_id == account_id)
    return query.order_by(PortfolioHolding.id.asc()).all()


def get(db: Session, holding_id: int) -> PortfolioHolding | None:
    return db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()


def holding(db: Session, account_id: int, ticker: str) -> PortfolioHolding | None:
    return db.query(PortfolioHolding).filter(
        PortfolioHolding.account_id == account_id, PortfolioHolding.ticker == ticker
    ).first()


def delete_baseline(db: Session, account_id: int, ticker: str | None = None) -> None:
    """Supprime l'inventaire Point Zéro du compte (ou la seule ligne de `ticker`)."""
    query = db.query(HoldingBaselineItem).filter(HoldingBaselineItem.account_id == account_id)
    if ticker is not None:
        query = query.filter(HoldingBaselineItem.ticker == ticker)
    query.delete()


def add_baseline_items(db: Session, items: list[HoldingBaselineItem]) -> None:
    db.add_all(items)


def later_trade_exists(db: Session, account_id: int, ticker: str, cutoff: datetime | None) -> bool:
    """Vrai s'il reste une opération sur titre postérieure à `cutoff` (toutes si pas de Point Zéro)."""
    return db.query(InvestmentTransaction.id).filter(
        InvestmentTransaction.account_id == account_id,
        InvestmentTransaction.ticker == ticker,
        InvestmentTransaction.quantity > 0,
        InvestmentTransaction.type.in_(TRADE_TYPES),
        *([InvestmentTransaction.date > cutoff] if cutoff else []),
    ).first() is not None
