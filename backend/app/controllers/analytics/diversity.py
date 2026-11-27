
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.core.sync_bridge import run_async
from app.schemas.analytics_reports import DiversityScanner, MarketReferenceSetting
from app.services.analytics import diversity as service
from app.services.investissement import market_reference

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


@router.put("/analytics/diversity-scanner/market-reference", response_model=MarketReferenceSetting)
def set_market_reference(payload: MarketReferenceSetting, db: Session = Depends(get_db)) -> dict[str, str | None]:
    """Référence de marché du scanner (ticker d'un profil ETF ; vide : ETF de référence du MSCI ACWI)."""
    return market_reference.set_market_reference(db, payload.ticker)
