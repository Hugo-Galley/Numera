"""Opérations d'investissement (`investment_transactions`)."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.dividends import DIVIDEND_TYPE
from app.domain.holdings import BUY_TYPES, TRADE_TYPES
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction


def for_account(db: Session, account_id: int) -> list[InvestmentTransaction]:
    """Opérations d'un compte, dans l'ordre de la base."""
    return db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account_id).all()


def trades(db: Session, account_id: int, until: datetime | None = None) -> list[InvestmentTransaction]:
    """Opérations qui font bouger une position (titre, quantité > 0, achat/vente), par date puis id."""
    filters = [
        InvestmentTransaction.account_id == account_id,
        InvestmentTransaction.ticker.isnot(None),
        InvestmentTransaction.quantity > 0,
        InvestmentTransaction.type.in_(TRADE_TYPES),
    ]
    if until is not None:
        filters.append(InvestmentTransaction.date <= until)
    return (
        db.query(InvestmentTransaction)
        .filter(*filters)
        .order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc())
        .all()
    )


def buys(db: Session, account_id: int) -> list[InvestmentTransaction]:
    """Versements et achats d'un compte, par date puis id."""
    return (
        db.query(InvestmentTransaction)
        .filter(InvestmentTransaction.account_id == account_id, InvestmentTransaction.type.in_(BUY_TYPES))
        .order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc())
        .all()
    )


def dividends(db: Session, account_id: int | None = None) -> list[InvestmentTransaction]:
    query = db.query(InvestmentTransaction).filter(InvestmentTransaction.type == DIVIDEND_TYPE)
    if account_id is not None:
        query = query.filter(InvestmentTransaction.account_id == account_id)
    return query.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).all()


def account_currencies(db: Session) -> dict[int, str]:
    return {acc_id: cur for acc_id, cur in db.query(Account.id, Account.currency).all()}


def delete_reinvestments(db: Session, dividend_id: int) -> None:
    """Supprime l'achat lié à un dividende réinvesti, puis flush."""
    db.query(InvestmentTransaction).filter(InvestmentTransaction.reinvest_of_id == dividend_id).delete()
    db.flush()


def add(db: Session, tx: InvestmentTransaction) -> None:
    db.add(tx)
    db.flush()
