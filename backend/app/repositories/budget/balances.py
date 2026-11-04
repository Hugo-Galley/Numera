from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def account_transactions_chronological(db: Session, account_id: int) -> list[Transaction]:
    """Transactions du compte par ordre chronologique (date puis id), pour le recalcul des soldes courants."""
    return (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
