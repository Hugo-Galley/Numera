"""Virements internes saisis à la main : contrepartie, liaison, déliaison, suggestions écartées."""
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, InvalidOperationError, NotFoundError
from app.models.transaction import Transaction
from app.repositories import accounts as account_repo
from app.repositories import transactions as repo
from app.schemas.transaction import TransferCounterpartCreate, TransferCounterpartRead
from app.services import reimbursements as remb
from app.services.balances import recalculate_running_balances
from app.services.transactions import require
from app.services.transfers import create_counterpart, link_pair, unlink_pair

REIMBURSED_CANNOT_TRANSFER = "Une transaction qui porte des remboursements ne peut pas être un virement interne"


async def create_transfer_counterpart(db: Session, transaction_id: int, payload: TransferCounterpartCreate) -> TransferCounterpartRead:
    """Crée la contrepartie manquante d'une sortie sur un autre compte et la relie."""
    tx = require(db, transaction_id)
    if tx.type != "Sortie":
        raise BusinessRuleError("Only a Sortie can get a counterpart")
    if remb.has_reimbursement(db, tx.id):
        raise InvalidOperationError(REIMBURSED_CANNOT_TRANSFER)
    dest = account_repo.get(db, payload.account_id)
    if not dest:
        raise NotFoundError("Account not found")
    if dest.id == tx.account_id:
        raise BusinessRuleError("Destination must be another account")

    leg, kind = await create_counterpart(db, tx, dest, date=payload.date, amount=payload.amount)
    db.commit()
    if kind == "regular":
        recalculate_running_balances(db, dest.id)
        db.commit()
    return TransferCounterpartRead(id=leg.id, type=kind)


def link_transactions(db: Session, transaction_id: int, other_id: int, type: str) -> dict:
    tx1 = require(db, transaction_id)
    if type not in ("regular", "investment"):
        raise BusinessRuleError("type must be 'regular' or 'investment'")
    if type == "regular" and other_id == transaction_id:
        raise BusinessRuleError("A transaction cannot be linked to itself")
    if type == "regular":
        other = repo.get(db, other_id)
        if not other:
            raise NotFoundError("Secondary transaction not found")
    else:
        other = repo.get_investment(db, other_id)
        if not other:
            raise NotFoundError("Investment transaction not found")

    if remb.has_reimbursement(db, tx1.id) or (type == "regular" and remb.has_reimbursement(db, other.id)):
        raise InvalidOperationError(REIMBURSED_CANNOT_TRANSFER)
    link_pair(db, tx1, other, type, "manual")
    db.commit()
    return {"status": "ok"}


def ignore_transfer(db: Session, transaction_id: int, other_id: int | None, type: str) -> None:
    """Écarte une suggestion de virement. Avec `other_id`, la ligne en face est écartée aussi."""
    tx = require(db, transaction_id)
    tx.is_transfer_ignored = True
    if other_id is not None:
        other = repo.get_investment(db, other_id) if type == "investment" else repo.get(db, other_id)
        if other:
            other.is_transfer_ignored = True
    db.commit()


def ignore_duplicate(db: Session, transaction_id: int) -> None:
    require(db, transaction_id).is_duplicate_ignored = True
    db.commit()


def unlink_transaction(db: Session, transaction_id: int) -> Transaction:
    tx = require(db, transaction_id)
    unlink_pair(db, tx)
    db.commit()
    db.refresh(tx)
    return tx
