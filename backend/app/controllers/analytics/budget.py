from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services import budget_period
from app.db.session import get_db
from app.schemas.category import BudgetAlert
from app.services.analytics.budget import compute_budget, compute_budget_alerts, compute_resilience

router = APIRouter()


@router.get("/budget")
async def budget_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return await compute_budget(db, month=month, year=year, account_id=account_id)


@router.get("/resilience")
async def resilience(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    db: Session = Depends(get_db),
):
    return await compute_resilience(db, year, month)


@router.get("/budget-alerts", response_model=list[BudgetAlert])
async def budget_alerts(
    year: int = Query(..., ge=2000, le=2200),
    month: int = Query(..., ge=1, le=12),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return await compute_budget_alerts(db, year=year, month=month, account_id=account_id)


class BudgetPeriodModeUpdate(BaseModel):
    mode: Literal["civil", "salary"]


@router.get("/budget-period")
def get_budget_period(
    year: int | None = Query(default=None, ge=2000, le=2200),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Mois budgétaire en cours et fenêtre (début / fin incluse) du mois demandé."""
    current_year, current_month = budget_period.current_period(db)
    info = budget_period.describe(db, year or current_year, month or current_month)
    return {**info, "current": {"year": current_year, "month": current_month}}


@router.put("/budget-period")
def set_budget_period_mode(payload: BudgetPeriodModeUpdate, db: Session = Depends(get_db)):
    budget_period.set_mode(db, payload.mode)
    return get_budget_period(year=None, month=None, db=db)
