from datetime import date

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.financial_event import FinancialEvent


def list_between(db: Session, start: date | None, end: date | None, account_id: int | None) -> list[FinancialEvent]:
    """Du plus récent au plus ancien, bornes incluses."""
    query = db.query(FinancialEvent)
    if start:
        query = query.filter(FinancialEvent.date >= start)
    if end:
        query = query.filter(FinancialEvent.date <= end)
    if account_id is not None:
        query = query.filter(FinancialEvent.account_id == account_id)
    return query.order_by(FinancialEvent.date.desc(), FinancialEvent.id.desc()).all()


def get(db: Session, event_id: int) -> FinancialEvent | None:
    return db.get(FinancialEvent, event_id)


def account_exists(db: Session, account_id: int) -> bool:
    return db.get(Account, account_id) is not None


def add(db: Session, event: FinancialEvent) -> None:
    db.add(event)
    db.flush()


def delete(db: Session, event: FinancialEvent) -> None:
    db.delete(event)
