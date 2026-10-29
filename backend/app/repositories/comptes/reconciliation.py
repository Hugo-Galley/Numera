from datetime import datetime

from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def last_before(db: Session, account_id: int, end: datetime) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id, Transaction.date < end)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .first()
    )


def window(db: Session, account_id: int, start: datetime, end: datetime) -> list[Transaction]:
    """Transactions du compte dans [start, end), hors Solde Initial, de la plus récente à la plus ancienne."""
    return (
        db.query(Transaction)
        .filter(
            Transaction.account_id == account_id,
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type != "Solde Initial",
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .all()
    )
