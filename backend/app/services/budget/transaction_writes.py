"""Transactions : création, modification, suppression (unitaire ou groupée) et découpage.

Toute mutation recalcule intégralement les soldes du ou des comptes touchés.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.integrations import currency as currency_module
from app.core.errors import BusinessRuleError, NotFoundError
from app.domain.finance import month_label_from_date, normalize_transaction_type
from app.core.time import utcnow_naive
from app.models.account import Account
from app.models.transaction import Transaction
from app.repositories.comptes import accounts as account_repo
from app.repositories.budget import transactions as repo
from app.schemas.transaction import (
    TransactionBulkDelete, TransactionBulkDeleteResult, TransactionBulkUpdate, TransactionCreate,
    TransactionSplitsUpdate, TransactionUpdate,
)
from app.services.budget import reimbursements as remb
from app.services.budget.balances import recalculate_running_balances
from app.services.budget.splits import check_split_compatible, set_splits
from app.services.budget.transactions import require
from app.services.budget.transfers import auto_link_transfers, release_partner


def validate_solde_initial(db: Session, account_id: int, date: datetime, exclude_id: int | None = None) -> None:
    """Un compte n'a qu'un seul Solde Initial et il doit être la première transaction
    (il remet le solde à zéro à sa date, cf. apply_transaction_to_balance)."""
    if repo.other_initial_balance(db, account_id, exclude_id):
        raise BusinessRuleError("A Solde Initial already exists for this account")
    earliest = repo.earliest_other(db, account_id, exclude_id)
    if earliest and date >= earliest.date:
        raise BusinessRuleError("Solde Initial must be the chronologically first transaction")


def _normalized_type(value: str) -> str:
    try:
        return normalize_transaction_type(value)
    except ValueError as exc:
        raise BusinessRuleError(str(exc)) from exc


async def _in_account_currency(db: Session, account: Account, amount: float, currency: str, date: datetime) -> float:
    if currency == account.currency:
        return amount
    return await currency_module.convert_amount(amount=amount, from_currency=currency, to_currency=account.currency, date=date.date(), db=db)


async def create_transaction(db: Session, payload: TransactionCreate) -> Transaction:
    account = account_repo.get(db, payload.account_id)
    if not account:
        raise NotFoundError("Account not found")
    transaction_type = _normalized_type(payload.type)
    if transaction_type == "Solde Initial":
        validate_solde_initial(db, payload.account_id, payload.date)

    currency = payload.currency or account.currency
    transaction = Transaction(
        account_id=payload.account_id,
        date=payload.date,
        month_label=month_label_from_date(payload.date),
        type=transaction_type,
        merchant=payload.merchant,
        category_id=payload.category_id,
        amount=await _in_account_currency(db, account, payload.amount, currency, payload.date),
        currency=currency,
        original_amount=payload.amount,
        running_balance=0.0,  # recalculé ci-dessous
        note=payload.note,
        is_exceptional=payload.is_exceptional and transaction_type == "Sortie",
        merchant_id=payload.merchant_id,
        is_recurring=payload.is_recurring,
        custom_icon=payload.custom_icon,
        custom_color=payload.custom_color,
    )
    if payload.tag_ids:
        transaction.tags = repo.tags_by_ids(db, payload.tag_ids)
    db.add(transaction)
    account.last_verified_at = utcnow_naive()
    db.commit()

    recalculate_running_balances(db, payload.account_id)
    db.commit()
    await auto_link_transfers(db)
    db.refresh(transaction)
    return transaction


def _bulk_type(payload: TransactionBulkUpdate, transactions: list[Transaction], db: Session) -> str | None:
    if payload.type is None:
        return None
    bulk_type = _normalized_type(payload.type)
    if bulk_type == "Solde Initial":
        raise BusinessRuleError("Solde Initial cannot be set through bulk update")
    if any(tx.type == "Solde Initial" for tx in transactions):
        raise BusinessRuleError("A Solde Initial transaction cannot be bulk-retyped")
    for tx in transactions:
        remb.check_transaction_change(db, tx, bulk_type, tx.amount, False)
        check_split_compatible(tx, bulk_type, tx.amount, tx.is_transfer)
    return bulk_type


async def bulk_update_transactions(db: Session, payload: TransactionBulkUpdate) -> None:
    if not payload.ids:
        return
    transactions = repo.get_many(db, payload.ids)
    if not transactions:
        return
    bulk_type = _bulk_type(payload, transactions, db)
    tags = repo.tags_by_ids(db, payload.tag_ids) if payload.tag_ids is not None else []

    affected_account_ids = set()
    for tx in transactions:
        if payload.category_id is not None:
            tx.category_id = payload.category_id
            tx.splits = []  # recatégoriser en masse remplace le découpage
        if payload.is_recurring is not None:
            tx.is_recurring = payload.is_recurring
        if bulk_type is not None:
            tx.type = bulk_type
        if payload.merchant is not None:
            tx.merchant = payload.merchant
        if payload.merchant_id is not None:
            tx.merchant_id = payload.merchant_id
        if payload.tag_ids is not None:
            tx.tags = tags
        affected_account_ids.add(tx.account_id)
    db.commit()
    for account_id in affected_account_ids:
        recalculate_running_balances(db, account_id)
    db.commit()


def _delete(db: Session, transactions: list[Transaction]) -> None:
    """Délie virements et remboursements, supprime, resynchronise l'autre côté des remboursements."""
    deleted_ids = {tx.id for tx in transactions}
    others: set[int] = set()
    for tx in transactions:
        release_partner(db, tx)  # le partenaire ne doit pas rester marqué is_transfer sans lien
        others |= remb.detach_before_delete(db, tx)
    # Les FK des bases migrées n'ont pas de ON DELETE SET NULL : les liens doivent être nuls en base avant les DELETE
    db.flush()
    for tx in transactions:
        repo.delete(db, tx)
    remb.sync_offsets(db, others - deleted_ids)
    db.commit()


