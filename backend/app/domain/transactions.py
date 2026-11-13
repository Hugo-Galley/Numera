"""Calculs purs sur les transactions (aucune Session)."""

from typing import Any

from app.models.transaction import Transaction
from app.schemas.transaction import TransactionRead


def net_amount(tx: Transaction) -> float:
    return float(tx.amount) - float(tx.reimbursement_offset or 0.0)


def tx_sample(tx: Transaction) -> dict[str, Any]:
    return {
        "id": tx.id,
        "account_id": tx.account_id,
        "date": tx.date.date().isoformat() if hasattr(tx.date, "date") else str(tx.date),
        "merchant": tx.merchant,
        "type": tx.type,
        "amount": round(float(tx.amount), 2),
        "currency": tx.currency,
    }


def tx_read(tx: Transaction) -> dict[str, Any]:
    return TransactionRead.model_validate(tx).model_dump(mode="json")


def category_share(amount: float, offset: float, split_part: float | None) -> float:
    """Montant net d'une dépense attribué à une catégorie.

    `split_part` : somme des parts de la dépense affectées à la catégorie (None si elle n'est pas découpée,
    ou si aucune catégorie n'est filtrée) ; le net des remboursements est réparti au prorata des parts.
    """
    net = amount - offset
    if split_part is None:
        return net
    return net * split_part / amount if amount else 0.0
