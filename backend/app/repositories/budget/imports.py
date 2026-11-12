from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.domain.csv_import import duplicate_key
from app.models.category import Category
from app.models.import_log import ImportLog
from app.models.transaction import Transaction


def recent_logs(db: Session, limit: int) -> list[ImportLog]:
    return db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(limit).all()


def categories_by_name(db: Session) -> dict[str, Category]:
    return {c.name: c for c in db.query(Category).all()}


def existing_keys(db: Session, account_id: int) -> Counter[Any]:
    """Occurrences de chaque clé de doublon déjà présente dans le compte (import idempotent).

    Clé sur les valeurs brutes du relevé (`original_*`, à défaut les valeurs stockées pour les lignes
    antérieures ou saisies à la main) : ni une règle ni une retouche manuelle ne la fait bouger."""
    return Counter(
        duplicate_key(tx.date, tx.amount, tx.original_merchant or tx.merchant, tx.original_type or tx.type)
        for tx in db.query(Transaction.date, Transaction.amount, Transaction.merchant, Transaction.type,
                           Transaction.original_merchant, Transaction.original_type)
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
