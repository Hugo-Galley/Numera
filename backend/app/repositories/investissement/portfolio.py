"""Lectures de la valorisation d'un compte titres : relevés du courtier, opérations, transactions bancaires."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.balance_snapshot import BalanceSnapshot
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.transaction import Transaction


def only_transfer_legs(query):
    """Restreint une requête de transactions bancaires aux jambes de virement reconnues."""
    return query.filter(Transaction.is_transfer.is_(True), Transaction.is_transfer_ignored.is_(False))


def investment_transactions(db: Session, account_id: int) -> list[InvestmentTransaction]:
    """Opérations d'investissement du compte, par date puis id."""
    query = db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account_id)
    return query.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).all()


def regular_transactions(db: Session, account_id: int, transfers_only: bool) -> list[Transaction]:
    """Transactions bancaires du compte (catégorie jointe), par date puis id ; jambes de virement seules si demandé."""
    regular = (
        db.query(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.account_id == account_id)
    )
    if transfers_only:
        regular = only_transfer_legs(regular)
    return regular.order_by(Transaction.date.asc(), Transaction.id.asc()).all()


def latest_zero_point(db: Session, account_id: int) -> BalanceSnapshot | None:
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.is_zero_point.is_(True))
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )


def latest_snapshot_until(db: Session, account_id: int, until: datetime) -> BalanceSnapshot | None:
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.date <= until)
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )


def latest_snapshot(db: Session, account_id: int) -> BalanceSnapshot | None:
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )


def snapshots_before(db: Session, account_id: int, day: datetime) -> list[BalanceSnapshot]:
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.date < day)
        .order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc())
        .all()
    )


def snapshots_since(db: Session, account_id: int, day: datetime) -> list[BalanceSnapshot]:
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.date >= day)
        .order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc())
        .all()
    )


def holdings_meta(db: Session, account_id: int) -> dict[str, PortfolioHolding]:
    return {h.ticker: h for h in db.query(PortfolioHolding).filter(PortfolioHolding.account_id == account_id).all()}
