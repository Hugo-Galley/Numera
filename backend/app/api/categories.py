from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.session import get_db
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name.asc()).all()


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name == payload.name).first()
    if existing:
        raise api_error(409, "category_already_exists", "Category already exists", {"name": payload.name})
    category = Category(
        name=payload.name,
        type=payload.type,
        icon=payload.icon,
        color=payload.color,
        group=payload.group,
        monthly_limit=payload.monthly_limit,
        annual_limit=payload.annual_limit,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise api_error(404, "category_not_found", "Category not found", {"category_id": category_id})

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != category.name:
        existing = db.query(Category).filter(Category.name == data["name"]).first()
        if existing:
            raise api_error(409, "category_already_exists", "Category already exists", {"name": data["name"]})

    for key, value in data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise api_error(404, "category_not_found", "Category not found", {"category_id": category_id})
    
    # Nullify references in transactions
    db.query(Transaction).filter(Transaction.category_id == category_id).update(
        {Transaction.category_id: None}, 
        synchronize_session=False
    )
    
    db.delete(category)
    db.commit()
