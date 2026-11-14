"""Requêtes des investissements : comptes titres, relevés, flux (opérations et transactions), répartitions."""
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.repositories.investissement.portfolio import only_transfer_legs
from app.repositories.types import Rows

INVESTMENT_TYPES = ["investissement", "assurance_vie"]


def get_account(db: Session, account_id: int) -> Account | None:
    return db.query(Account).filter(Account.id == account_id).first()


def investment_accounts(db: Session, account_id: int | None = None) -> list[Account]:
    """Comptes titres et assurances-vie actifs (un seul si `account_id`)."""
    query = db.query(Account).filter(Account.type.in_(INVESTMENT_TYPES), Account.active.is_(True))
    if account_id:
        query = query.filter(Account.id == account_id)
    return query.all()


def securities_accounts(db: Session) -> list[Account]:
    """Comptes titres actifs, par id."""
    return db.query(Account).filter(Account.type == "investissement", Account.active.is_(True)).order_by(Account.id).all()


def latest_zero_point(db: Session, account_id: int, until: datetime | None = None) -> BalanceSnapshot | None:
    query = db.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.is_zero_point.is_(True))
    if until is not None:
        query = query.filter(BalanceSnapshot.date <= until)
    return query.order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()).first()


def snapshots(db: Session, account_id: int, since: datetime | None = None) -> list[BalanceSnapshot]:
    query = db.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account_id)
    if since is not None:
        query = query.filter(BalanceSnapshot.date >= since)
    return query.order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc()).all()


def investment_operations(db: Session, account_id: int, until: datetime | None = None, since: datetime | None = None,
                          after: datetime | None = None, ordered: bool = False) -> list[InvestmentTransaction]:
    """Opérations d'investissement du compte : jusqu'à `until`, depuis `since` (inclus) ou après `after` (exclu)."""
    query = db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account_id)
    if until is not None:
        query = query.filter(InvestmentTransaction.date <= until)
    if since is not None:
        query = query.filter(InvestmentTransaction.date >= since)
    elif after is not None:
        query = query.filter(InvestmentTransaction.date > after)
    if ordered:
        query = query.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc())
    return query.all()


def has_investment_operations(db: Session, account_id: int) -> bool:
    return db.query(InvestmentTransaction.id).filter(InvestmentTransaction.account_id == account_id).first() is not None


def account_transactions(db: Session, account_id: int, until: datetime | None = None, since: datetime | None = None,
                         after: datetime | None = None, transfer_legs_only: bool = False, ordered: bool = False) -> list[Transaction]:
    """Transactions bancaires du compte (catégorie jointe) ; `transfer_legs_only` ne garde que les virements."""
    query = db.query(Transaction).outerjoin(Category, Transaction.category_id == Category.id).filter(
        Transaction.account_id == account_id
    )
    if until is not None:
        query = query.filter(Transaction.date <= until)
    if since is not None:
        query = query.filter(Transaction.date >= since)
    elif after is not None:
        query = query.filter(Transaction.date > after)
    if transfer_legs_only:
        query = only_transfer_legs(query)
    if ordered:
        query = query.order_by(Transaction.date.asc(), Transaction.id.asc())
    return query.all()


def allocated_operations(db: Session, account_id: int) -> list[InvestmentTransaction]:
    """Opérations portant une classe d'actifs (répartition avancée)."""
    return db.query(InvestmentTransaction).filter(
        InvestmentTransaction.account_id == account_id,
        InvestmentTransaction.asset_class.isnot(None)
    ).all()


def distinct_values(db: Session, column: InstrumentedAttribute[Any]) -> Rows:
    rows: Rows = db.query(column).filter(column.isnot(None)).distinct().all()
    return rows
