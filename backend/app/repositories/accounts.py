from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.transaction import Transaction


def list_all(db: Session) -> list[Account]:
    return db.query(Account).order_by(Account.id.asc()).all()


def get(db: Session, account_id: int) -> Account | None:
    return db.query(Account).filter(Account.id == account_id).first()


def add(db: Session, account: Account) -> None:
    db.add(account)
    db.flush()


def clear_main_flag(db: Session, except_id: int) -> None:
    """Un seul compte principal : retire le drapeau à tous les autres."""
    db.query(Account).filter(Account.id != except_id).update({"is_main": False})


def latest_snapshot(db: Session, account_id: int) -> BalanceSnapshot | None:
    return db.query(BalanceSnapshot).filter(
        BalanceSnapshot.account_id == account_id
    ).order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()).first()


def latest_transaction(db: Session, account_id: int) -> Transaction | None:
    return db.query(Transaction).filter(
        Transaction.account_id == account_id
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
