"""Lectures du scanner de diversification : positions et dernière valeur connue des comptes actifs."""

from sqlalchemy.orm import Session

from app.models.portfolio_holding import PortfolioHolding


def holdings(db: Session, account_id: int | None) -> list[PortfolioHolding]:
    query = db.query(PortfolioHolding)
    if account_id is not None:
        query = query.filter(PortfolioHolding.account_id == account_id)
    return query.all()
