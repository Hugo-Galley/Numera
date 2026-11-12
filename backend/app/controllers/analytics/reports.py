from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.sync_bridge import run_async
from app.db.session import get_db
from app.schemas.analytics_reports import Sankey
from app.schemas.insight import CashflowProjection, MoneyFlowReport, MonthlyReport
from app.services.analytics import reports as service

router = APIRouter()


@router.get("/cashflow-projection", response_model=CashflowProjection)
def get_cashflow_projection(
    days: int = Query(default=30, ge=7, le=365),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return run_async(service.compute_cashflow_projection(db, days=days, account_id=account_id))


@router.get("/monthly-report", response_model=MonthlyReport)
def get_monthly_report(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Rapport mensuel consolidé, comparé au mois précédent, avec insights."""
    return run_async(service.compute_monthly_report(db, month, year, account_id))


@router.get("/money-flow", response_model=MoneyFlowReport)
def get_money_flow(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Où est passé l'argent du mois."""
    return run_async(service.compute_money_flow(db, month, year, account_id))


@router.get("/sankey", response_model=Sankey, response_model_exclude_unset=True)
def sankey_analytics(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return run_async(service.compute_sankey(db, month, year, account_id))
