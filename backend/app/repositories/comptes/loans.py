from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.loan import Loan, LoanPrepayment


def list_all(db: Session) -> list[Loan]:
    return db.query(Loan).order_by(Loan.id.asc()).all()


def get(db: Session, loan_id: int) -> Loan | None:
    return db.get(Loan, loan_id)


def get_by_account(db: Session, account_id: int) -> Loan | None:
    return db.query(Loan).filter(Loan.account_id == account_id).first()


def get_prepayment(db: Session, prepayment_id: int) -> LoanPrepayment | None:
    return db.get(LoanPrepayment, prepayment_id)


def add(db: Session, obj: Account | Loan | LoanPrepayment) -> None:
    db.add(obj)
    db.flush()


def delete(db: Session, obj: Account | LoanPrepayment) -> None:
    db.delete(obj)
