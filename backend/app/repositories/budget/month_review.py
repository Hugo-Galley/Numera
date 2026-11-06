from sqlalchemy.orm import Session

from app.models.month_closure import MonthClosure


def get_closure(db: Session, year: int, month: int) -> MonthClosure | None:
    return db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).first()


def delete_closure(db: Session, year: int, month: int) -> None:
    db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).delete()


def list_closures(db: Session) -> list[MonthClosure]:
    return db.query(MonthClosure).order_by(MonthClosure.year.desc(), MonthClosure.month.desc()).all()
