from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.tax import AnnualReport, TaxOverview, TaxSettings, TaxSettingsUpdate
from app.services.tax import annual_report, load_tax_settings, save_tax_settings, tax_overview

router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/overview", response_model=TaxOverview)
async def get_overview(db: Session = Depends(get_db)):
    return await tax_overview(db)


@router.get("/settings", response_model=TaxSettings)
def get_settings(db: Session = Depends(get_db)):
    return load_tax_settings(db)


@router.patch("/settings", response_model=TaxSettings)
def update_settings(payload: TaxSettingsUpdate, db: Session = Depends(get_db)):
    return save_tax_settings(db, payload)


@router.get("/annual-report", response_model=AnnualReport)
async def get_annual_report(year: int | None = None, db: Session = Depends(get_db)):
    return await annual_report(db, year)
