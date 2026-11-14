from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.core.sync_bridge import run_async
from app.schemas.analytics_budget import BudgetOverview, BudgetPeriod, Resilience
from app.schemas.category import BudgetAlert
from app.services.analytics.budget import compute_budget, compute_budget_alerts, compute_resilience
from app.services.budget import budget_period

router = APIRouter()


@router.get("/budget", response_model=BudgetOverview)
def budget_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return run_async(compute_budget(db, month=month, year=year, account_id=account_id))


@router.get("/resilience", response_model=Resilience)
def resilience(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return run_async(compute_resilience(db, year, month))


@router.get("/budget-alerts", response_model=list[BudgetAlert])
def budget_alerts(
    year: int = Query(..., ge=2000, le=2200),
    month: int = Query(..., ge=1, le=12),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[BudgetAlert]:
    return run_async(compute_budget_alerts(db, year=year, month=month, account_id=account_id))


class BudgetPeriodModeUpdate(BaseModel):
    mode: Literal["civil", "salary"]


@router.get("/budget-period", response_model=BudgetPeriod)
def get_budget_period(
    year: int | None = Query(default=None, ge=2000, le=2200),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mois budgétaire en cours et fenêtre (début / fin incluse) du mois demandé."""
    return budget_period.period_info(db, year, month)


@router.put("/budget-period", response_model=BudgetPeriod)
def set_budget_period_mode(payload: BudgetPeriodModeUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    return budget_period.update_mode(db, payload.mode)
