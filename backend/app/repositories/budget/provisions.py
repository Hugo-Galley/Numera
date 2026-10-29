from collections.abc import Iterable
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.provision import Provision
from app.models.transaction import Transaction
from app.repositories.analytics.common import category_lines


def list_ordered(db: Session) -> list[Provision]:
    return db.query(Provision).order_by(Provision.active.desc(), Provision.name.asc()).all()


def list_active(db: Session) -> list[Provision]:
    return db.query(Provision).filter(Provision.active.is_(True)).all()


def get(db: Session, provision_id: int) -> Provision | None:
    return db.get(Provision, provision_id)


def category_exists(db: Session, category_id: int) -> bool:
    return db.get(Category, category_id) is not None


def account_exists(db: Session, account_id: int) -> bool:
    return db.get(Account, account_id) is not None


def accounts_in(db: Session, account_ids: Iterable[int]) -> list[Account]:
    return db.query(Account).filter(Account.id.in_(list(account_ids))).all()


def category_expenses_between(db: Session, category_id: int, start: datetime, end: datetime) -> list:
    """(date, devise, montant net) des dépenses de la catégorie dans [start, end), parts de découpage comprises."""
    lines = category_lines()
    return (
        db.query(Transaction.date, Account.currency, lines.c.net_amount)
        .select_from(Transaction)
        .join(lines, lines.c.transaction_id == Transaction.id)
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            lines.c.category_id == category_id,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,  # noqa: E712
            Transaction.date >= start,
            Transaction.date < end,
        )
        .all()
    )


def add(db: Session, provision: Provision) -> None:
    db.add(provision)
    db.flush()


def delete(db: Session, provision: Provision) -> None:
    db.delete(provision)
