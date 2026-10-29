"""Positions (`portfolio_holdings`) et inventaire Point Zéro (`holding_baseline_items`)."""
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.holding_baseline_item import HoldingBaselineItem
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
