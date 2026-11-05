from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.sync_bridge import run_async
from app.db.session import get_db
from app.services.analytics import metrics as service

router = APIRouter()


@router.get("/tags")
def tags_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return run_async(service.compute_tags(db, month, year, start_date, end_date, account_id))


@router.get("/expenses-by-category")
def expenses_by_category(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return run_async(service.compute_expenses_by_category(db, month, year, account_id))


@router.get("/top-merchants")
def top_merchants(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    limit: int = Query(default=5, ge=1, le=50),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return run_async(service.compute_top_merchants(db, month, year, limit, account_id))


@router.get("/account-flow-summary")
def account_flow_summary(
    account_id: int = Query(...),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Flux net du mois (de paie) courant et du précédent d'un compte + dépense moyenne."""
    return service.compute_account_flow_summary(db, account_id, start_date, end_date)


@router.get("/kpi-history")
def kpi_history(
    months_count: int = Query(default=6, ge=1, le=24),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):
    return run_async(service.compute_kpi_history(db, months_count, account_id))


@router.get("/timeseries")
def timeseries_analytics(
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return run_async(service.compute_timeseries(db, year, account_id))


@router.get("/calendar")
def calendar_analytics(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return run_async(service.compute_calendar(db, month, year, account_id))
