from collections import Counter

from sqlalchemy.orm import Session

from app.domain.csv_import import duplicate_key
from app.models.category import Category
from app.models.import_log import ImportLog
from app.models.transaction import Transaction


def recent_logs(db: Session, limit: int) -> list[ImportLog]:
    return db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(limit).all()


def categories_by_name(db: Session) -> dict[str, Category]:
    return {c.name: c for c in db.query(Category).all()}


def existing_keys(db: Session, account_id: int) -> Counter:
    """Occurrences de chaque clé de doublon déjà présente dans le compte (import idempotent)."""
    return Counter(
        duplicate_key(tx.date, tx.amount, tx.merchant, tx.type)
        for tx in db.query(Transaction.date, Transaction.amount, Transaction.merchant, Transaction.type)
        .filter(Transaction.account_id == account_id)
        .all()
    )


def has_initial_balance(db: Session, account_id: int) -> bool:
    return (
        db.query(Transaction.id)
        .filter(Transaction.account_id == account_id, Transaction.type == "Solde Initial")
        .first()
        is not None
    )


def add(db: Session, obj: Category | Transaction | ImportLog) -> None:
    db.add(obj)
    db.flush()
