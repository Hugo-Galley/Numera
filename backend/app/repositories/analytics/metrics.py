"""Requêtes d'agrégat des métriques : tags, catégories, marchands, flux d'un compte, kpi-history, timeseries, calendrier."""
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from app.models.account import Account
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.merchant import Merchant
from app.models.recurring_transaction import RecurringTransaction
from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.tag import Tag, transaction_tags
from app.models.telecommuting_day import TelecommutingDay
from app.models.transaction import Transaction
from app.repositories.analytics.budget import INTEREST_CATEGORIES, INVESTMENT_CATEGORIES
from app.repositories.analytics.common import NET_AMOUNT, budget_versement_ids, category_lines, income_criterion


def _budget_scope(db: Session, query: Query, account_id: int | None, tr_accounts: set[int]) -> Query:
    """Un compte, ou le périmètre du budget (courant/épargne hors tickets restaurant)."""
    if account_id:
        return query.filter(Transaction.account_id == account_id)
    query = query.filter(Account.type.in_(["courant", "epargne"]))
    if tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query


def tag_spending_rows(db: Session, start: datetime | None, end: datetime, account_id: int | None,
                      tr_accounts: set[int]) -> list:
    query = db.query(
        Tag.id,
        Tag.name,
        Tag.color,
        Account.currency,
        func.sum(NET_AMOUNT).label("total")
    ).join(transaction_tags, Tag.id == transaction_tags.c.tag_id) \
     .join(Transaction, Transaction.id == transaction_tags.c.transaction_id) \
     .join(Account, Transaction.account_id == Account.id) \
     .filter(Transaction.type == "Sortie", Transaction.is_transfer == False)  # noqa: E712
    if start:
        query = query.filter(Transaction.date >= start)
    query = query.filter(Transaction.date < end)
    return _budget_scope(db, query, account_id, tr_accounts).group_by(Tag.id, Account.currency).all()


def category_expense_rows(db: Session, start: datetime, end: datetime, account_id: int | None,
                          tr_accounts: set[int]) -> list:
    """(Category | None, devise, total) des sorties, dépenses découpées comprises."""
    lines = category_lines()
    query = (
        db.query(
            Category,
            Account.currency,
            func.coalesce(func.sum(lines.c.net_amount), 0.0).label("total"),
        )
        .select_from(Transaction)
        .join(lines, lines.c.transaction_id == Transaction.id)
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, lines.c.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,  # noqa: E712
        )
    )
    # Même périmètre que le budget : le total de la répartition doit égaler `depenses_totales`
    return _budget_scope(db, query, account_id, tr_accounts).group_by(Category.id, Account.currency).all()


