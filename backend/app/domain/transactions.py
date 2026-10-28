"""Calculs purs sur les transactions (aucune Session)."""
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionRead


def net_amount(tx: Transaction) -> float:
    return float(tx.amount) - float(tx.reimbursement_offset or 0.0)


def tx_sample(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "account_id": tx.account_id,
        "date": tx.date.date().isoformat() if hasattr(tx.date, "date") else str(tx.date),
        "merchant": tx.merchant,
        "type": tx.type,
        "amount": round(float(tx.amount), 2),
        "currency": tx.currency,
    }


def tx_read(tx: Transaction) -> dict:
    return TransactionRead.model_validate(tx).model_dump(mode="json")
