"""Bilan annuel « Wrapped » (calcul : `services/analytics/wrapped.py`)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.sync_bridge import run_async
from app.db.session import get_db
from app.schemas.wrapped import WrappedReport
from app.services.analytics.wrapped import compute_wrapped

router = APIRouter()


@router.get("/wrapped", response_model=WrappedReport)
def get_wrapped(
    year: int = Query(ge=2000, le=2200),
    db: Session = Depends(get_db),
) -> WrappedReport:
    return run_async(compute_wrapped(db, year))
