from sqlalchemy.orm import Session

from app.models.categorization_rule import CategorizationRule
from app.models.category import Category
from app.models.merchant import Merchant
from app.models.recurring_transaction import RecurringTransaction
from app.models.salary_config import SalaryConfig
from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction

# Toutes les colonnes qui référencent une catégorie : remises à NULL avant suppression
_CATEGORY_REFERENCES = (
    Transaction.category_id,
    SavingsGoal.category_id,
    CategorizationRule.category_id,
    RecurringTransaction.category_id,
    Merchant.category_id,
    SalaryConfig.salary_category_id,
    SalaryConfig.ticket_category_id,
)


def list_all(db: Session, include_archived: bool) -> list[Category]:
    query = db.query(Category)
    if not include_archived:
        query = query.filter(Category.archived.is_(False))
    return query.order_by(Category.name.asc()).all()


def get(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def get_by_name(db: Session, name: str) -> Category | None:
    return db.query(Category).filter(Category.name == name).first()


def add(db: Session, category: Category) -> None:
    db.add(category)
    db.flush()


def detach_references(db: Session, category_id: int) -> None:
    for column in _CATEGORY_REFERENCES:
        db.query(column.class_).filter(column == category_id).update({column: None}, synchronize_session=False)


def delete(db: Session, category: Category) -> None:
    db.delete(category)
