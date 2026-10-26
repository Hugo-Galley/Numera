from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.loans import build_schedule, monthly_payment, remaining_principal, simulate_prepayment, terms_of
from app.db.session import get_db
from app.models.account import Account
from app.models.loan import Loan, LoanPrepayment
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

router = APIRouter(prefix="/loans", tags=["loans"])

ACCOUNT_FIELDS = ("name", "institution", "logo", "color")


def _get(db: Session, loan_id: int) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Crédit introuvable")
    return loan


def _summary(loan: Loan, today: date | None = None) -> LoanSummary:
    today = today or date.today()
    terms, prepayments = terms_of(loan)
    rows = build_schedule(terms, prepayments)
    remaining = remaining_principal(terms, prepayments, today)
    upcoming = next((row for row in rows if row.date > today), None)
    current_payment = upcoming.payment if upcoming else monthly_payment(terms.principal, terms.annual_rate_pct, terms.duration_months)
    total_interest = round(sum(row.interest for row in rows), 2)
    total_insurance = round(sum(row.insurance for row in rows), 2)
    account = loan.account
    return LoanSummary(
        id=loan.id, account_id=loan.account_id, name=account.name, institution=account.institution,
        logo=account.logo, color=account.color, kind=loan.kind, principal=loan.principal,
        annual_rate_pct=loan.annual_rate_pct, duration_months=loan.duration_months, start_date=loan.start_date,
        insurance_monthly=loan.insurance_monthly, monthly_payment=current_payment, remaining_principal=remaining,
        repaid_pct=round((1 - remaining / loan.principal) * 100, 2) if loan.principal else 0.0,
        end_date=rows[-1].date if rows else loan.start_date, total_interest=total_interest,
        total_insurance=total_insurance, total_cost=round(total_interest + total_insurance, 2),
        prepayments=[PrepaymentRead.model_validate(p) for p in loan.prepayments],
    )


@router.get("", response_model=list[LoanSummary])
def list_loans(db: Session = Depends(get_db)):
    return [_summary(loan) for loan in db.query(Loan).order_by(Loan.id.asc()).all()]


@router.post("", response_model=LoanSummary, status_code=201)
def create_loan(payload: LoanCreate, db: Session = Depends(get_db)):
    """Crée le compte `credit` et son prêt ensemble ; la valeur du compte est −capital restant dû."""
    data = payload.model_dump()
    account = Account(type="credit", currency="EUR", active=True, **{f: data.pop(f) for f in ACCOUNT_FIELDS})
    db.add(account)
    db.flush()
    loan = Loan(account_id=account.id, **data)
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return _summary(loan)


@router.get("/by-account/{account_id}", response_model=LoanSummary)
def get_loan_by_account(account_id: int, db: Session = Depends(get_db)):
    loan = db.query(Loan).filter(Loan.account_id == account_id).first()
    if loan is None:
        raise HTTPException(status_code=404, detail="Crédit introuvable")
    return _summary(loan)


@router.get("/{loan_id}", response_model=LoanSummary)
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    return _summary(_get(db, loan_id))


@router.patch("/{loan_id}", response_model=LoanSummary)
def update_loan(loan_id: int, payload: LoanUpdate, db: Session = Depends(get_db)):
    loan = _get(db, loan_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field in ACCOUNT_FIELDS:
            if field == "name" and value is None:
                continue
            setattr(loan.account, field, value)
        elif value is not None:  # colonnes non nullables : `null` = ne pas modifier
            setattr(loan, field, value)
    db.commit()
    db.refresh(loan)
    return _summary(loan)


@router.delete("/{loan_id}", status_code=204)
def delete_loan(loan_id: int, db: Session = Depends(get_db)):
    """Supprime le prêt, ses remboursements anticipés et son compte."""
    loan = _get(db, loan_id)
    db.delete(loan.account)
    db.commit()


@router.get("/{loan_id}/schedule", response_model=list[ScheduleRowRead])
def get_schedule(loan_id: int, db: Session = Depends(get_db)):
    terms, prepayments = terms_of(_get(db, loan_id))
    return [ScheduleRowRead(**row.__dict__) for row in build_schedule(terms, prepayments)]


@router.post("/{loan_id}/simulate-prepayment", response_model=SimulationResult)
def simulate(loan_id: int, payload: SimulationRequest, db: Session = Depends(get_db)):
    """Remboursement anticipé hypothétique : rien n'est enregistré."""
    terms, prepayments = terms_of(_get(db, loan_id))
    return SimulationResult(**simulate_prepayment(terms, prepayments, payload.amount, payload.date, payload.mode))


@router.post("/{loan_id}/prepayments", response_model=PrepaymentRead, status_code=201)
def add_prepayment(loan_id: int, payload: PrepaymentCreate, db: Session = Depends(get_db)):
    loan = _get(db, loan_id)
    prepayment = LoanPrepayment(loan_id=loan.id, **payload.model_dump())
    db.add(prepayment)
    db.commit()
    db.refresh(prepayment)
    return prepayment


@router.delete("/{loan_id}/prepayments/{prepayment_id}", status_code=204)
def delete_prepayment(loan_id: int, prepayment_id: int, db: Session = Depends(get_db)):
    prepayment = db.get(LoanPrepayment, prepayment_id)
    if prepayment is None or prepayment.loan_id != loan_id:
        raise HTTPException(status_code=404, detail="Remboursement anticipé introuvable")
    db.delete(prepayment)
    db.commit()
