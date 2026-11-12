from sqlalchemy.orm import Session

from app.domain.finance import apply_transaction_to_balance
from app.repositories.budget import balances as repo


def recalculate_running_balances(db: Session, account_id: int) -> None:
    """Recalcule les soldes courants du compte par ordre chronologique. Ne commit pas : l'appelant porte la transaction.

    Lecture par colonnes et mise à jour en masse des seules lignes dont le solde change."""
    current_balance = 0.0
    changed: list[tuple[int, float]] = []
    for tx_id, tx_type, amount, stored in repo.account_ledger_chronological(db, account_id):
        current_balance = apply_transaction_to_balance(current_balance, tx_type, amount)
        if stored != current_balance:
            changed.append((tx_id, current_balance))
    repo.update_running_balances(db, account_id, changed)
