from datetime import datetime
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionRead

logger = get_logger(__name__)


def _tx_sample(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "account_id": tx.account_id,
        "date": tx.date.date().isoformat() if hasattr(tx.date, "date") else str(tx.date),
        "merchant": tx.merchant,
        "type": tx.type,
        "amount": round(float(tx.amount), 2),
        "currency": tx.currency,
    }


def _tx_read(tx: Transaction) -> dict:
    return TransactionRead.model_validate(tx).model_dump(mode="json")


def _savings_account_ids(db: Session) -> list[int]:
    return [acc.id for acc in db.query(Account).filter(Account.type == "epargne", Account.active.is_(True)).all()]


def _savings_events_by_account(db: Session, account_ids: list[int], end_date: datetime) -> dict[int, list[tuple[datetime, int, float]]]:
    events: dict[int, list[tuple[datetime, int, float]]] = {acc_id: [] for acc_id in account_ids}
    if not account_ids:
        return events

    snapshots = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id.in_(account_ids), BalanceSnapshot.date <= end_date)
        .order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc())
        .all()
    )
    for snap in snapshots:
        events[snap.account_id].append((snap.date, 1, float(snap.current_value)))

    transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids), Transaction.date <= end_date)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
    for tx in transactions:
        events[tx.account_id].append((tx.date, 0, float(tx.running_balance)))

    for acc_id, items in events.items():
        items.sort(key=lambda item: (item[0], item[1]))
        events[acc_id] = items
    return events


def _savings_total_at(db: Session, account_ids: list[int], end_date: datetime) -> float:
    events = _savings_events_by_account(db, account_ids, end_date)
    total = 0.0
    for items in events.values():
        total += items[-1][2] if items else 0.0
    return total


def _get_ticket_restaurant_account_ids(db: Session) -> set[int]:
    from app.models.salary_config import SalaryConfig
    ticket_account_ids = set()
    try:
        salary_config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
        if salary_config and salary_config.ticket_account_id:
            ticket_account_ids.add(salary_config.ticket_account_id)
            
        matching_accounts = db.query(Account.id).filter(
            (Account.name.ilike("%ticket%restaurant%")) | 
            (Account.name.ilike("%tickets%restaurant%")) |
            (Account.type == "ticket_restaurant")
        ).all()
        for acc_id_tuple in matching_accounts:
            ticket_account_ids.add(acc_id_tuple[0])
    except Exception as e:
        logger.warning(f"Error getting ticket restaurant accounts: {e}")
        
    return ticket_account_ids
