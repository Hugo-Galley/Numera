from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.reimbursement import (
    AllocationCreate,
    CandidateRead,
    ClaimCreate,
    ClaimRead,
    ClaimUpdate,
    EntryClaims,
    ReimbursementSummary,
)
from app.services.budget import reimbursements as remb

router = APIRouter(prefix="/reimbursements", tags=["reimbursements"])


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
    return remb.create_claim_view(db, payload)


@router.patch("/claims/{claim_id}", response_model=ClaimRead)
def update_claim(claim_id: int, payload: ClaimUpdate, db: Session = Depends(get_db)):
    return remb.update_claim_view(db, claim_id, payload)


@router.delete("/claims/{claim_id}", status_code=204)
def delete_claim(claim_id: int, db: Session = Depends(get_db)):
    remb.delete_claim(db, remb.require_claim(db, claim_id))


@router.get("/claims/{claim_id}/candidates", response_model=list[CandidateRead])
def claim_candidates(claim_id: int, db: Session = Depends(get_db)):
    return remb.candidates(db, remb.require_claim(db, claim_id))


@router.post("/claims/{claim_id}/allocations", response_model=ClaimRead)
def allocate(claim_id: int, payload: AllocationCreate, db: Session = Depends(get_db)):
    return remb.allocate_view(db, claim_id, payload)


@router.delete("/allocations/{allocation_id}", status_code=204)
def remove_allocation(allocation_id: int, db: Session = Depends(get_db)):
    remb.remove_allocation(db, remb.require_allocation(db, allocation_id))


@router.get("/entries/{entree_id}/claims", response_model=EntryClaims)
def entry_claims(entree_id: int, db: Session = Depends(get_db)):
    return remb.claims_for_entree(db, remb.get_transaction(db, entree_id))
