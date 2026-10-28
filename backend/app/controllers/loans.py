from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.loan import (
    LoanCreate,
    LoanSummary,
    LoanUpdate,
    PrepaymentCreate,
    PrepaymentRead,
    ScheduleRowRead,
    SimulationRequest,
    SimulationResult,
)
from app.services import loans as service

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("", response_model=list[LoanSummary])
def list_loans(db: Session = Depends(get_db)):
    return service.list_loans(db)


@router.post("", response_model=LoanSummary, status_code=201)
def create_loan(payload: LoanCreate, db: Session = Depends(get_db)):
    """Crée le compte `credit` et son prêt ensemble ; la valeur du compte est −capital restant dû."""
    return service.create_loan(db, payload)


@router.get("/by-account/{account_id}", response_model=LoanSummary)
def get_loan_by_account(account_id: int, db: Session = Depends(get_db)):
    return service.get_loan_by_account(db, account_id)


@router.get("/{loan_id}", response_model=LoanSummary)
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    return service.get_loan(db, loan_id)


@router.patch("/{loan_id}", response_model=LoanSummary)
def update_loan(loan_id: int, payload: LoanUpdate, db: Session = Depends(get_db)):
    return service.update_loan(db, loan_id, payload)


@router.delete("/{loan_id}", status_code=204)
def delete_loan(loan_id: int, db: Session = Depends(get_db)):
    """Supprime le prêt, ses remboursements anticipés et son compte."""
    service.delete_loan(db, loan_id)


@router.get("/{loan_id}/schedule", response_model=list[ScheduleRowRead])
def get_schedule(loan_id: int, db: Session = Depends(get_db)):
    return service.get_schedule(db, loan_id)


@router.post("/{loan_id}/simulate-prepayment", response_model=SimulationResult)
def simulate(loan_id: int, payload: SimulationRequest, db: Session = Depends(get_db)):
    """Remboursement anticipé hypothétique : rien n'est enregistré."""
    return service.simulate(db, loan_id, payload)


@router.post("/{loan_id}/prepayments", response_model=PrepaymentRead, status_code=201)
def add_prepayment(loan_id: int, payload: PrepaymentCreate, db: Session = Depends(get_db)):
    return service.add_prepayment(db, loan_id, payload)


@router.delete("/{loan_id}/prepayments/{prepayment_id}", status_code=204)
def delete_prepayment(loan_id: int, prepayment_id: int, db: Session = Depends(get_db)):
    service.delete_prepayment(db, loan_id, prepayment_id)
