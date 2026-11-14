from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.core.sync_bridge import run_async
from app.schemas.tax import AnnualReport, TaxOverview, TaxSettings, TaxSettingsUpdate
from app.services.investissement.tax import annual_report, load_tax_settings, save_tax_settings, tax_overview

router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/overview", response_model=TaxOverview)
def get_overview(db: Session = Depends(get_db)) -> TaxOverview:
    return run_async(tax_overview(db))


@router.get("/settings", response_model=TaxSettings)
def get_settings(db: Session = Depends(get_db)) -> TaxSettings:
    return load_tax_settings(db)


@router.patch("/settings", response_model=TaxSettings)
def update_settings(payload: TaxSettingsUpdate, db: Session = Depends(get_db)) -> TaxSettings:
    return save_tax_settings(db, payload)


@router.get("/annual-report", response_model=AnnualReport)
def get_annual_report(year: int | None = None, db: Session = Depends(get_db)) -> AnnualReport:
    return run_async(annual_report(db, year))
