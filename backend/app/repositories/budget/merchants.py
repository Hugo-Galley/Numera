from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.merchant import Merchant, MerchantAlias
from app.models.transaction import Transaction


def list_page(db: Session, skip: int, limit: int, search: str | None) -> list[Merchant]:
    query = select(Merchant)
    if search:
        query = query.where(Merchant.name.ilike(f"%{search}%"))
    return db.scalars(query.offset(skip).limit(limit)).all()


def get(db: Session, merchant_id: int) -> Merchant | None:
    return db.get(Merchant, merchant_id)


def name_taken(db: Session, name: str) -> bool:
    return db.scalar(select(Merchant.id).where(Merchant.name == name)) is not None


def taken_aliases(db: Session, labels: list[str]) -> list[str]:
    return db.scalars(select(MerchantAlias.label).where(MerchantAlias.label.in_(labels))).all()


def get_alias(db: Session, alias_id: int) -> MerchantAlias | None:
    return db.get(MerchantAlias, alias_id)


def all_aliases(db: Session) -> list[MerchantAlias]:
    return db.scalars(select(MerchantAlias)).all()


def add(db: Session, obj: Merchant | MerchantAlias) -> None:
    db.add(obj)
    db.flush()


def delete(db: Session, obj: Merchant | MerchantAlias) -> None:
    db.delete(obj)


def link_unnormalized_transactions(db: Session, merchant_id: int, labels: list[str]) -> int:
    """Rattache au marchand les transactions encore non normalisées dont le libellé bancaire est un de ses alias."""
    if not labels:
        return 0
    result = db.execute(
        Transaction.__table__.update()
        .where(Transaction.merchant.in_(labels))
        .where(Transaction.merchant_id == None)  # noqa: E711
        .values(merchant_id=merchant_id)
    )
    return result.rowcount


def unnormalized_labels(db: Session, min_count: int) -> list[tuple[str, int]]:
    # Les flux internes (virements, alimentations d'épargne/investissement) ne sont pas des marchands
    query = (
        select(Transaction.merchant, func.count(Transaction.id).label("count"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(Transaction.merchant_id == None)  # noqa: E711
        .where(Transaction.is_transfer == False)  # noqa: E712
        .where(func.coalesce(Category.name, "").notin_(["Investissement", "Epargne"]))
        .group_by(Transaction.merchant)
        .having(func.count(Transaction.id) >= min_count)
        .order_by(func.count(Transaction.id).desc())
    )
    return db.execute(query).all()
