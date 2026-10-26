from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account import Account
from app.models.financial_event import FinancialEvent
from app.schemas.financial_event import FinancialEventCreate, FinancialEventRead, FinancialEventUpdate

router = APIRouter(prefix="/financial-events", tags=["financial-events"])


def _check_account(db: Session, account_id: int | None) -> None:
    if account_id is not None and db.get(Account, account_id) is None:
        raise HTTPException(status_code=404, detail="Compte introuvable")


def _read(event: FinancialEvent) -> FinancialEventRead:
    read = FinancialEventRead.model_validate(event)
    read.account_name = event.account.name if event.account else None
    return read


@router.get("", response_model=list[FinancialEventRead])
def list_financial_events(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Journal des décisions, du plus récent au plus ancien (bornes incluses)."""
    query = db.query(FinancialEvent)
    if start:
        query = query.filter(FinancialEvent.date >= start)
    if end:
        query = query.filter(FinancialEvent.date <= end)
    if account_id is not None:
        query = query.filter(FinancialEvent.account_id == account_id)
    return [_read(e) for e in query.order_by(FinancialEvent.date.desc(), FinancialEvent.id.desc()).all()]


@router.post("", response_model=FinancialEventRead, status_code=201)
def create_financial_event(payload: FinancialEventCreate, db: Session = Depends(get_db)):
    _check_account(db, payload.account_id)
    data = payload.model_dump()
    data["note"] = (data["note"] or "").strip() or None
    event = FinancialEvent(**data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return _read(event)


@router.patch("/{event_id}", response_model=FinancialEventRead)
def update_financial_event(event_id: int, payload: FinancialEventUpdate, db: Session = Depends(get_db)):
    event = db.get(FinancialEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    data = payload.model_dump(exclude_unset=True)
    _check_account(db, data.get("account_id"))
    for field in ("date", "title"):
        if field in data and data[field] is None:
            data.pop(field)  # colonnes non nullables : `null` = ne pas modifier
    if "note" in data:
        data["note"] = (data["note"] or "").strip() or None
    for field, value in data.items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return _read(event)


@router.delete("/{event_id}", status_code=204)
def delete_financial_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(FinancialEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    db.delete(event)
    db.commit()
