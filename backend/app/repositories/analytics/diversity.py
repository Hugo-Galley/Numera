"""Lectures du scanner de diversification : positions et dernière valeur connue des comptes actifs."""

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.portfolio_holding import PortfolioHolding
from app.repositories.comptes.balances import own_account


def holdings(db: Session, account_id: int | None) -> list[PortfolioHolding]:
    """Positions d'un compte, ou de tous les comptes à soi."""
    query = db.query(PortfolioHolding)
    if account_id is not None:
        query = query.filter(PortfolioHolding.account_id == account_id)
    else:
        query = query.join(Account, PortfolioHolding.account_id == Account.id).filter(own_account())
    return query.all()
