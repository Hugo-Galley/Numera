"""Lectures du scanner de diversification : positions et dernière valeur connue des comptes actifs."""
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.portfolio_holding import PortfolioHolding
from app.models.transaction import Transaction


def holdings(db: Session, account_id: int | None) -> list[PortfolioHolding]:
    query = db.query(PortfolioHolding)
    if account_id is not None:
        query = query.filter(PortfolioHolding.account_id == account_id)
    return query.all()


def active_accounts(db: Session) -> list[Account]:
    return db.query(Account).filter(Account.active.is_(True)).all()


def latest_snapshot(db: Session, account_id: int) -> BalanceSnapshot | None:
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )


def last_transaction(db: Session, account_id: int) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .first()
    )
