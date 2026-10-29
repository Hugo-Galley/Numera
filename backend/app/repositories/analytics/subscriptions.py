"""Requêtes des abonnements : récurrences, abonnements potentiels, total « Abonnement » d'un mois."""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction


def recurrings(db: Session, account_id: int | None, include_other: bool) -> list[RecurringTransaction]:
    query = db.query(RecurringTransaction)
    if not include_other:
        query = query.filter(RecurringTransaction.type == "Sortie")
    if account_id:
        query = query.filter(RecurringTransaction.account_id == account_id)
    return query.all()


def last_occurrence(db: Session, recurring_id: int) -> Transaction | None:
    return db.query(Transaction).filter(
        Transaction.recurring_transaction_id == recurring_id
    ).order_by(Transaction.date.desc()).first()


def potential_subscriptions(db: Session, since: datetime, account_id: int | None) -> list:
    """Sorties répétées (même marchand, même montant, au moins deux) hors récurrences et ignorées."""
    query = db.query(
        Transaction.merchant,
        Transaction.amount,
        Category.name.label("category_name"),
        func.count(Transaction.id).label("count"),
        func.max(Transaction.date).label("last_date")
    ).join(Category, Transaction.category_id == Category.id, isouter=True) \
     .filter(Transaction.type == "Sortie") \
     .filter(Transaction.date >= since) \
     .filter(Transaction.recurring_transaction_id == None) \
     .filter(Transaction.is_subscription_ignored == False) \
     .group_by(Transaction.merchant, Transaction.amount, Category.id) \
     .having(func.count(Transaction.id) >= 2)  # noqa: E711, E712
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    return query.all()


def ignore_detection(db: Session, merchant: str, amount: float) -> None:
    db.query(Transaction).filter(
        Transaction.merchant == merchant,
        Transaction.amount == amount,
        Transaction.recurring_transaction_id == None  # noqa: E711
    ).update({"is_subscription_ignored": True}, synchronize_session=False)


def subscription_category_rows(db: Session, start: datetime, end: datetime, tr_accounts: set[int]) -> list:
    """Sorties de catégorie « Abonnement » par devise, hors tickets restaurant."""
    query = (
        db.query(Account.currency, func.coalesce(func.sum(Transaction.amount), 0.0).label("total"))
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,  # noqa: E712
            Category.name == "Abonnement",
        )
    )
    if tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query.group_by(Account.currency).all()
