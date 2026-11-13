
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.sync_bridge import run_async
from app.db.session import get_db
from app.schemas.analytics_reports import DiversityScanner
from app.services.analytics import diversity as service

router = APIRouter(tags=["diversity-scanner"])


@router.get("/analytics/diversity-scanner", response_model=DiversityScanner)
def diversity_scanner(
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Consolidated Diversity & ETF Look-Through Scanner.
    Computes true underlying company exposures, country/sector breakdown,
    redundancy & overlap detection, diversity score, and dual-view (Stocks vs Total Wealth).
    """
    return run_async(service.compute_diversity(db, account_id))
