from sqlalchemy.orm import Session

from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction


def list_by_priority(db: Session) -> list[CategorizationRule]:
    return db.query(CategorizationRule).order_by(CategorizationRule.priority.desc(), CategorizationRule.id.desc()).all()


def list_for_application(db: Session) -> list[CategorizationRule]:
    """Ordre d'application : priorité décroissante (à égalité, ordre de la base, comme avant)."""
    return db.query(CategorizationRule).order_by(CategorizationRule.priority.desc()).all()


def get(db: Session, rule_id: int) -> CategorizationRule | None:
    return db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()


def add(db: Session, rule: CategorizationRule) -> None:
    db.add(rule)
    db.flush()


def delete(db: Session, rule: CategorizationRule) -> None:
    db.delete(rule)


def categorizable_transactions(db: Session) -> list[Transaction]:
    """Transactions auxquelles une règle peut s'appliquer : ni « Solde Initial » ni virement interne."""
    return (
        db.query(Transaction)
        .filter(Transaction.type != "Solde Initial", Transaction.is_transfer == False)  # noqa: E712
        .all()
    )
