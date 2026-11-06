from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.benefit import Benefit
from app.models.transaction import Transaction


def list_ordered(db: Session) -> list[Benefit]:
    return db.query(Benefit).order_by(Benefit.active.desc(), Benefit.name.asc()).all()


def list_active(db: Session) -> list[Benefit]:
    return db.query(Benefit).filter(Benefit.active.is_(True)).all()


def get(db: Session, benefit_id: int) -> Benefit | None:
    return db.get(Benefit, benefit_id)


def account_exists(db: Session, account_id: int) -> bool:
    return db.get(Account, account_id) is not None


def matching_entries(db: Session, benefit: Benefit, since: datetime) -> list[Transaction]:
    """Entrées (hors virements internes) dont le libellé ou la note contient le motif de l'aide."""
    pattern = f"%{benefit.match_pattern.strip()}%"
    query = db.query(Transaction).filter(
        Transaction.type == "Entree",
        Transaction.is_transfer == False,
        Transaction.is_provisional == False,  # l'entrée générée n'est pas un versement reçu
        Transaction.date >= since,
        or_(Transaction.merchant.ilike(pattern), Transaction.note.ilike(pattern)),
    )
    if benefit.account_id is not None:
        query = query.filter(Transaction.account_id == benefit.account_id)
    if benefit.start_date is not None:
        query = query.filter(Transaction.date >= datetime.combine(benefit.start_date, datetime.min.time()))
    return query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()


def provisional_entries(db: Session) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.is_provisional == True, Transaction.benefit_id.isnot(None))
        .order_by(Transaction.date, Transaction.id)
        .all()
    )


def has_generated_in(db: Session, benefit_id: int, start: datetime, end: datetime) -> bool:
    """Une entrée générée (provisoire ou déjà remplacée) existe pour l'aide dans [start, end[."""
    return (
        db.query(Transaction.id)
        .filter(Transaction.benefit_id == benefit_id, Transaction.date >= start, Transaction.date < end)
        .first()
        is not None
    )


def add(db: Session, benefit: Benefit) -> None:
    db.add(benefit)
    db.flush()


def delete(db: Session, benefit: Benefit) -> None:
    db.delete(benefit)
