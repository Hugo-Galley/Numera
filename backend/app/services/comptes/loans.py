"""Crédits : un crédit = un compte `credit` + une ligne `loans`, créés et supprimés ensemble."""
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.domain.loans import add_months, build_schedule, monthly_payment, remaining_principal, simulate_prepayment, terms_of
from app.models.account import Account
from app.models.loan import Loan, LoanPrepayment
from app.repositories.comptes import loans as repo
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

ACCOUNT_FIELDS = ("name", "institution", "logo", "color")


def loan_remaining(db: Session, account_id: int, at: date) -> float | None:
    """Capital restant dû du prêt d'un compte `credit`, ou None si le compte n'a pas de prêt.

    Avant le déblocage (pris un mois avant la première échéance) la dette n'existe pas encore : 0.
    """
    loan = repo.get_by_account(db, account_id)
    if loan is None:
        return None
    if at < add_months(loan.start_date, -1):
        return 0.0
    terms, prepayments = terms_of(loan)
    return remaining_principal(terms, prepayments, at)


def _get(db: Session, loan_id: int) -> Loan:
    loan = repo.get(db, loan_id)
    if loan is None:
        raise NotFoundError("Crédit introuvable")
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


def list_loans(db: Session) -> list[LoanSummary]:
    return [_summary(loan) for loan in repo.list_all(db)]


def create_loan(db: Session, payload: LoanCreate) -> LoanSummary:
    """Crée le compte `credit` et son prêt ensemble ; la valeur du compte est −capital restant dû."""
    data = payload.model_dump()
    account = Account(type="credit", currency="EUR", active=True, **{f: data.pop(f) for f in ACCOUNT_FIELDS})
    repo.add(db, account)
    loan = Loan(account_id=account.id, **data)
    repo.add(db, loan)
    db.commit()
    db.refresh(loan)
    return _summary(loan)


def get_loan_by_account(db: Session, account_id: int) -> LoanSummary:
    loan = repo.get_by_account(db, account_id)
    if loan is None:
        raise NotFoundError("Crédit introuvable")
    return _summary(loan)


def get_loan(db: Session, loan_id: int) -> LoanSummary:
    return _summary(_get(db, loan_id))


def update_loan(db: Session, loan_id: int, payload: LoanUpdate) -> LoanSummary:
    loan = _get(db, loan_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in ACCOUNT_FIELDS:
            if field == "name" and value is None:
                continue
            setattr(loan.account, field, value)
        elif value is not None:  # colonnes non nullables : `null` = ne pas modifier
            setattr(loan, field, value)
    db.commit()
    db.refresh(loan)
    return _summary(loan)


def delete_loan(db: Session, loan_id: int) -> None:
    """Supprime le prêt, ses remboursements anticipés et son compte."""
    repo.delete(db, _get(db, loan_id).account)
    db.commit()


def get_schedule(db: Session, loan_id: int) -> list[ScheduleRowRead]:
    terms, prepayments = terms_of(_get(db, loan_id))
    return [ScheduleRowRead(**row.__dict__) for row in build_schedule(terms, prepayments)]


def simulate(db: Session, loan_id: int, payload: SimulationRequest) -> SimulationResult:
    """Remboursement anticipé hypothétique : rien n'est enregistré."""
    terms, prepayments = terms_of(_get(db, loan_id))
    return SimulationResult(**simulate_prepayment(terms, prepayments, payload.amount, payload.date, payload.mode))


def add_prepayment(db: Session, loan_id: int, payload: PrepaymentCreate) -> LoanPrepayment:
    loan = _get(db, loan_id)
    prepayment = LoanPrepayment(loan_id=loan.id, **payload.model_dump())
    repo.add(db, prepayment)
    db.commit()
    db.refresh(prepayment)
    return prepayment


def delete_prepayment(db: Session, loan_id: int, prepayment_id: int) -> None:
    prepayment = repo.get_prepayment(db, prepayment_id)
    if prepayment is None or prepayment.loan_id != loan_id:
        raise NotFoundError("Remboursement anticipé introuvable")
    repo.delete(db, prepayment)
    db.commit()
