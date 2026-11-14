"""Lectures de l'enveloppe fiscale : comptes par enveloppe, versements, point zéro."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.investment_transaction import InvestmentTransaction


def contributions(db: Session, account_id: int, tx_type: str, year: int | None = None) -> list[InvestmentTransaction]:
    """Opérations d'un type sur le compte, de l'année donnée seulement si `year` est fourni."""
    query = db.query(InvestmentTransaction).filter(
        InvestmentTransaction.account_id == account_id, InvestmentTransaction.type == tx_type
    )
    if year is not None:
        query = query.filter(
            InvestmentTransaction.date >= datetime(year, 1, 1), InvestmentTransaction.date < datetime(year + 1, 1, 1)
        )
    return query.all()


def has_zero_point_snapshot(db: Session, account_id: int) -> bool:
    return (
        db.query(BalanceSnapshot.id)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.is_zero_point.is_(True))
        .first()
        is not None
    )


def wrapped_accounts(db: Session) -> list[Account]:
    """Comptes actifs rattachés à une enveloppe fiscale."""
    return (
        db.query(Account)
        .filter(Account.tax_wrapper.isnot(None), Account.active.is_(True))
        .order_by(Account.id.asc())
        .all()
    )


def unwrapped_accounts(db: Session) -> list[Account]:
    """Comptes actifs sans enveloppe fiscale (candidats à une suggestion)."""
    return db.query(Account).filter(Account.tax_wrapper.is_(None), Account.active.is_(True)).order_by(Account.id).all()


def cto_accounts(db: Session) -> list[Account]:
    return db.query(Account).filter(Account.tax_wrapper == "cto").order_by(Account.id.asc()).all()
