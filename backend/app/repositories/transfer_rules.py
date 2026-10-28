from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transfer_rule import TransferRule


def list_all(db: Session) -> list[TransferRule]:
    return db.query(TransferRule).order_by(TransferRule.id).all()


def get(db: Session, rule_id: int) -> TransferRule | None:
    return db.get(TransferRule, rule_id)


def existing_account_ids(db: Session, account_ids: list[int]) -> set[int]:
    return {a.id for a in db.query(Account.id).filter(Account.id.in_(account_ids)).all()}


def add(db: Session, rule: TransferRule) -> None:
    db.add(rule)
    db.flush()


def delete(db: Session, rule: TransferRule) -> None:
    db.delete(rule)
