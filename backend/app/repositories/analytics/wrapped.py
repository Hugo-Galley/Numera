"""Requêtes du bilan annuel : sorties réelles, abonnements, dividendes, années disponibles."""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.domain.wrapped import NON_EXPENSE_CATEGORIES
from app.models.account import Account
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.repositories.analytics.common import NET_AMOUNT


def expense_query(db: Session, start: datetime, end: datetime, tr_accounts: set[int]) -> Query:
    """Sorties réelles du budget : hors virements internes et comptes tickets restaurant."""
    query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,  # noqa: E712
            Account.type.in_(["courant", "epargne"]),
        )
    )
    if tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query


def subscription_recurrings(db: Session) -> list[RecurringTransaction]:
    """Récurrences de dépense « abonnement » : ni virement, ni épargne/investissement."""
    return (
        db.query(RecurringTransaction)
        .outerjoin(Category, RecurringTransaction.category_id == Category.id)
        .filter(
            RecurringTransaction.type == "Sortie",
            RecurringTransaction.transfer_to_account_id.is_(None),
            func.coalesce(Category.name, "").notin_(NON_EXPENSE_CATEGORIES),
        )
        .all()
    )


def dividend_rows(db: Session, start: datetime, end: datetime) -> list:
    return (
        db.query(Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total"))
        .join(Account, InvestmentTransaction.account_id == Account.id)
        .filter(
            InvestmentTransaction.type == "dividende",
            InvestmentTransaction.date >= start,
            InvestmentTransaction.date < end,
        )
        .group_by(Account.currency)
        .all()
    )


def subscription_expense_rows(db: Session, start: datetime, end: datetime, tr_accounts: set[int],
                              recurring_ids: list[int]) -> list:
    return (
        expense_query(db, start, end, tr_accounts)
        .filter(Transaction.recurring_transaction_id.in_(recurring_ids))
        .with_entities(Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total"))
        .group_by(Account.currency)
        .all()
    )


def expense_count(db: Session, start: datetime, end: datetime, tr_accounts: set[int]) -> int:
    return expense_query(db, start, end, tr_accounts).count()


def biggest_expense_candidates(db: Session, start: datetime, end: datetime, tr_accounts: set[int]) -> list:
    """Vingt plus grosses sorties nettes hors épargne/investissement, avec devise et catégorie."""
    return (
        expense_query(db, start, end, tr_accounts)
        .filter(func.coalesce(Category.name, "").notin_(NON_EXPENSE_CATEGORIES))
        .with_entities(Transaction, Account.currency, Category.name.label("category_name"))
        .order_by(NET_AMOUNT.desc())
        .limit(20)
        .all()
    )


def recurring_bounds(db: Session, recurring_ids: list[int]) -> list:
    """Première et dernière échéance réelle de chaque récurrence."""
    return (
        db.query(
            Transaction.recurring_transaction_id,
            func.min(Transaction.date).label("first"),
            func.max(Transaction.date).label("last"),
        )
        .filter(Transaction.recurring_transaction_id.in_(recurring_ids))
        .group_by(Transaction.recurring_transaction_id)
        .all()
    )


def available_years(db: Session) -> list[int]:
    rows = (
        db.query(func.strftime("%Y", Transaction.date))
        .filter(Transaction.type != "Solde Initial")
        .distinct()
        .all()
    )
    return sorted((int(r[0]) for r in rows if r[0]), reverse=True)
