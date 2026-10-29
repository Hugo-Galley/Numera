from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.month_review import CloseRequest, ClosureRead, MonthReviewRead
from app.services.budget import month_review as service

router = APIRouter(prefix="/month-review", tags=["month-review"])


@router.get("", response_model=MonthReviewRead)
async def get_month_review(
    year: int = Query(ge=2000, le=2200),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
):
    """État de la revue d'un mois : étapes 1 à 3 calculées, statut de clôture, indicateur de modification."""
    return await service.get_month_review(db, year, month)


@router.post("/close", response_model=MonthReviewRead)
async def close_month(payload: CloseRequest, db: Session = Depends(get_db)):
    """Marque le mois comme revu et fige la photo des chiffres. Idempotent : re-clôturer remplace la photo."""
    return await service.close_month(db, payload)


@router.delete("", status_code=204)
def reopen_month(
    year: int = Query(ge=2000, le=2200),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Rouvre un mois (supprime sa clôture). Sans effet si le mois n'était pas clôturé."""
    service.reopen_month(db, year, month)


@router.get("/closures", response_model=list[ClosureRead])
def list_closures(db: Session = Depends(get_db)):
    return service.list_closures(db)
