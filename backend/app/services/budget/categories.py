from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.category import Category
from app.repositories.budget import categories as repo
from app.schemas.category import CategoryCreate, CategoryUpdate


def _require(db: Session, category_id: int) -> Category:
    category = repo.get(db, category_id)
    if not category:
        raise NotFoundError("Category not found", code="category_not_found", context={"category_id": category_id})
    return category


def _ensure_name_free(db: Session, name: str) -> None:
    if repo.get_by_name(db, name):
        raise ConflictError("Category already exists", code="category_already_exists", context={"name": name})


def list_categories(db: Session, include_archived: bool) -> list[Category]:
    return repo.list_all(db, include_archived)


def create_category(db: Session, payload: CategoryCreate) -> Category:
    _ensure_name_free(db, payload.name)
    category = Category(
        name=payload.name,
        type=payload.type,
        icon=payload.icon,
        color=payload.color,
        group=payload.group,
        monthly_limit=payload.monthly_limit,
        annual_limit=payload.annual_limit,
    )
    repo.add(db, category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, payload: CategoryUpdate) -> Category:
    category = _require(db, category_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != category.name:
        _ensure_name_free(db, data["name"])
    if data.get("archived", True) is None:
        data.pop("archived")  # colonne non nullable : `null` = ne pas modifier
    for key, value in data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = _require(db, category_id)
    repo.detach_references(db, category_id)
    repo.delete(db, category)
    db.commit()
