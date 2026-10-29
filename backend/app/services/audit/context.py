"""Contexte partagé par les règles du Centre d'Actions."""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Query, Session

from app.repositories.analytics import audit as repo
from app.services import reimbursements as remb


@dataclass
class AuditContext:
    db: Session
    now: datetime


def unallocated_reimbursements_query(db: Session, now: datetime) -> Query | None:
    """Remboursements reçus (catégorie « Remboursement… ») non affectés, s'il existe une créance ouverte."""
    has_open_claim = any(
        remb.claim_received(db, claim.id) < claim.expected_amount - remb.EPS
        for claim in repo.reimbursement_claims(db)
    )
    if not has_open_claim:
        return None
    return repo.unallocated_reimbursements(db, now)
