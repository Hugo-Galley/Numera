from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Query, Session

from app.models.account import Account
from app.models.category import Category
from app.models.merchant import Merchant
from app.models.tag import Tag
from app.models.transaction import Transaction
from app.models.transaction_split import TransactionSplit
from app.repositories.analytics.common import ticket_restaurant_account_ids


@dataclass
class TransactionFilters:
    """Filtres de `GET /transactions` (mêmes noms que les paramètres de la route)."""
    account_id: int | None = None
    category_id: int | None = None
    type: str | None = None
    merchant: str | None = None
    month: int | None = None
    year: int | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_transfer: bool | None = None
    tag_ids: list[int] | None = None
    search: str | None = None
    uncategorized: bool = False
    merchant_name: str | None = None
    period: bool = False
    # Bornes du mois de paie, résolues par le service quand `period` est vrai
    period_start: datetime | None = None
    period_end: datetime | None = None
    budget_scope: bool = False


def get(db: Session, transaction_id: int) -> Transaction | None:
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def distinct_merchants(db: Session) -> list[str]:
    rows = db.query(Transaction.merchant).distinct().order_by(Transaction.merchant.asc()).all()
    return [m[0] for m in rows if m[0]]


def _column_filters(db: Session, query: Query, f: TransactionFilters) -> Query:
    if f.account_id is not None:
        query = query.filter(Transaction.account_id == f.account_id)
    if f.category_id is not None:
        # Une dépense découpée apparaît sous chacune des catégories de ses parts
        split_tx_ids = db.query(TransactionSplit.transaction_id).filter(TransactionSplit.category_id == f.category_id)
        query = query.filter(or_(Transaction.category_id == f.category_id, Transaction.id.in_(split_tx_ids)))
    if f.type is not None:
        query = query.filter(Transaction.type == f.type)
    if f.merchant is not None:
        query = query.filter(Transaction.merchant.ilike(f"%{f.merchant}%"))
    if f.min_amount is not None:
        query = query.filter(Transaction.amount >= f.min_amount)
    if f.max_amount is not None:
        query = query.filter(Transaction.amount <= f.max_amount)
    if f.start_date is not None:
        query = query.filter(Transaction.date >= f.start_date)
    if f.end_date is not None:
        query = query.filter(Transaction.date <= f.end_date)
    if f.is_transfer is not None:
        query = query.filter(Transaction.is_transfer == f.is_transfer)
    if f.uncategorized:
        query = query.filter(Transaction.category_id.is_(None))
    return query


def _join_filters(db: Session, query: Query, f: TransactionFilters) -> Query:
    if f.tag_ids:
        query = query.join(Transaction.tags).filter(Tag.id.in_(f.tag_ids))
    if f.search:
        search_filter = f"%{f.search}%"
        query = query.outerjoin(Category, Transaction.category_id == Category.id).filter(
            or_(
                Transaction.merchant.ilike(search_filter),
                Transaction.note.ilike(search_filter),
                Transaction.type.ilike(search_filter),
                Category.name.ilike(search_filter),
            )
        )
    if f.merchant_name is not None:
        query = query.outerjoin(Merchant, Transaction.merchant_id == Merchant.id).filter(
            func.coalesce(Merchant.name, Transaction.merchant) == f.merchant_name
        )
    if f.budget_scope:
        query = query.join(Account, Transaction.account_id == Account.id).filter(Account.type.in_(["courant", "epargne"]))
        tr_accounts = ticket_restaurant_account_ids(db)
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query


def _month_filter(db: Session, query: Query, f: TransactionFilters) -> Query:
    if f.month is None or f.year is None:
        return query
    if f.period:  # mois de paie, comme les analytics
        start, end = f.period_start, f.period_end
    else:
        start = datetime(f.year, f.month, 1)
        end = datetime(f.year + (1 if f.month == 12 else 0), 1 if f.month == 12 else f.month + 1, 1)
    return query.filter(and_(Transaction.date >= start, Transaction.date < end))


def filtered(db: Session, f: TransactionFilters, skip: int, limit: int) -> list[Transaction]:
    """Transactions filtrées, de la plus récente à la plus ancienne."""
    query = db.query(Transaction)
    query = _column_filters(db, query, f)
    query = _join_filters(db, query, f)
    query = _month_filter(db, query, f)
    return query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(skip).limit(limit).all()


def get_many(db: Session, ids: list[int]) -> list[Transaction]:
    return db.query(Transaction).filter(Transaction.id.in_(ids)).all()


def get_investment(db: Session, investment_transaction_id: int):
    from app.models.investment_transaction import InvestmentTransaction

    return db.query(InvestmentTransaction).filter(InvestmentTransaction.id == investment_transaction_id).first()


def tags_by_ids(db: Session, tag_ids: list[int]) -> list[Tag]:
    return db.query(Tag).filter(Tag.id.in_(tag_ids)).all()


def other_initial_balance(db: Session, account_id: int, exclude_id: int | None) -> Transaction | None:
    return db.query(Transaction).filter(
        Transaction.account_id == account_id,
        Transaction.type == "Solde Initial",
        Transaction.id != (exclude_id or -1),
    ).first()


def earliest_other(db: Session, account_id: int, exclude_id: int | None) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id, Transaction.id != (exclude_id or -1))
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .first()
    )


def add(db: Session, tx: Transaction) -> None:
    db.add(tx)
    db.flush()


def delete(db: Session, tx: Transaction) -> None:
    db.delete(tx)
