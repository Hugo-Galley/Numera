from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot


def list_for(db: Session, account_id: int | None) -> list[BalanceSnapshot]:
    query = db.query(BalanceSnapshot)
    if account_id is not None:
        query = query.filter(BalanceSnapshot.account_id == account_id)
    return query.order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc()).all()


def get(db: Session, snapshot_id: int) -> BalanceSnapshot | None:
    return db.query(BalanceSnapshot).filter(BalanceSnapshot.id == snapshot_id).first()


def get_account(db: Session, account_id: int) -> Account | None:
    return db.query(Account).filter(Account.id == account_id).first()


def latest(db: Session, account_id: int) -> BalanceSnapshot | None:
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )


def clear_zero_points(db: Session, account_id: int, except_id: int | None = None) -> None:
    """Retire le drapeau point zéro des relevés du compte (un seul point zéro par compte)."""
    query = db.query(BalanceSnapshot).filter(
        BalanceSnapshot.account_id == account_id,
        BalanceSnapshot.is_zero_point.is_(True),
    )
    if except_id is not None:
        query = query.filter(BalanceSnapshot.id != except_id)
    for snapshot in query:
        snapshot.is_zero_point = False


def add(db: Session, snapshot: BalanceSnapshot) -> None:
    db.add(snapshot)
    db.flush()


def delete(db: Session, snapshot: BalanceSnapshot) -> None:
    db.delete(snapshot)
