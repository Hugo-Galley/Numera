from sqlalchemy import func, select, union
from sqlalchemy.orm import Session

from app.models.reimbursement import ReimbursementAllocation, ReimbursementClaim


def locked_transaction_ids():
    """Sous-requête des transactions portant une créance ou une affectation (exclues des virements)."""
    return union(
        select(ReimbursementClaim.transaction_id),
        select(ReimbursementAllocation.entree_transaction_id),
    )


def claim_received_total(db: Session, claim_id: int) -> float:
    return db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0)).filter(
        ReimbursementAllocation.claim_id == claim_id
    ).scalar()


def entree_allocated_total(db: Session, entree_id: int) -> float:
    return db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0)).filter(
        ReimbursementAllocation.entree_transaction_id == entree_id
    ).scalar()


def sortie_expected_total(db: Session, sortie_id: int, exclude_claim_id: int | None = None) -> float:
    q = db.query(func.coalesce(func.sum(ReimbursementClaim.expected_amount), 0.0)).filter(
        ReimbursementClaim.transaction_id == sortie_id
    )
    if exclude_claim_id is not None:
        q = q.filter(ReimbursementClaim.id != exclude_claim_id)
    return q.scalar()


def sortie_received_total(db: Session, sortie_id: int) -> float:
    return (
        db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0))
        .join(ReimbursementClaim, ReimbursementAllocation.claim_id == ReimbursementClaim.id)
        .filter(ReimbursementClaim.transaction_id == sortie_id)
        .scalar()
    )


def has_reimbursement(db: Session, tx_id: int) -> bool:
    if db.query(ReimbursementClaim.id).filter(ReimbursementClaim.transaction_id == tx_id).first():
        return True
    return db.query(ReimbursementAllocation.id).filter(ReimbursementAllocation.entree_transaction_id == tx_id).first() is not None


def get_claim(db: Session, claim_id: int) -> ReimbursementClaim | None:
    return db.get(ReimbursementClaim, claim_id)


def get_allocation(db: Session, allocation_id: int) -> ReimbursementAllocation | None:
    return db.get(ReimbursementAllocation, allocation_id)
