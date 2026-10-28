from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.financial_event import FinancialEventCreate, FinancialEventRead, FinancialEventUpdate
from app.services import financial_events as service

router = APIRouter(prefix="/financial-events", tags=["financial-events"])


@router.get("", response_model=list[FinancialEventRead])
def list_financial_events(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Journal des décisions, du plus récent au plus ancien (bornes incluses)."""
    return service.list_financial_events(db, start, end, account_id)


@router.post("", response_model=FinancialEventRead, status_code=201)
def create_financial_event(payload: FinancialEventCreate, db: Session = Depends(get_db)):
    return service.create_financial_event(db, payload)


@router.patch("/{event_id}", response_model=FinancialEventRead)
def update_financial_event(event_id: int, payload: FinancialEventUpdate, db: Session = Depends(get_db)):
    return service.update_financial_event(db, event_id, payload)


@router.delete("/{event_id}", status_code=204)
def delete_financial_event(event_id: int, db: Session = Depends(get_db)):
    service.delete_financial_event(db, event_id)
