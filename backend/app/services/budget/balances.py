from sqlalchemy.orm import Session

from app.domain.finance import apply_transaction_to_balance
from app.repositories.budget import balances as repo


def recalculate_running_balances(db: Session, account_id: int):
    """Recalcule les soldes courants du compte par ordre chronologique. Ne commit pas : l'appelant porte la transaction."""
    current_balance = 0.0
    for tx in repo.account_transactions_chronological(db, account_id):
        current_balance = apply_transaction_to_balance(current_balance, tx.type, tx.amount)
        tx.running_balance = current_balance
    db.flush()