def merchant_expense_rows(db: Session, start: datetime, end: datetime, account_id: int | None,
                          tr_accounts: set[int]) -> list:
    """(marchand canonique ou libellé, devise, total) des sorties hors Investissement/Epargne."""
    query = (
        db.query(
            func.coalesce(Merchant.name, Transaction.merchant).label("merchant"),
            Account.currency,
            func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .outerjoin(Merchant, Transaction.merchant_id == Merchant.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,  # noqa: E712
            func.coalesce(Category.name, "").notin_(INVESTMENT_CATEGORIES),
        )
    )
    query = _budget_scope(db, query, account_id, tr_accounts)
    return query.group_by(func.coalesce(Merchant.name, Transaction.merchant), Account.currency).all()


# --- Flux d'un compte ---

def get_account(db: Session, account_id: int) -> Account | None:
    return db.query(Account).filter(Account.id == account_id).first()


def flow_by_type(db: Session, account_id: int, start: datetime, end: datetime) -> dict[str, float]:
    rows = (
        db.query(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(
            Transaction.account_id == account_id,
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.is_transfer == False,  # noqa: E712
            Transaction.type.in_(["Entree", "Interets", "Sortie"]),
        )
        .group_by(Transaction.type)
        .all()
    )
    return {t: float(v) for t, v in rows}


def average_expense(db: Session, account_id: int, start: datetime | None, end: datetime | None) -> float:
    query = db.query(func.coalesce(func.avg(Transaction.amount), 0.0)).filter(
        Transaction.account_id == account_id,
        Transaction.type == "Sortie",
        Transaction.is_transfer == False,  # noqa: E712
    )
    if start is not None:
        query = query.filter(Transaction.date >= start)
    if end is not None:
        query = query.filter(Transaction.date <= end)
    return float(query.scalar() or 0.0)


# --- kpi-history (une requête par famille, groupée par mois budgétaire `label`) ---

def accounts_by_ids(db: Session, ids: list[int]) -> dict[int, Account]:
    return {acc.id: acc for acc in db.query(Account).filter(Account.id.in_(ids)).all()} if ids else {}


def earliest_transaction_date(db: Session, account_id: int | None) -> datetime | None:
    query = db.query(func.min(Transaction.date))
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    return query.scalar()


def kpi_transaction_rows(db: Session, label, start: datetime, end: datetime, account_id: int | None,
                         tr_accounts: set[int]) -> list:
    """(mois, devise, type, total) hors virements ; une entrée n'est un revenu que selon income_criterion."""
    query = db.query(
        label, Account.currency, Transaction.type, func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
    ).select_from(Transaction).join(Account, Transaction.account_id == Account.id).filter(
        Transaction.date >= start, Transaction.date < end,
        Transaction.is_transfer == False,  # noqa: E712
    )
    if not account_id:
        query = query.filter(Account.type.in_(["courant", "epargne"]))
        query = query.filter(or_(Transaction.type == "Sortie", income_criterion(db)))
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    else:
        query = query.filter(Transaction.account_id == account_id)
    return query.group_by(label, Account.currency, Transaction.type).all()


def kpi_investment_rows(db: Session, label, start: datetime, end: datetime, account_id: int | None) -> list:
    """(mois, devise, type, total) des dividendes et versements (vue globale : versements du budget seulement)."""
    query = db.query(
        label, Account.currency, InvestmentTransaction.type,
        func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")
    ).join(Account, InvestmentTransaction.account_id == Account.id).filter(
        InvestmentTransaction.date >= start,
        InvestmentTransaction.date < end,
        InvestmentTransaction.type.in_(["dividende", "versement"])
    )
    if account_id:
        query = query.filter(InvestmentTransaction.account_id == account_id)
    else:
        query = query.filter(or_(
            InvestmentTransaction.type != "versement",
            InvestmentTransaction.id.in_(budget_versement_ids(db)),
        ))
    return query.group_by(label, Account.currency, InvestmentTransaction.type).all()


def kpi_categorized_investment_rows(db: Session, label, start: datetime, end: datetime, account_id: int | None,
                                    tr_accounts: set[int]) -> list:
    query = db.query(
        label, Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
    ).select_from(Transaction).join(Account, Transaction.account_id == Account.id).join(
        Category, Transaction.category_id == Category.id
    ).filter(
        Transaction.date >= start, Transaction.date < end,
        Transaction.type == "Sortie",
        Category.name.in_(INVESTMENT_CATEGORIES),
        Transaction.is_transfer == False,  # noqa: E712
    )
    if not account_id:
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    else:
        query = query.filter(Transaction.account_id == account_id)
    return query.group_by(label, Account.currency).all()


def kpi_category_interest_rows(db: Session, label, start: datetime, end: datetime, account_id: int | None,
                               tr_accounts: set[int]) -> list:
    """Intérêts portés par une catégorie (hors type Interets, déjà compté)."""
    query = db.query(
        label, Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
    ).select_from(Transaction).join(Account, Transaction.account_id == Account.id).join(
        Category, Transaction.category_id == Category.id
    ).filter(
        Transaction.date >= start, Transaction.date < end,
        Transaction.type != "Interets",
        Category.name.in_(INTEREST_CATEGORIES)
    )
    return _budget_scope(db, query, account_id, tr_accounts).group_by(label, Account.currency).all()


# --- timeseries ---

def has_transaction_in_year(db: Session, year: int, account_id: int | None) -> bool:
    query = db.query(Transaction).filter(func.strftime("%Y", Transaction.date) == str(year))
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    return query.first() is not None


def month_income_rows(db: Session, start: datetime, end: datetime, account_id: int | None,
                      tr_accounts: set[int]) -> list:
    query = db.query(
        Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
    ).join(Account, Transaction.account_id == Account.id).filter(
        Transaction.date >= start,
        Transaction.date < end,
        Transaction.type.in_(["Entree", "Interets"]),
        Transaction.is_transfer == False,  # un virement interne n'est ni un revenu ni une dépense  # noqa: E712
    )
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    else:
        query = query.filter(Account.type.in_(["courant", "epargne"]), income_criterion(db))
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query.group_by(Account.currency).all()


def month_expense_rows(db: Session, start: datetime, end: datetime, account_id: int | None,
                       tr_accounts: set[int]) -> list:
    query = db.query(
        Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
    ).join(Account, Transaction.account_id == Account.id).filter(
        Transaction.date >= start,
        Transaction.date < end,
        Transaction.type == "Sortie",
        Transaction.is_transfer == False,  # noqa: E712
    )
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    else:
        query = query.filter(Account.type.in_(["courant", "epargne"]))
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query.group_by(Account.currency).all()


def month_investment_rows(db: Session, start: datetime, end: datetime, type_: str, account_id: int | None) -> list:
    query = db.query(
        Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")
    ).join(Account, InvestmentTransaction.account_id == Account.id).filter(
        InvestmentTransaction.date >= start, InvestmentTransaction.date < end, InvestmentTransaction.type == type_
    )
    if account_id:
        query = query.filter(InvestmentTransaction.account_id == account_id)
    return query.group_by(Account.currency).all()


def account_transactions(db: Session, account_id: int) -> list[Transaction]:
    return db.query(Transaction).order_by(Transaction.date.asc(), Transaction.id.asc()).filter(
        Transaction.account_id == account_id
    ).all()


def salary_rows(db: Session, start: datetime, end: datetime, account_id: int | None) -> list:
    """Entrées catégorisées « Salaire » par devise."""
    query = (
        db.query(Account.currency, func.coalesce(func.sum(Transaction.amount), 0.0).label("total"))
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Category.name == "Salaire",
            Transaction.type == "Entree",
        )
        .group_by(Account.currency)
    )
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    return query.all()


# --- calendrier ---

def transactions_between(db: Session, start: datetime, end: datetime, account_id: int | None,
                         tr_accounts: set[int]) -> list[Transaction]:
    query = db.query(Transaction).filter(Transaction.date >= start, Transaction.date < end)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    elif tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query.all()


def investment_transactions_between(db: Session, start: datetime, end: datetime,
                                    account_id: int | None) -> list[InvestmentTransaction]:
    query = db.query(InvestmentTransaction).filter(InvestmentTransaction.date >= start, InvestmentTransaction.date < end)
    if account_id:
        query = query.filter(InvestmentTransaction.account_id == account_id)
    return query.all()


def active_recurrings(db: Session, account_id: int | None, tr_accounts: set[int]) -> list[RecurringTransaction]:
    query = db.query(RecurringTransaction).filter(RecurringTransaction.is_active == True)  # noqa: E712
    if account_id:
        query = query.filter(RecurringTransaction.account_id == account_id)
    elif tr_accounts:
        query = query.filter(RecurringTransaction.account_id.notin_(tr_accounts))
    return query.all()


def salary_config_for_recurring(db: Session, recurring_id: int) -> SalaryConfig | None:
    return db.query(SalaryConfig).filter(
        (SalaryConfig.salary_recurring_id == recurring_id) | (SalaryConfig.ticket_recurring_id == recurring_id)
    ).first()


def salary_month(db: Session, config_id: int, label: str) -> SalaryMonth | None:
    return db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config_id, SalaryMonth.month_label == label
    ).first()


def telecommuting_count(db: Session, config_id: int, label: str) -> int:
    return db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config_id, TelecommutingDay.month_label == label
    ).count()


def all_accounts(db: Session) -> list[Account]:
    return db.query(Account).all()


def last_transaction_before(db: Session, account_id: int, before: datetime) -> Transaction | None:
    return db.query(Transaction).filter(
        Transaction.account_id == account_id, Transaction.date < before
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
