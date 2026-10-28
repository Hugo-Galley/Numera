from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.analytics.budget import compute_resilience
from app.services.tax import build_annual_report, build_overview, load_tax_settings, save_tax_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.tax import AnnualReport, TaxOverview, TaxSettings, TaxSettingsUpdate

logger = get_logger(__name__)
router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/overview", response_model=TaxOverview)
async def get_overview(db: Session = Depends(get_db)):
    today = date.today()
    try:
        months = (await compute_resilience(db, today.year, today.month))["months"]
    except Exception as exc:  # le conseil reste utile sans l'épargne de précaution
        logger.warning(f"Resilience unavailable for tax advice: {exc}")
        months = None
    return build_overview(db, today, months)


@router.get("/settings", response_model=TaxSettings)
def get_settings(db: Session = Depends(get_db)):
    return load_tax_settings(db)


@router.patch("/settings", response_model=TaxSettings)
def update_settings(payload: TaxSettingsUpdate, db: Session = Depends(get_db)):
    return save_tax_settings(db, payload)


@router.get("/annual-report", response_model=AnnualReport)
async def get_annual_report(year: int | None = None, db: Session = Depends(get_db)):
    return await build_annual_report(db, year or date.today().year)
