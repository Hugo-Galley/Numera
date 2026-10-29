from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.analytics import diversity as service

router = APIRouter(tags=["diversity-scanner"])


@router.get("/analytics/diversity-scanner")
async def diversity_scanner(
    account_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Consolidated Diversity & ETF Look-Through Scanner.
    Computes true underlying company exposures, country/sector breakdown,
    redundancy & overlap detection, diversity score, and dual-view (Stocks vs Total Wealth).
    """
    return await service.compute_diversity(db, account_id)
