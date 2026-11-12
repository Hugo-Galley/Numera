from datetime import datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from app.models.account import Account
from app.models.category import Category
from app.models.month_closure import MonthClosure
from app.models.transaction import Transaction
from app.repositories.analytics.common import NET_AMOUNT
from app.repositories.types import QueryT, Rows


def get_closure(db: Session, year: int, month: int) -> MonthClosure | None:
    return db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).first()


def delete_closure(db: Session, year: int, month: int) -> None:
    db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).delete()


def list_closures(db: Session) -> list[MonthClosure]:
    return db.query(MonthClosure).order_by(MonthClosure.year.desc(), MonthClosure.month.desc()).all()


def exceptional_expense_totals(db: Session, start: datetime, end: datetime, excluded_categories: list[str],
                               account_id: int | None, tr_accounts: set[int]) -> Rows:
    """(devise, total net) des dépenses exceptionnelles, hors catégories exclues ; vue globale : courant/épargne hors tickets restaurant."""
    query: Query[Any] = (
        db.query(Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0))
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.is_exceptional.is_(True),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
            or_(Category.name.is_(None), Category.name.notin_(excluded_categories)),
        )
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    else:
        query = query.filter(Account.type.in_(["courant", "epargne"]))
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    rows: Rows = query.group_by(Account.currency).all()
    return rows


def transaction_count(db: Session, start: datetime, end: datetime) -> int:
    return db.query(Transaction).filter(Transaction.date >= start, Transaction.date < end).count()


def uncategorized_expenses(db: Session, start: datetime, end: datetime, limit: int) -> tuple[int, float | None, list[Transaction]]:
    """(nombre, total net, plus grosses lignes) des sorties sans catégorie du mois."""

    def scoped(query: QueryT) -> QueryT:
        return query.filter(
            Transaction.category_id.is_(None),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
        )

    base = scoped(db.query(Transaction))
    count = base.count()
    total: float | None = scoped(db.query(func.coalesce(func.sum(NET_AMOUNT), 0.0))).scalar()
    items: list[Transaction] = base.order_by(Transaction.amount.desc(), Transaction.id.asc()).limit(limit).all()
    return count, total, items


def top_expense_rows(db: Session, start: datetime, end: datetime, excluded_categories: list[str],
                     tr_accounts: set[int], limit: int) -> list[Transaction]:
    """Plus grosses dépenses nettes (courant/épargne, hors virements, catégories exclues et tickets restaurant)."""
    query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
            Account.type.in_(["courant", "epargne"]),
            or_(Category.name.is_(None), Category.name.notin_(excluded_categories)),
        )
    )
    if tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    rows: list[Transaction] = query.order_by(NET_AMOUNT.desc(), Transaction.id.asc()).limit(limit).all()
    return rows


def month_totals_by_currency(db: Session, start: datetime, end: datetime) -> Rows:
    """(devise, type, total net) des entrées, intérêts et sorties du mois, hors virements."""
    rows: Rows = (
        db.query(Account.currency, Transaction.type, func.coalesce(func.sum(NET_AMOUNT), 0.0))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type.in_(["Entree", "Interets", "Sortie"]),
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Account.currency, Transaction.type)
        .all()
    )
    return rows
