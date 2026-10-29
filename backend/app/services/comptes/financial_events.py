from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.financial_event import FinancialEvent
from app.repositories.comptes import financial_events as repo
from app.schemas.financial_event import FinancialEventCreate, FinancialEventRead, FinancialEventUpdate


def _check_account(db: Session, account_id: int | None) -> None:
    if account_id is not None and not repo.account_exists(db, account_id):
        raise NotFoundError("Compte introuvable")


def _require(db: Session, event_id: int) -> FinancialEvent:
    event = repo.get(db, event_id)
    if event is None:
        raise NotFoundError("Événement introuvable")
    return event


def _read(event: FinancialEvent) -> FinancialEventRead:
    read = FinancialEventRead.model_validate(event)
    read.account_name = event.account.name if event.account else None
    return read


def list_financial_events(db: Session, start: date | None, end: date | None,
                          account_id: int | None) -> list[FinancialEventRead]:
    """Journal des décisions, du plus récent au plus ancien (bornes incluses)."""
    return [_read(e) for e in repo.list_between(db, start, end, account_id)]


def create_financial_event(db: Session, payload: FinancialEventCreate) -> FinancialEventRead:
    _check_account(db, payload.account_id)
    data = payload.model_dump()
    data["note"] = (data["note"] or "").strip() or None
    event = FinancialEvent(**data)
    repo.add(db, event)
    db.commit()
    db.refresh(event)
    return _read(event)


def update_financial_event(db: Session, event_id: int, payload: FinancialEventUpdate) -> FinancialEventRead:
    event = _require(db, event_id)
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


def delete_financial_event(db: Session, event_id: int) -> None:
    repo.delete(db, _require(db, event_id))
    db.commit()
