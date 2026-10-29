from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.insight import FireResponse, WealthForecastResponse, WealthSimulationResponse
from app.services.analytics import investments as service

router = APIRouter()


@router.get("/investments")
async def investments_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):
    return await service.compute_investments(db, month, year, account_id)


@router.get("/investments/{account_id}")
async def investment_account_analytics(account_id: int, db: Session = Depends(get_db)):
    return await service.compute_investment_account(db, account_id)


@router.get("/investments/{account_id}/performance-history")
async def investment_performance_history(account_id: int, db: Session = Depends(get_db)):
    return await service.compute_performance_history(db, account_id)


@router.get("/investments-allocation")
async def investments_allocation(account_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    return await service.compute_allocation(db, account_id)


@router.get("/investments-allocation-advanced")
async def investments_allocation_advanced(db: Session = Depends(get_db)):
    """Répartition avancée : par classe d'actifs, secteur et zone géographique."""
    return await service.compute_allocation_advanced(db)


@router.get("/patrimoine-allocation")
async def patrimoine_allocation(db: Session = Depends(get_db)):
    """Répartition du patrimoine actif (tous comptes) ; crédits exclus des items, en `total_debts_eur`."""
    return await service.compute_patrimoine_allocation(db)


@router.get("/wealth-forecast", response_model=WealthForecastResponse)
async def wealth_forecast(
    years: int = Query(default=10, ge=1, le=50),
    extra_monthly: float = Query(default=0.0, ge=-100000, le=100000),
    monthly_savings: Optional[float] = Query(default=None, ge=-100000, le=100000),
    investment_return_pct: Optional[float] = Query(default=None, ge=-50, le=100),
    savings_return_pct: Optional[float] = Query(default=None, ge=-50, le=100),
    db: Session = Depends(get_db),
):
    """Prévision simple du patrimoine (épargne moyenne des 12 derniers mois complets, XIRR constaté) ;
    `monthly_savings`, `investment_return_pct` et `savings_return_pct` remplacent les valeurs calculées."""
    return await service.compute_wealth_forecast(
        db, years, extra_monthly, monthly_savings, investment_return_pct, savings_return_pct
    )


@router.get("/fire", response_model=FireResponse)
async def fire_projection(
    withdrawal_rate_pct: float = Query(default=4.0, gt=0, le=20),
    inflation_pct: float = Query(default=2.0, ge=-5, le=20),
    return_pct: Optional[float] = Query(default=None, ge=-50, le=100),
    monthly_savings: Optional[float] = Query(default=None, ge=-100000, le=100000),
    annual_expenses: Optional[float] = Query(default=None, gt=0, le=10_000_000),
    db: Session = Depends(get_db),
):
    """Indépendance financière sur les données réelles (cible = dépenses annuelles ÷ taux de retrait)."""
    return await service.compute_fire(db, withdrawal_rate_pct, inflation_pct, return_pct, monthly_savings, annual_expenses)


@router.get("/asset-allocation/suggestions")
def get_asset_allocation_suggestions(db: Session = Depends(get_db)):
    """Valeurs de classes d'actifs, secteurs et zones pour l'autocomplétion."""
    return service.compute_allocation_suggestions(db)


@router.get("/wealth-simulation", response_model=WealthSimulationResponse)
async def wealth_simulation(
    initial_capital: float = Query(ge=0),
    monthly_contribution: float = Query(ge=0),
    annual_return_pct: float = Query(ge=-100, le=1000),
    years: int = Query(ge=1, le=50, default=15),
    volatility_pct: float = Query(ge=0, le=100, default=0.0),
    inflation_rate_pct: float = Query(ge=-50, le=100, default=0.0),
    contribution_indexation_pct: float = Query(ge=-50, le=100, default=0.0),
    tax_rate_pct: float = Query(ge=0, le=100, default=0.0),
    tax_deferred: bool = Query(default=True),
    events: Optional[str] = Query(default=None),
):
    """Simulateur de patrimoine (intérêts composés, inflation, fiscalité, événements, volatilité Monte-Carlo)."""
    return service.compute_wealth_simulation(
        initial_capital, monthly_contribution, annual_return_pct, years, volatility_pct, inflation_rate_pct,
        contribution_indexation_pct, tax_rate_pct, tax_deferred, events,
    )
