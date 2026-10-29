"""Requêtes des rapports : flux du money-flow, nœuds du Sankey, soldes et récurrences de la projection de trésorerie."""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.repositories.analytics.budget import INVESTMENT_CATEGORIES
from app.repositories.analytics.common import NET_AMOUNT, budget_versement_ids, category_lines, income_criterion


def _scope(query, account_id: int | None, tr_accounts: set[int], *extra):
    """Un compte, ou courant/épargne hors tickets restaurant (plus d'éventuels critères de la vue globale)."""
    if account_id:
        return query.filter(Transaction.account_id == account_id)
    query = query.filter(Account.type.in_(["courant", "epargne"]), *extra)
    if tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query


def money_flow_rows(db: Session, start: datetime, end: datetime, account_id: int | None, tr_accounts: set[int]) -> list:
    """(Transaction, nom de catégorie, devise du compte) hors virements."""
    query = (
        db.query(Transaction, Category.name.label("cat_name"), Account.currency.label("acc_currency"))
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.date >= start, Transaction.date < end)
        .filter(Transaction.is_transfer == False)  # noqa: E712
    )
    return _scope(query, account_id, tr_accounts).all()


def budget_versements(db: Session, start: datetime, end: datetime) -> list:
    """(montant, devise, nom du compte) des versements alimentés par un virement interne lié."""
    return (
        db.query(InvestmentTransaction.amount, Account.currency, Account.name)
        .join(Account, InvestmentTransaction.account_id == Account.id)
        .filter(
            InvestmentTransaction.type == "versement",
            InvestmentTransaction.date >= start,
            InvestmentTransaction.date < end,
            InvestmentTransaction.id.in_(budget_versement_ids(db)),
        )
        .all()
    )


def sankey_expense_rows(db: Session, start: datetime, end: datetime, account_id: int | None, tr_accounts: set[int]) -> list:
    """(Category, devise, total) des dépenses catégorisées hors Investissement/Epargne (traités à part)."""
    lines = category_lines()
    query = (
        db.query(Category, Account.currency, func.coalesce(func.sum(lines.c.net_amount), 0.0).label("total"))
        .select_from(Transaction)
        .join(lines, lines.c.transaction_id == Transaction.id)
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, lines.c.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,  # noqa: E712
            ~Category.name.in_(INVESTMENT_CATEGORIES)
        )
    )
    return _scope(query, account_id, tr_accounts).group_by(Category.id, Account.currency).all()


def sankey_income_rows(db: Session, start: datetime, end: datetime, account_id: int | None, tr_accounts: set[int]) -> list:
    """(Category | None, devise, total) des revenus (Solde Initial exclu : base du solde, pas un revenu)."""
    query = (
        db.query(Category, Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total"))
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type.in_(["Entree", "Interets"]),
            Transaction.is_transfer == False  # noqa: E712
        )
    )
    return _scope(query, account_id, tr_accounts, income_criterion(db)).group_by(Category.id, Account.currency).all()


def dividend_rows(db: Session, start: datetime, end: datetime, account_id: int | None) -> list:
    query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(
        Account, InvestmentTransaction.account_id == Account.id
    ).filter(
        InvestmentTransaction.type == "dividende",
        InvestmentTransaction.date >= start,
        InvestmentTransaction.date < end
    )
    if account_id:
        query = query.filter(InvestmentTransaction.account_id == account_id)
    return query.group_by(Account.currency).all()


# --- Projection de trésorerie ---

def get_account(db: Session, account_id: int) -> Account | None:
    return db.query(Account).filter(Account.id == account_id).first()


def active_accounts(db: Session) -> list[Account]:
    return db.query(Account).filter(Account.active == True).all()  # noqa: E712


def last_transaction(db: Session, account_id: int) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .first()
    )


def active_recurrings(db: Session, account_id: int | None, tr_accounts: set[int]) -> list[RecurringTransaction]:
    query = db.query(RecurringTransaction).filter(RecurringTransaction.is_active == True)  # noqa: E712
    if account_id:
        query = query.filter(RecurringTransaction.account_id == account_id)
    elif tr_accounts:
        query = query.filter(RecurringTransaction.account_id.notin_(tr_accounts))
    return query.all()


def last_occurrence(db: Session, recurring_id: int) -> datetime | None:
    return db.query(func.max(Transaction.date)).filter(Transaction.recurring_transaction_id == recurring_id).scalar()
