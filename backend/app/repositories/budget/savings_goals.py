from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction


def list_all(db: Session) -> list[SavingsGoal]:
    return db.query(SavingsGoal).all()


def get(db: Session, goal_id: int) -> SavingsGoal | None:
    return db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()


def add(db: Session, goal: SavingsGoal) -> None:
    db.add(goal)
    db.flush()


def delete(db: Session, goal: SavingsGoal) -> None:
    db.delete(goal)


def goal_rows(db: Session, goal: SavingsGoal) -> list[tuple[str, float, str]]:
    """(type, montant, devise du compte) des transactions suivies par l'objectif.

    Sans mot-clé, compte ni catégorie, l'objectif ne suit rien (liste vide par prudence).
    """
    if not goal.keyword and not goal.account_id and not goal.category_id:
        return []
    query = db.query(Transaction.type, Transaction.amount, Account.currency).join(Account).outerjoin(Category)
    if goal.account_id:
        query = query.filter(Transaction.account_id == goal.account_id)
    if goal.category_id:
        query = query.filter(Transaction.category_id == goal.category_id)
    if goal.keyword:
        query = query.filter(or_(
            Transaction.note.ilike(f"%{goal.keyword}%"),
            Transaction.merchant.ilike(f"%{goal.keyword}%"),
            Category.name.ilike(f"%{goal.keyword}%")
        ))
    return query.all()
