from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.recurring_transaction import RecurringTransactionCreate, RecurringTransactionRead, RecurringTransactionUpdate
from app.core.recurring import generate_recurring_transactions

router = APIRouter(prefix="/recurring-transactions", tags=["recurring-transactions"])

@router.post("/trigger", response_model=int)
async def trigger_generation(db: Session = Depends(get_db)) -> int:
    """Manually trigger the generation of recurring transactions."""
    return await generate_recurring_transactions(db)

@router.get("/", response_model=list[RecurringTransactionRead])
async def read_recurring_transactions(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    trigger: bool = Query(default=False)
) -> Any:
    if trigger:
        await generate_recurring_transactions(db)
    return db.query(RecurringTransaction).offset(skip).limit(limit).all()

@router.post("/", response_model=RecurringTransactionRead)
def create_recurring_transaction(
    *,
    db: Session = Depends(get_db),
    recurring_tx_in: RecurringTransactionCreate,
) -> Any:
    recurring_tx = RecurringTransaction(**recurring_tx_in.model_dump())
    db.add(recurring_tx)
    db.commit()
    db.refresh(recurring_tx)
    return recurring_tx

@router.patch("/{recurring_tx_id}", response_model=RecurringTransactionRead)
def update_recurring_transaction(
    *,
    db: Session = Depends(get_db),
    recurring_tx_id: int,
    recurring_tx_in: RecurringTransactionUpdate,
) -> Any:
    recurring_tx = db.query(RecurringTransaction).filter(RecurringTransaction.id == recurring_tx_id).first()
    if not recurring_tx:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    
    update_data = recurring_tx_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(recurring_tx, field, value)
    
    db.add(recurring_tx)
    db.commit()
    db.refresh(recurring_tx)
    return recurring_tx

@router.delete("/{recurring_tx_id}")
def delete_recurring_transaction(
    *,
    db: Session = Depends(get_db),
    recurring_tx_id: int,
) -> Any:
    recurring_tx = db.query(RecurringTransaction).filter(RecurringTransaction.id == recurring_tx_id).first()
    if not recurring_tx:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    
    db.delete(recurring_tx)
    db.commit()
    return {"message": "Recurring transaction deleted"}
