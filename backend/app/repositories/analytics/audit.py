"""Requêtes du Centre d'Actions et de l'audit des données (requêtes de base, que le service ordonne et limite)."""
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Query, Session

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.categorization_rule import CategorizationRule
from app.models.category import Category
from app.models.dismissed_insight import DismissedInsight
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.reimbursement import ReimbursementClaim
from app.models.transaction import Transaction

DUPLICATE_KEY = (
    Transaction.account_id,
    Transaction.date,
    Transaction.type,
    Transaction.merchant,
    Transaction.amount,
    Transaction.currency,
)


def uncategorized_expenses(db: Session) -> Query:
    """Sorties sans catégorie, hors virements (non ordonnées)."""
    return db.query(Transaction).filter(
        Transaction.category_id.is_(None),
        Transaction.type == "Sortie",
        Transaction.is_transfer.is_(False),
    )


def missing_merchants(db: Session) -> Query:
    return db.query(Transaction).filter(
        or_(Transaction.merchant.is_(None), func.trim(Transaction.merchant) == "")
    ).order_by(Transaction.date.desc(), Transaction.id.desc())


def duplicate_groups(db: Session) -> Query:
    """Groupes de transactions identiques (compte, date, type, marchand, montant, devise) non ignorés."""
    return (
        db.query(*DUPLICATE_KEY, func.count(Transaction.id).label("count"))
        .filter(Transaction.is_duplicate_ignored == False)
        .group_by(*DUPLICATE_KEY)
        .having(func.count(Transaction.id) > 1)
    )


def duplicate_group_transactions(db: Session, row) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(
            Transaction.account_id == row.account_id,
            Transaction.date == row.date,
            Transaction.type == row.type,
            Transaction.merchant == row.merchant,
            Transaction.amount == row.amount,
            Transaction.currency == row.currency,
        )
        .order_by(Transaction.id.asc())
        .all()
    )


def latest_snapshot_date(db: Session, account_id: int, id_tiebreak: bool = False) -> datetime | None:
    order = (BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()) if id_tiebreak else (BalanceSnapshot.date.desc(),)
    snapshot = db.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account_id).order_by(*order).first()
    return snapshot.date if snapshot else None


def recent_unlinked_sorties(db: Session, since: datetime, strict: bool, limit: int) -> list[Transaction]:
    """Sorties non rapprochées depuis `since` ; `strict` exclut aussi celles liées à une opération titres."""
    filters = [
        Transaction.type == "Sortie",
        Transaction.is_transfer.is_(False),
        Transaction.is_transfer_ignored.is_(False),
        Transaction.linked_transaction_id.is_(None),
    ]
    if strict:
        filters.append(Transaction.linked_investment_transaction_id.is_(None))
    query = db.query(Transaction).filter(*filters, Transaction.date >= since)
    if strict:
        query = query.order_by(Transaction.date.desc())
    return query.limit(limit).all()


