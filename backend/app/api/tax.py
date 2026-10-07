from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.analytics.tax import build_annual_report, build_overview, load_tax_settings, save_tax_settings
from app.db.session import get_db
from app.schemas.tax import AnnualReport, TaxOverview, TaxSettings, TaxSettingsUpdate

router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/overview", response_model=TaxOverview)
def get_overview(db: Session = Depends(get_db)):
    return build_overview(db, date.today())


@router.get("/settings", response_model=TaxSettings)
def get_settings(db: Session = Depends(get_db)):
    return load_tax_settings(db)


@router.patch("/settings", response_model=TaxSettings)
def update_settings(payload: TaxSettingsUpdate, db: Session = Depends(get_db)):
    return save_tax_settings(db, payload)


@router.get("/annual-report", response_model=AnnualReport)
async def get_annual_report(year: int | None = None, db: Session = Depends(get_db)):
    return await build_annual_report(db, year or date.today().year)
