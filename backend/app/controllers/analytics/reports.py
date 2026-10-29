from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.insight import CashflowProjection, MonthlyReport, MoneyFlowReport
from app.services.analytics import reports as service

router = APIRouter()


@router.get("/cashflow-projection", response_model=CashflowProjection)
async def get_cashflow_projection(
    days: int = Query(default=30, ge=7, le=365),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return await service.compute_cashflow_projection(db, days=days, account_id=account_id)


@router.get("/monthly-report", response_model=MonthlyReport)
async def get_monthly_report(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Rapport mensuel consolidé, comparé au mois précédent, avec insights."""
    return await service.compute_monthly_report(db, month, year, account_id)


@router.get("/money-flow", response_model=MoneyFlowReport)
async def get_money_flow(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Où est passé l'argent du mois."""
    return await service.compute_money_flow(db, month, year, account_id)


@router.get("/sankey")
async def sankey_analytics(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return await service.compute_sankey(db, month, year, account_id)
