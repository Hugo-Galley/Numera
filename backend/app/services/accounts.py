from datetime import date

from sqlalchemy.orm import Session

from app.core.loans import loan_remaining
from app.models.balance_snapshot import BalanceSnapshot
from app.models.transaction import Transaction


def account_balance(db: Session, account_id: int) -> float:
    """Solde = source la plus récente entre le dernier snapshot et la dernière transaction.

    Compte `credit` : −capital restant dû de son prêt à ce jour.
    """
    remaining = loan_remaining(db, account_id, date.today())
    if remaining is not None:
        return -remaining
    latest_snap = db.query(BalanceSnapshot).filter(
        BalanceSnapshot.account_id == account_id
    ).order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()).first()

    latest_tx = db.query(Transaction).filter(
        Transaction.account_id == account_id
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()

    if latest_snap and (not latest_tx or latest_snap.date >= latest_tx.date):
        return float(latest_snap.current_value)

    if latest_tx:
        return float(latest_tx.running_balance)

    return 0.0
