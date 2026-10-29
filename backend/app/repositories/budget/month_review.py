from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.month_closure import MonthClosure


def active_accounts(db: Session) -> list[Account]:
    return db.query(Account).filter(Account.active.is_(True)).order_by(Account.id.asc()).all()


def get_closure(db: Session, year: int, month: int) -> MonthClosure | None:
    return db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).first()


def delete_closure(db: Session, year: int, month: int) -> None:
    db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).delete()


def list_closures(db: Session) -> list[MonthClosure]:
    return db.query(MonthClosure).order_by(MonthClosure.year.desc(), MonthClosure.month.desc()).all()
