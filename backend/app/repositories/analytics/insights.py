"""Requêtes des insights : sorties du mois, catégories, insights écartés."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.dismissed_insight import DismissedInsight
from app.models.transaction import Transaction


def month_expenses(db: Session, start: datetime, end: datetime, account_id: int | None, tr_accounts: set[int]) -> list:
    """(Transaction, devise du compte) des sorties hors virements."""
    query = db.query(Transaction, Account.currency).join(Account).filter(
        Transaction.date >= start,
        Transaction.date < end,
        Transaction.type == "Sortie",
        Transaction.is_transfer == False
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    elif tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query.all()


def get_category(db: Session, category_id) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def dismissed_titles(db: Session) -> set[str]:
    return set(db.scalars(select(DismissedInsight.title)))


def is_dismissed(db: Session, title: str) -> bool:
    return db.query(DismissedInsight).filter(DismissedInsight.title == title).first() is not None


def add_dismissed(db: Session, title: str) -> None:
    db.add(DismissedInsight(title=title))
