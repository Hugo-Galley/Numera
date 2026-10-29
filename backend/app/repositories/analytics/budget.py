"""Requêtes d'agrégat du budget : flux par devise (vue globale), sommes d'un compte, soldes et alertes."""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.repositories.analytics.common import NET_AMOUNT, budget_versement_ids, category_lines, income_criterion

INVESTMENT_CATEGORIES = ["Investissement", "Epargne"]
INTEREST_CATEGORIES = ["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"]


def _window(query: Query, column, start: datetime | None, end: datetime) -> Query:
    if start:
        query = query.filter(column >= start)
    return query.filter(column < end)


def _exclude(query: Query, tr_accounts: set[int]) -> Query:
    return query.filter(Transaction.account_id.notin_(tr_accounts)) if tr_accounts else query


def _net_by_currency(db: Session) -> Query:
    return db.query(
        Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
    ).join(Account, Transaction.account_id == Account.id)


# --- Vue globale : flux par devise du compte (courant/épargne, hors tickets restaurant) ---

def income_by_currency(db: Session, start: datetime | None, end: datetime, tr_accounts: set[int]) -> list:
    """Revenus au sens de income_criterion (Solde Initial jamais compté)."""
    query = _net_by_currency(db).filter(
        Transaction.type.in_(["Entree", "Interets"]), Transaction.is_transfer == False  # noqa: E712
    ).filter(Account.type.in_(["courant", "epargne"]), income_criterion(db))
    query = _window(_exclude(query, tr_accounts), Transaction.date, start, end)
    return query.group_by(Account.currency).all()


def dividends_total_by_currency(db: Session, start: datetime | None, end: datetime) -> list:
    """Dividendes des comptes titres, comptés en revenus."""
    query = db.query(
        Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")
    ).join(Account, InvestmentTransaction.account_id == Account.id).filter(InvestmentTransaction.type == "dividende")
    return _window(query, InvestmentTransaction.date, start, end).group_by(Account.currency).all()


def interests_by_currency(db: Session, start: datetime | None, end: datetime, tr_accounts: set[int]) -> list:
    """Intérêts (type ou catégorie intérêts/dividendes) des comptes courant/épargne."""
    query = _net_by_currency(db).outerjoin(Category, Transaction.category_id == Category.id).filter(
        ((Transaction.type == "Interets") | (Category.name.in_(INTEREST_CATEGORIES))),
        Transaction.is_transfer == False,  # noqa: E712
    ).filter(Account.type.in_(["courant", "epargne"]))
    query = _window(_exclude(query, tr_accounts), Transaction.date, start, end)
    return query.group_by(Account.currency).all()


def dividends_by_currency(db: Session, start: datetime | None, end: datetime) -> list:
    """Dividendes des comptes titres, ajoutés aux intérêts."""
    query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(
        Account, InvestmentTransaction.account_id == Account.id
    ).filter(InvestmentTransaction.type == "dividende", InvestmentTransaction.date < end)
    if start:
        query = query.filter(InvestmentTransaction.date >= start)
    return query.group_by(Account.currency).all()


def expenses_by_currency(db: Session, start: datetime | None, end: datetime, tr_accounts: set[int]) -> list:
    query = _net_by_currency(db).filter(
        Transaction.type == "Sortie", Transaction.is_transfer == False  # noqa: E712
    ).filter(Account.type.in_(["courant", "epargne"]))
    query = _window(_exclude(query, tr_accounts), Transaction.date, start, end)
    return query.group_by(Account.currency).all()


def categorized_investments_by_currency(db: Session, start: datetime | None, end: datetime, tr_accounts: set[int]) -> list:
    """Sorties catégorisées Investissement/Epargne (non consommées)."""
    query = _net_by_currency(db).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.type == "Sortie", Category.name.in_(INVESTMENT_CATEGORIES), Transaction.is_transfer == False  # noqa: E712
    )
    query = _exclude(_window(query, Transaction.date, start, end), tr_accounts)
    return query.group_by(Account.currency).all()


def budget_versements_by_currency(db: Session, start: datetime | None, end: datetime,
                                  account_id: int | None = None) -> list:
    """Versements d'un compte titres, ou (vue globale) ceux alimentés par un compte du budget."""
    query = db.query(
        Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")
    ).join(Account, InvestmentTransaction.account_id == Account.id).filter(InvestmentTransaction.type == "versement")
    query = _window(query, InvestmentTransaction.date, start, end)
    if account_id:
        query = query.filter(InvestmentTransaction.account_id == account_id)
    else:
        query = query.filter(InvestmentTransaction.id.in_(budget_versement_ids(db)))
    return query.group_by(Account.currency).all()