def strict_transfer_candidates(db: Session, sorties: list[Transaction]) -> list[Transaction]:
    """Entrées candidates (même devise, non rapprochées) de toutes ces sorties, en une seule requête.
    L'appariement fin (autre compte, même montant, ±3 jours) est fait par `domain.transfers.strict_matches`."""
    if not sorties:
        return []
    return (
        db.query(Transaction)
        .filter(
            Transaction.type == "Entree",
            Transaction.amount.in_({s.amount for s in sorties}),
            Transaction.is_transfer.is_(False),
            Transaction.is_transfer_ignored.is_(False),
            Transaction.linked_transaction_id.is_(None),
            Transaction.date >= min(s.date for s in sorties) - timedelta(days=3),
            Transaction.date <= max(s.date for s in sorties) + timedelta(days=3),
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )


def reimbursement_claims(db: Session) -> list[ReimbursementClaim]:
    return db.query(ReimbursementClaim).all()


def unallocated_reimbursements(db: Session, now: datetime) -> Query:
    """Remboursements reçus (catégorie « Remboursement… ») non affectés, sur 180 jours."""
    return (
        db.query(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.type == "Entree",
            Category.name.ilike("Remboursement%"),
            Transaction.reimbursement_offset == 0,
            Transaction.is_transfer.is_(False),
            Transaction.date >= now - timedelta(days=180),
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )


def merchant_category_counts(db: Session, since: datetime) -> list:
    """(marchand, catégorie, nombre) des entrées/sorties hors virements et récurrences."""
    return (
        db.query(Transaction.merchant, Transaction.category_id, func.count(Transaction.id))
        .filter(
            Transaction.date >= since,
            Transaction.merchant.is_not(None), Transaction.merchant != "",
            Transaction.is_transfer.is_(False),
            Transaction.recurring_transaction_id.is_(None),
            Transaction.type.in_(["Sortie", "Entree"]),
        )
        .group_by(Transaction.merchant, Transaction.category_id)
        .all()
    )


def rule_exists(db: Session, merchant: str) -> bool:
    return db.query(CategorizationRule).filter(
        or_(
            func.lower(CategorizationRule.merchant_name) == func.lower(merchant),
            func.lower(CategorizationRule.pattern) == func.lower(merchant)
        )
    ).first() is not None


def unnormalized_merchant_counts(db: Session) -> Query:
    """(libellé, nombre) des transactions sans marchand canonique."""
    return (
        db.query(Transaction.merchant, func.count(Transaction.id).label("count"))
        .filter(Transaction.merchant_id.is_(None), Transaction.merchant.is_not(None), Transaction.merchant != "")
        .group_by(Transaction.merchant)
    )


def account_names(db: Session) -> dict[int, str]:
    return {a.id: a.name for a in db.query(Account.id, Account.name).all()}


def unlinked_dividend_counts(db: Session) -> list:
    return (
        db.query(InvestmentTransaction.account_id, func.count(InvestmentTransaction.id))
        .filter(InvestmentTransaction.type == "dividende", InvestmentTransaction.ticker.is_(None))
        .group_by(InvestmentTransaction.account_id)
        .all()
    )


def last_dividend_by_ticker(db: Session) -> dict[tuple[int, str], datetime]:
    return {
        (acc_id, (ticker or "").upper()): last
        for acc_id, ticker, last in db.query(
            InvestmentTransaction.account_id, InvestmentTransaction.ticker, func.max(InvestmentTransaction.date)
        )
        .filter(InvestmentTransaction.type == "dividende", InvestmentTransaction.ticker.isnot(None))
        .group_by(InvestmentTransaction.account_id, InvestmentTransaction.ticker)
        .all()
    }


def dividend_paying_holdings(db: Session) -> list[PortfolioHolding]:
    return db.query(PortfolioHolding).filter(PortfolioHolding.pays_dividends.is_(True), PortfolioHolding.quantity > 0).all()


def active_investment_accounts(db: Session) -> list[Account]:
    return db.query(Account).filter(Account.type == "investissement", Account.active.is_(True)).all()


def dismissed_ids(db: Session) -> set[str]:
    return set(db.scalars(select(DismissedInsight.title)))


def is_dismissed(db: Session, action_id: str) -> bool:
    return db.query(DismissedInsight).filter(DismissedInsight.title == action_id).first() is not None


def add_dismissed(db: Session, action_id: str) -> None:
    db.add(DismissedInsight(title=action_id))


# --- Audit des données ---

def transaction_count(db: Session, account_id: int | None = None) -> int:
    query = db.query(func.count(Transaction.id))
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    return query.scalar() or 0


def active_account_count(db: Session) -> int:
    return db.query(func.count(Account.id)).filter(Account.active.is_(True)).scalar() or 0


def has_initial_balance(db: Session, account_id: int) -> bool:
    return db.query(Transaction.id).filter(
        Transaction.account_id == account_id, Transaction.type == "Solde Initial"
    ).first() is not None


def unused_categories(db: Session) -> list[Category]:
    return (
        db.query(Category)
        .outerjoin(Transaction, Transaction.category_id == Category.id)
        .filter(Category.archived.is_(False))
        .group_by(Category.id)
        .having(func.count(Transaction.id) == 0)
        .order_by(Category.name.asc())
        .limit(20)
        .all()
    )
