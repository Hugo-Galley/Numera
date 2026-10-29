from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dividend import DividendSummary
from app.services.analytics import dividends as service

router = APIRouter()


@router.get("/dividends", response_model=DividendSummary)
async def get_dividends(
    account_id: int | None = Query(default=None),
    months: int = Query(default=24, ge=1, le=120),
    db: Session = Depends(get_db),
):
    """Dividendes nets / bruts en EUR : totaux, par mois, par année et par titre (avec rendements)."""
    return await service.compute_dividends(db, account_id, months)
