from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.category import Category


def ungrouped_category(db: Session, name: str) -> Category | None:
    """Catégorie de ce nom dont le groupe est vide ou absent."""
    return db.query(Category).filter(Category.name == name, or_(Category.group.is_(None), Category.group == "")).first()


def has_categories(db: Session) -> bool:
    return db.query(Category).first() is not None
