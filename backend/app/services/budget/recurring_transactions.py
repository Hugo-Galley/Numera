"""Récurrences : CRUD des règles ; chaque création/modification relance la génération immédiate."""
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.logging import get_logger
from app.models.recurring_transaction import RecurringTransaction
from app.repositories.budget import recurring as repo
from app.schemas.recurring_transaction import RecurringTransactionCreate, RecurringTransactionUpdate
from app.services.budget.recurring import generate_recurring_transactions

logger = get_logger(__name__)

_NOT_NULL_FIELDS = (
    "account_id", "name", "type", "amount", "currency", "frequency",
    "start_date", "is_active", "auto_generate",
)


def _validate_transfer_target(
    db: Session, account_id: int, type_: str, ticker: str | None, dest_id: int | None, credit_day: int | None = None
) -> None:
    """Une récurrence « virement » est une Sortie d'un compte non titres vers un autre compte."""
    if dest_id is None:
        if credit_day is not None:
            raise BusinessRuleError("A credit day requires a transfer destination")
        return
    source = repo.get_account(db, account_id)
    dest = repo.get_account(db, dest_id)
    if not dest:
        raise NotFoundError("Destination account not found")
    if dest_id == account_id:
        raise BusinessRuleError("Source and destination accounts must differ")
    if type_ != "Sortie":
        raise BusinessRuleError("A transfer recurrence must be a Sortie")
    if source and source.type == "investissement":
        raise BusinessRuleError("A transfer recurrence cannot come from a securities account")
    if ticker and dest.type != "investissement":
        raise BusinessRuleError("A security can only be bought through a transfer to an investment account")


def _require_account(db: Session, account_id: int) -> None:
    if repo.get_account(db, account_id) is None:
        raise NotFoundError("Account not found")


def _require(db: Session, rule_id: int) -> RecurringTransaction:
    rule = repo.get_rule(db, rule_id)
    if not rule:
        raise NotFoundError("Recurring transaction not found")
    return rule


def _months_csv(months: list[int] | None) -> str | None:
    """Mois exclus : liste d'entiers -> CSV stocké en base."""
    return ",".join(str(m) for m in months) if months is not None else None


async def _generate_now(db: Session, rule: RecurringTransaction) -> None:
    if not (rule.auto_generate and rule.is_active):
        return
    try:
        await generate_recurring_transactions(db)
        db.refresh(rule)
    except Exception:
        # La récurrence est créée ; la génération sera rejouée par la tâche de fond.
        db.rollback()
        logger.exception("Génération immédiate échouée pour la récurrence %s", rule.id)


async def trigger_generation(db: Session) -> int:
    return await generate_recurring_transactions(db)


async def read_recurring_transactions(db: Session, skip: int, limit: int, trigger: bool) -> list[RecurringTransaction]:
    if trigger:
        await generate_recurring_transactions(db)
    return repo.list_page(db, skip, limit)


async def create_recurring_transaction(db: Session, recurring_tx_in: RecurringTransactionCreate) -> RecurringTransaction:
    _require_account(db, recurring_tx_in.account_id)
    data = recurring_tx_in.model_dump()
    if data.get("excluded_months") is not None:
        data["excluded_months"] = _months_csv(data["excluded_months"])
    _validate_transfer_target(
        db, data["account_id"], data["type"], data.get("ticker"),
        data.get("transfer_to_account_id"), data.get("transfer_credit_day"),
    )
    rule = RecurringTransaction(**data)
    repo.add(db, rule)
    db.commit()
    db.refresh(rule)
    await _generate_now(db, rule)
    return rule


async def update_recurring_transaction(db: Session, recurring_tx_id: int,
                                       recurring_tx_in: RecurringTransactionUpdate) -> RecurringTransaction:
    rule = _require(db, recurring_tx_id)
    update_data = recurring_tx_in.model_dump(exclude_unset=True)
    # Colonnes NOT NULL : un `null` explicite est ignoré plutôt que de provoquer un 500
    for field in _NOT_NULL_FIELDS:
        if update_data.get(field, 0) is None:
            del update_data[field]
    if "account_id" in update_data:
        _require_account(db, update_data["account_id"])
    start = update_data.get("start_date", rule.start_date)
    end = update_data.get("end_date", rule.end_date)
    if start and end and end < start:
        raise BusinessRuleError("end_date doit être postérieure à start_date")
    if "excluded_months" in update_data:
        update_data["excluded_months"] = _months_csv(update_data["excluded_months"])
    _validate_transfer_target(
        db,
        update_data.get("account_id", rule.account_id),
        update_data.get("type", rule.type),
        update_data.get("ticker", rule.ticker),
        update_data.get("transfer_to_account_id", rule.transfer_to_account_id),
        update_data.get("transfer_credit_day", rule.transfer_credit_day),
    )
    for field, value in update_data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    await _generate_now(db, rule)
    return rule


def delete_recurring_transaction(db: Session, recurring_tx_id: int) -> dict:
    rule = _require(db, recurring_tx_id)
    repo.detach_rule(db, recurring_tx_id)
    repo.delete(db, rule)
    db.commit()
    return {"message": "Recurring transaction deleted"}
