from datetime import datetime
from typing import Any

from sqlalchemy import CompoundSelect, func, select, union
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.reimbursement import ReimbursementAllocation, ReimbursementClaim
from app.models.transaction import Transaction


def locked_transaction_ids() -> CompoundSelect[*tuple[Any, ...]]:
    """Sous-requête des transactions portant une créance ou une affectation (exclues des virements)."""
    return union(
        select(ReimbursementClaim.transaction_id),
        select(ReimbursementAllocation.entree_transaction_id),
    )


def claim_received_total(db: Session, claim_id: int) -> float:
    total: float = db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0)).filter(
        ReimbursementAllocation.claim_id == claim_id
    ).scalar()
    return total


def entree_allocated_total(db: Session, entree_id: int) -> float:
    total: float = db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0)).filter(
        ReimbursementAllocation.entree_transaction_id == entree_id
    ).scalar()
    return total


def sortie_expected_total(db: Session, sortie_id: int, exclude_claim_id: int | None = None) -> float:
    q = db.query(func.coalesce(func.sum(ReimbursementClaim.expected_amount), 0.0)).filter(
        ReimbursementClaim.transaction_id == sortie_id
    )
    if exclude_claim_id is not None:
        q = q.filter(ReimbursementClaim.id != exclude_claim_id)
    total: float = q.scalar()
    return total


def sortie_received_total(db: Session, sortie_id: int) -> float:
    total: float = (
        db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0))
        .join(ReimbursementClaim, ReimbursementAllocation.claim_id == ReimbursementClaim.id)
        .filter(ReimbursementClaim.transaction_id == sortie_id)
        .scalar()
    )
    return total


def has_reimbursement(db: Session, tx_id: int) -> bool:
    if db.query(ReimbursementClaim.id).filter(ReimbursementClaim.transaction_id == tx_id).first():
        return True
    return db.query(ReimbursementAllocation.id).filter(ReimbursementAllocation.entree_transaction_id == tx_id).first() is not None


def get_claim(db: Session, claim_id: int) -> ReimbursementClaim | None:
    return db.get(ReimbursementClaim, claim_id)


def get_allocation(db: Session, allocation_id: int) -> ReimbursementAllocation | None:
    return db.get(ReimbursementAllocation, allocation_id)


def received_by_claim(db: Session, claim_ids: list[int]) -> dict[int, float]:
    """Total affecté à chaque créance, en une requête groupée."""
    if not claim_ids:
        return {}
    rows = (
        db.query(ReimbursementAllocation.claim_id, func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0))
        .filter(ReimbursementAllocation.claim_id.in_(claim_ids))
        .group_by(ReimbursementAllocation.claim_id)
        .all()
    )
    return {claim_id: float(total) for claim_id, total in rows}


def transactions_with_currency(db: Session, tx_ids: set[int]) -> dict[int, tuple[Transaction, str]]:
    """Transactions et devise de leur compte, en une requête."""
    if not tx_ids:
        return {}
    rows = (
        db.query(Transaction, Account.currency)
        .join(Account, Transaction.account_id == Account.id)
        .filter(Transaction.id.in_(tx_ids))
        .all()
    )
    return {tx.id: (tx, currency or "EUR") for tx, currency in rows}


def claims_of(db: Session, transaction_id: int) -> list[ReimbursementClaim]:
    return db.query(ReimbursementClaim).filter(ReimbursementClaim.transaction_id == transaction_id).all()


def allocations_of_entree(db: Session, entree_id: int) -> list[ReimbursementAllocation]:
    return db.query(ReimbursementAllocation).filter(ReimbursementAllocation.entree_transaction_id == entree_id).all()


def allocation_between(db: Session, claim_id: int, entree_id: int) -> ReimbursementAllocation | None:
    return (
        db.query(ReimbursementAllocation)
        .filter(ReimbursementAllocation.claim_id == claim_id, ReimbursementAllocation.entree_transaction_id == entree_id)
        .first()
    )


def claims_by_date(db: Session, debtor: str | None) -> list[ReimbursementClaim]:
    """Créances (du débiteur donné, en minuscules, si fourni), de la dépense la plus récente à la plus ancienne."""
    q = db.query(ReimbursementClaim).join(Transaction, ReimbursementClaim.transaction_id == Transaction.id)
    if debtor:
        q = q.filter(func.lower(ReimbursementClaim.debtor) == debtor)
    return q.order_by(Transaction.date.desc(), ReimbursementClaim.id).all()


def entree_candidates(db: Session, currency: str, earliest: datetime, latest: datetime) -> list[Transaction]:
    """Entrées (hors virements) d'un compte de cette devise, entre `earliest` et `latest` inclus."""
    return (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type == "Entree",
            Transaction.is_transfer.is_(False),
            Account.currency == currency,
            Transaction.date >= earliest,
            Transaction.date <= latest,
        )
        .all()
    )
