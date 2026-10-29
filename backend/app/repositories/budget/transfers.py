from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.budget.reimbursements import locked_transaction_ids
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.models.transfer_rule import TransferRule


def accounts_by_id(db: Session) -> dict[int, Account]:
    return {a.id: a for a in db.query(Account).all()}


def unlinked_sorties(db: Session, source_account_id: int | None, since: datetime | None) -> list[Transaction]:
    """Sorties ni liées, ni ignorées, ni verrouillées par une créance."""
    q = db.query(Transaction).filter(
        Transaction.type == "Sortie",
        Transaction.is_transfer.is_(False),
        Transaction.is_transfer_ignored.is_(False),
        Transaction.linked_transaction_id.is_(None),
        Transaction.linked_investment_transaction_id.is_(None),
        Transaction.id.notin_(locked_transaction_ids()),
    )
    if source_account_id is not None:
        q = q.filter(Transaction.account_id == source_account_id)
    if since:
        q = q.filter(Transaction.date >= since)
    return q.all()


def unlinked_entrees(db: Session, dest_account_id: int | None, date_floor: datetime | None) -> list[Transaction]:
    q = db.query(Transaction).filter(
        Transaction.type == "Entree",
        Transaction.is_transfer.is_(False),
        Transaction.is_transfer_ignored.is_(False),
        Transaction.linked_transaction_id.is_(None),
        Transaction.id.notin_(locked_transaction_ids()),
    )
    if dest_account_id is not None:
        q = q.filter(Transaction.account_id == dest_account_id)
    if date_floor:
        q = q.filter(Transaction.date >= date_floor)
    return q.all()


def unlinked_versements(db: Session, dest_account_id: int | None, date_floor: datetime | None) -> list[InvestmentTransaction]:
    q = db.query(InvestmentTransaction).filter(
        InvestmentTransaction.type == "versement",
        InvestmentTransaction.is_transfer.is_(False),
        InvestmentTransaction.is_transfer_ignored.is_(False),
        InvestmentTransaction.linked_transaction_id.is_(None),
    )
    if dest_account_id is not None:
        q = q.filter(InvestmentTransaction.account_id == dest_account_id)
    if date_floor:
        q = q.filter(InvestmentTransaction.date >= date_floor)
    return q.all()


def active_rules(db: Session, rule_ids: list[int] | None) -> list[TransferRule]:
    q = db.query(TransferRule).filter(TransferRule.is_active.is_(True))
    if rule_ids:
        q = q.filter(TransferRule.id.in_(rule_ids))
    return q.order_by(TransferRule.id).all()


def is_locked(db: Session, transaction_id: int) -> bool:
    return db.query(Transaction.id).filter(
        Transaction.id == transaction_id, Transaction.id.in_(locked_transaction_ids())
    ).first() is not None


def legs_near(db: Session, model, type_: str, exclude_account_id: int, low: datetime, high: datetime,
              account_id: int | None) -> list:
    """Opérations non liées d'un type donné, hors du compte `exclude_account_id`, entre `low` et `high`."""
    q = db.query(model).filter(
        model.type == type_, model.is_transfer.is_(False),
        model.account_id != exclude_account_id, model.date >= low, model.date <= high,
    )
    if account_id is not None:
        q = q.filter(model.account_id == account_id)
    if model is Transaction:
        q = q.filter(Transaction.id.notin_(locked_transaction_ids()))
    return q.all()
