"""Opérations d'investissement (`investment_transactions`)."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.dividends import DIVIDEND_TYPE
from app.domain.holdings import BUY_TYPES, TRADE_TYPES
from app.models.account import Account
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.transaction import Transaction


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


def list_for(db: Session, account_id: int | None, skip: int, limit: int | None) -> list[InvestmentTransaction]:
    query = db.query(InvestmentTransaction)
    if account_id is not None:
        query = query.filter(InvestmentTransaction.account_id == account_id)
    query = query.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def get(db: Session, tx_id: int) -> InvestmentTransaction | None:
    return db.query(InvestmentTransaction).filter(InvestmentTransaction.id == tx_id).first()


def dividend_link_candidates(db: Session, account_id: int) -> dict[str, str]:
    """Titres auxquels rattacher un dividende : positions, puis inventaire, puis titres des opérations."""
    candidates: dict[str, str] = {}
    for h in db.query(PortfolioHolding).filter(PortfolioHolding.account_id == account_id).all():
        candidates[h.ticker] = h.asset_name
    for b in db.query(HoldingBaselineItem).filter(HoldingBaselineItem.account_id == account_id).all():
        candidates.setdefault(b.ticker, b.asset_name)
    for ticker, name in (
        db.query(InvestmentTransaction.ticker, InvestmentTransaction.note)
        .filter(InvestmentTransaction.account_id == account_id, InvestmentTransaction.ticker.isnot(None))
        .distinct()
        .all()
    ):
        candidates.setdefault(ticker, name or ticker)
    return candidates


def unlinked_dividends(db: Session, account_id: int) -> list[InvestmentTransaction]:
    return (
        db.query(InvestmentTransaction)
        .filter(
            InvestmentTransaction.account_id == account_id,
            InvestmentTransaction.type == DIVIDEND_TYPE,
            InvestmentTransaction.ticker.is_(None),
        )
        .order_by(InvestmentTransaction.date.asc())
        .all()
    )


def linked_bank_transactions(db: Session, tx_id: int) -> list[Transaction]:
    return db.query(Transaction).filter(Transaction.linked_investment_transaction_id == tx_id).all()


def holding(db: Session, account_id: int, ticker: str) -> PortfolioHolding | None:
    return db.query(PortfolioHolding).filter(
        PortfolioHolding.account_id == account_id, PortfolioHolding.ticker == ticker.upper().strip()
    ).first()


def delete(db: Session, tx: InvestmentTransaction) -> None:
    db.delete(tx)
