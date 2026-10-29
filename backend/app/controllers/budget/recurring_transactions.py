from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.recurring_transaction import RecurringTransactionCreate, RecurringTransactionRead, RecurringTransactionUpdate
from app.services.budget import recurring_transactions as service

router = APIRouter(prefix="/recurring-transactions", tags=["recurring-transactions"])


@router.post("/trigger", response_model=int)
async def trigger_generation(db: Session = Depends(get_db)) -> int:
    """Manually trigger the generation of recurring transactions."""
    return await service.trigger_generation(db)


@router.get("/", response_model=list[RecurringTransactionRead])
async def read_recurring_transactions(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=1000, ge=1, le=5000),  # défaut large : une troncature silencieuse masquait des lignes
    trigger: bool = Query(default=False)
) -> Any:
    return await service.read_recurring_transactions(db, skip, limit, trigger)


@router.post("/", response_model=RecurringTransactionRead)
async def create_recurring_transaction(*, db: Session = Depends(get_db), recurring_tx_in: RecurringTransactionCreate) -> Any:
    return await service.create_recurring_transaction(db, recurring_tx_in)


@router.patch("/{recurring_tx_id}", response_model=RecurringTransactionRead)
async def update_recurring_transaction(
    *, db: Session = Depends(get_db), recurring_tx_id: int, recurring_tx_in: RecurringTransactionUpdate,
) -> Any:
    return await service.update_recurring_transaction(db, recurring_tx_id, recurring_tx_in)


@router.delete("/{recurring_tx_id}")
def delete_recurring_transaction(*, db: Session = Depends(get_db), recurring_tx_id: int) -> Any:
    return service.delete_recurring_transaction(db, recurring_tx_id)
