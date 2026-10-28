from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.core import reimbursements as remb
from app.models.reimbursement import ReimbursementAllocation, ReimbursementClaim
from app.models.transaction import Transaction
from app.schemas.reimbursement import (
    AllocationCreate,
    CandidateRead,
    ClaimCreate,
    ClaimRead,
    ClaimUpdate,
    EntryClaims,
    ReimbursementSummary,
)

router = APIRouter(prefix="/reimbursements", tags=["reimbursements"])


def _claim(db: Session, claim_id: int) -> ReimbursementClaim:
    claim = db.get(ReimbursementClaim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Créance introuvable")
    return claim


@router.get("/claims", response_model=list[ClaimRead])
def list_claims(
    status: str = Query(default="open", pattern="^(open|settled|all)$"),
    debtor: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Créances (« ce qu'on me doit ») ; `open` = reste dû > 0."""
    return remb.list_claims(db, status, debtor)


@router.get("/summary", response_model=ReimbursementSummary)
def reimbursement_summary(db: Session = Depends(get_db)):
    return remb.summary(db)


@router.post("/claims", response_model=ClaimRead, status_code=201)
def create_claim(payload: ClaimCreate, db: Session = Depends(get_db)):
    claim = remb.create_claim(db, payload.transaction_id, payload.debtor, payload.expected_amount, payload.note)
    return remb.claim_view(db, claim)


@router.patch("/claims/{claim_id}", response_model=ClaimRead)
def update_claim(claim_id: int, payload: ClaimUpdate, db: Session = Depends(get_db)):
    claim = remb.update_claim(db, _claim(db, claim_id), payload.model_dump(exclude_unset=True))
    return remb.claim_view(db, claim)


@router.delete("/claims/{claim_id}", status_code=204)
def delete_claim(claim_id: int, db: Session = Depends(get_db)):
    remb.delete_claim(db, _claim(db, claim_id))


@router.get("/claims/{claim_id}/candidates", response_model=list[CandidateRead])
def claim_candidates(claim_id: int, db: Session = Depends(get_db)):
    return remb.candidates(db, _claim(db, claim_id))


@router.post("/claims/{claim_id}/allocations", response_model=ClaimRead)
def allocate(claim_id: int, payload: AllocationCreate, db: Session = Depends(get_db)):
    claim = _claim(db, claim_id)
    remb.allocate(db, claim, payload.entree_id, payload.amount)
    return remb.claim_view(db, claim)


@router.delete("/allocations/{allocation_id}", status_code=204)
def remove_allocation(allocation_id: int, db: Session = Depends(get_db)):
    allocation = db.get(ReimbursementAllocation, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Affectation introuvable")
    remb.remove_allocation(db, allocation)


@router.get("/entries/{entree_id}/claims", response_model=EntryClaims)
def entry_claims(entree_id: int, db: Session = Depends(get_db)):
    entree = db.get(Transaction, entree_id)
    if not entree:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    return remb.claims_for_entree(db, entree)
