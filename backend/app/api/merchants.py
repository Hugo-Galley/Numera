from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_

from app.api import deps
from app.models.merchant import Merchant, MerchantAlias
from app.models.transaction import Transaction
from app.schemas import merchant as merchant_schemas
from app.db.session import SessionLocal

router = APIRouter(prefix="/merchants", tags=["merchants"])

@router.get("", response_model=List[merchant_schemas.MerchantRead])
def get_merchants(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
):
    query = select(Merchant)
    if search:
        query = query.where(Merchant.name.ilike(f"%{search}%"))
    
    merchants = db.scalars(query.offset(skip).limit(limit)).all()
    return merchants

@router.post("", response_model=merchant_schemas.MerchantRead, status_code=status.HTTP_201_CREATED)
def create_merchant(
    merchant_in: merchant_schemas.MerchantCreate,
    db: Session = Depends(deps.get_db)
):
    # Check if merchant already exists
    existing = db.scalar(select(Merchant).where(Merchant.name == merchant_in.name))
    if existing:
        raise HTTPException(status_code=400, detail="Merchant already exists")
    
    merchant = Merchant(
        name=merchant_in.name,
        category_id=merchant_in.category_id,
        icon=merchant_in.icon,
        color=merchant_in.color
    )
    db.add(merchant)
    db.flush()
    
    # Add aliases
    for label in merchant_in.aliases:
        alias = MerchantAlias(merchant_id=merchant.id, label=label)
        db.add(alias)
    
    db.commit()
    db.refresh(merchant)
    return merchant

@router.get("/{merchant_id}", response_model=merchant_schemas.MerchantRead)
def get_merchant(
    merchant_id: int,
    db: Session = Depends(deps.get_db)
):
    merchant = db.get(Merchant, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant

@router.put("/{merchant_id}", response_model=merchant_schemas.MerchantRead)
def update_merchant(
    merchant_id: int,
    merchant_in: merchant_schemas.MerchantUpdate,
    db: Session = Depends(deps.get_db)
):
    merchant = db.get(Merchant, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    update_data = merchant_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(merchant, field, value)
    
    db.commit()
    db.refresh(merchant)
    return merchant

@router.delete("/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_merchant(
    merchant_id: int,
    db: Session = Depends(deps.get_db)
):
    merchant = db.get(Merchant, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    db.delete(merchant)
    db.commit()
    return None

@router.post("/{merchant_id}/aliases", response_model=merchant_schemas.MerchantAlias)
def add_alias(
    merchant_id: int,
    alias_in: merchant_schemas.MerchantAliasCreate,
    db: Session = Depends(deps.get_db)
):
    merchant = db.get(Merchant, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    # Check if alias already exists
    existing = db.scalar(select(MerchantAlias).where(MerchantAlias.label == alias_in.label))
    if existing:
        raise HTTPException(status_code=400, detail="Alias already exists")
    
    alias = MerchantAlias(merchant_id=merchant_id, label=alias_in.label)
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias

@router.delete("/aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_alias(
    alias_id: int,
    db: Session = Depends(deps.get_db)
):
    alias = db.get(MerchantAlias, alias_id)
    if not alias:
        raise HTTPException(status_code=404, detail="Alias not found")
    
    db.delete(alias)
    db.commit()
    return None

@router.post("/auto-normalize")
def auto_normalize_transactions(
    db: Session = Depends(deps.get_db)
):
    """
    Match transactions with merchants based on aliases.
    """
    # Get all aliases
    aliases = db.scalars(select(MerchantAlias)).all()
    
    count = 0
    for alias in aliases:
        # Update transactions that match the alias label and don't have a merchant_id
        result = db.execute(
            Transaction.__table__.update()
            .where(Transaction.merchant == alias.label)
            .where(Transaction.merchant_id == None)
            .values(merchant_id=alias.merchant_id)
        )
        count += result.rowcount
    
    db.commit()
    return {"normalized_count": count}

@router.get("/suggestions/unnormalized")
def get_unnormalized_merchant_labels(
    db: Session = Depends(deps.get_db),
    min_count: int = 5
):
    """
    Find merchant labels in transactions that are not yet normalized.
    """
    query = (
        select(Transaction.merchant, func.count(Transaction.id).label("count"))
        .where(Transaction.merchant_id == None)
        .group_by(Transaction.merchant)
        .having(func.count(Transaction.id) >= min_count)
        .order_by(func.count(Transaction.id).desc())
    )
    
    results = db.execute(query).all()
    return [{"label": r.merchant, "count": r.count} for r in results]