def bulk_delete_transactions(db: Session, payload: TransactionBulkDelete) -> TransactionBulkDeleteResult:
    """Supprime plusieurs transactions dans une seule transaction SQL, puis recalcule
    une fois les soldes de chaque compte (des DELETE parallèles se marchent dessus)."""
    transactions = repo.get_many(db, payload.ids)
    affected_account_ids = {tx.account_id for tx in transactions}
    _delete(db, transactions)
    for account_id in affected_account_ids:
        recalculate_running_balances(db, account_id)
    db.commit()
    return TransactionBulkDeleteResult(deleted=len(transactions))


def delete_transaction(db: Session, transaction_id: int) -> None:
    transaction = require(db, transaction_id)
    account_id = transaction.account_id
    _delete(db, [transaction])
    recalculate_running_balances(db, account_id)
    db.commit()


def update_transaction_splits(db: Session, transaction_id: int, payload: TransactionSplitsUpdate) -> Transaction:
    """Découpe une dépense entre plusieurs catégories (liste vide = annuler le découpage)."""
    transaction = require(db, transaction_id)
    set_splits(db, transaction, payload.items)
    db.commit()
    db.refresh(transaction)
    return transaction


async def _apply_amount_change(db: Session, transaction: Transaction, account: Account, update_data: dict) -> None:
    """Reconvertit le montant si le montant, la devise ou la date changent."""
    if not ("amount" in update_data or "currency" in update_data or "date" in update_data):
        return
    original_amount = update_data.get("amount", transaction.original_amount)
    currency = update_data.get("currency", transaction.currency)
    date = update_data.get("date", transaction.date)
    update_data["amount"] = await _in_account_currency(db, account, original_amount, currency, date)
    update_data["original_amount"] = original_amount
    update_data["currency"] = currency


def _apply_tags(db: Session, transaction: Transaction, update_data: dict) -> None:
    if "tag_ids" in update_data:
        tag_ids = update_data.pop("tag_ids")
        transaction.tags = repo.tags_by_ids(db, tag_ids) if tag_ids is not None else []


def _check_change(db: Session, transaction: Transaction, update_data: dict) -> None:
    new_type = update_data.get("type", transaction.type)
    new_amount = update_data.get("amount", transaction.amount)
    remb.check_transaction_change(db, transaction, new_type, new_amount, bool(update_data.get("is_transfer")))
    check_split_compatible(transaction, new_type, new_amount, bool(update_data.get("is_transfer", transaction.is_transfer)))
    if transaction.splits and "category_id" in update_data and update_data["category_id"] != transaction.category_id:
        transaction.splits = []  # choisir une seule catégorie annule le découpage


async def update_transaction(db: Session, transaction_id: int, payload: TransactionUpdate) -> Transaction:
    transaction = require(db, transaction_id)
    account = account_repo.get(db, transaction.account_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "type" in update_data:
        update_data["type"] = _normalized_type(update_data["type"])
    if "date" in update_data:
        update_data["month_label"] = month_label_from_date(update_data["date"])
    new_type = update_data.get("type", transaction.type)
    if new_type == "Solde Initial" and ("type" in update_data or "date" in update_data):
        validate_solde_initial(db, transaction.account_id, update_data.get("date", transaction.date), exclude_id=transaction.id)

    await _apply_amount_change(db, transaction, account, update_data)
    _apply_tags(db, transaction, update_data)
    _check_change(db, transaction, update_data)
    # La colonne n'est pas nullable : un `null` explicite équivaut à « ne pas modifier »
    if update_data.get("is_exceptional", True) is None:
        update_data.pop("is_exceptional")
    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    recalculate_running_balances(db, transaction.account_id)
    db.commit()
    await auto_link_transfers(db)
    db.refresh(transaction)
    return transaction