def earliest_transaction_date(db: Session) -> datetime | None:
    return db.query(func.min(Transaction.date)).scalar()


# --- Vue compte : sommes dans la devise du compte ---

def account_transactions_sum(db: Session, account_id: int, start: datetime | None, end: datetime,
                             types: list[str], investment_categories: bool = False) -> float:
    """Somme nette (hors virements) des transactions d'un compte, éventuellement limitée aux catégories d'investissement."""
    query = db.query(func.coalesce(func.sum(NET_AMOUNT), 0.0))
    if investment_categories:
        query = query.join(Category, Transaction.category_id == Category.id).filter(
            Transaction.account_id == account_id, Transaction.type.in_(types),
            Category.name.in_(INVESTMENT_CATEGORIES), Transaction.is_transfer == False,  # noqa: E712
        )
    else:
        query = query.filter(
            Transaction.account_id == account_id, Transaction.type.in_(types), Transaction.is_transfer == False  # noqa: E712
        )
    return float(_window(query, Transaction.date, start, end).scalar() or 0.0)


def account_investment_sum(db: Session, account_id: int, start: datetime | None, end: datetime, type_: str) -> float:
    query = db.query(func.coalesce(func.sum(InvestmentTransaction.amount), 0.0)).filter(
        InvestmentTransaction.account_id == account_id, InvestmentTransaction.type == type_
    )
    return float(_window(query, InvestmentTransaction.date, start, end).scalar() or 0.0)


def latest_snapshot(db: Session, account_id: int, end: datetime) -> BalanceSnapshot | None:
    return db.query(BalanceSnapshot).filter(
        BalanceSnapshot.account_id == account_id, BalanceSnapshot.date <= end
    ).order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()).first()


def last_transaction(db: Session, account_id: int, end: datetime) -> Transaction | None:
    return db.query(Transaction).filter(
        Transaction.account_id == account_id, Transaction.date <= end
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()


def latest_balance_rows(db: Session, account_id: int, end: datetime) -> list:
    """Dernier solde courant (date max puis id max) du compte, avec son type et sa devise."""
    account_last_tx = (
        db.query(Transaction.account_id.label("account_id"), func.max(Transaction.date).label("max_date"))
        .filter(Transaction.date <= end)
        .group_by(Transaction.account_id)
        .subquery()
    )
    latest_tx_ids = (
        db.query(func.max(Transaction.id).label("max_id"))
        .join(
            account_last_tx,
            (Transaction.account_id == account_last_tx.c.account_id) & (Transaction.date == account_last_tx.c.max_date),
        )
        .group_by(Transaction.account_id)
        .subquery()
    )
    return (
        db.query(Account.id, Account.type, Account.currency, func.coalesce(func.sum(Transaction.running_balance), 0.0).label("total"))
        .join(Account, Transaction.account_id == Account.id)
        .join(latest_tx_ids, Transaction.id == latest_tx_ids.c.max_id)
        .filter(Account.id == account_id)
        .group_by(Account.id, Account.type, Account.currency)
        .all()
    )


# --- Alertes de plafonds ---

def capped_categories(db: Session) -> list[Category]:
    return db.query(Category).filter(
        (Category.monthly_limit.isnot(None)) | (Category.annual_limit.isnot(None))
    ).all()


def category_spending_rows(db: Session, start: datetime, end: datetime, account_id: int | None,
                           tr_accounts: set[int]) -> list:
    """Dépenses par (catégorie, devise), dépenses découpées comprises (une ligne par part)."""
    lines = category_lines()
    query = (
        db.query(lines.c.category_id, Account.currency, func.sum(lines.c.net_amount))
        .select_from(Transaction)
        .join(lines, lines.c.transaction_id == Transaction.id)
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,  # noqa: E712
            Transaction.date >= start,
            Transaction.date < end,
        )
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    else:
        query = _exclude(query, tr_accounts)
    return query.group_by(lines.c.category_id, Account.currency).all()


def investment_category(db: Session) -> Category | None:
    return db.query(Category).filter(Category.name == "Investissement").first()
