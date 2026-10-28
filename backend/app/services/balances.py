from sqlalchemy.orm import Session

from app.core.finance import apply_transaction_to_balance
from app.models.transaction import Transaction


def recalculate_running_balances(db: Session, account_id: int):
    """Recalculate running balances for all transactions of an account in chronological order."""
    transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
    
    current_balance = 0.0
    for tx in transactions:
        current_balance = apply_transaction_to_balance(current_balance, tx.type, tx.amount)
        tx.running_balance = current_balance
    
    db.commit()
