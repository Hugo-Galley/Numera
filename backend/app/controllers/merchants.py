from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers import deps
from app.schemas import merchant as merchant_schemas
from app.services import merchants as service

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("", response_model=List[merchant_schemas.MerchantRead])
def get_merchants(
    db: Session = Depends(deps.get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=1000, ge=1, le=5000),
    search: Optional[str] = None
):
    return service.get_merchants(db, skip, limit, search)


@router.post("", response_model=merchant_schemas.MerchantRead, status_code=status.HTTP_201_CREATED)
def create_merchant(merchant_in: merchant_schemas.MerchantCreate, db: Session = Depends(deps.get_db)):
    return service.create_merchant(db, merchant_in)


@router.get("/{merchant_id}", response_model=merchant_schemas.MerchantRead)
def get_merchant(merchant_id: int, db: Session = Depends(deps.get_db)):
    return service.get_merchant(db, merchant_id)


@router.put("/{merchant_id}", response_model=merchant_schemas.MerchantRead)
def update_merchant(merchant_id: int, merchant_in: merchant_schemas.MerchantUpdate, db: Session = Depends(deps.get_db)):
    return service.update_merchant(db, merchant_id, merchant_in)


@router.delete("/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_merchant(merchant_id: int, db: Session = Depends(deps.get_db)):
    service.delete_merchant(db, merchant_id)


@router.post("/{merchant_id}/aliases", response_model=merchant_schemas.MerchantAlias)
def add_alias(merchant_id: int, alias_in: merchant_schemas.MerchantAliasCreate, db: Session = Depends(deps.get_db)):
    return service.add_alias(db, merchant_id, alias_in)


@router.delete("/aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_alias(alias_id: int, db: Session = Depends(deps.get_db)):
    service.remove_alias(db, alias_id)


@router.post("/auto-normalize")
def auto_normalize_transactions(db: Session = Depends(deps.get_db)):
    """Match transactions with merchants based on aliases."""
    return service.auto_normalize_transactions(db)


@router.get("/suggestions/unnormalized")
def get_unnormalized_merchant_labels(db: Session = Depends(deps.get_db), min_count: int = 5):
    """Find merchant labels in transactions that are not yet normalized."""
    return service.get_unnormalized_merchant_labels(db, min_count)
