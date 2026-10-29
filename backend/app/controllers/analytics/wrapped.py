"""Bilan annuel « Wrapped » (calcul : `services/analytics/wrapped.py`)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.wrapped import WrappedReport
from app.services.analytics.wrapped import compute_wrapped

router = APIRouter()


@router.get("/wrapped", response_model=WrappedReport)
async def get_wrapped(
    year: int = Query(ge=2000, le=2200),
    db: Session = Depends(get_db),
) -> WrappedReport:
    return await compute_wrapped(db, year)
