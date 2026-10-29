"""Prévision de patrimoine, indépendance financière (FIRE) et simulateur de patrimoine."""
import math
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain import projections as proj
from app.schemas.insight import (
    FireResponse,
    WealthForecastPoint,
    WealthForecastResponse,
    WealthForecastSavingsMonth,
    WealthSimulationResponse,
)
from app.services.analytics import portfolio as portfolio_service
from app.services.analytics.investments.allocation import compute_patrimoine_allocation
from app.services.analytics.metrics import compute_kpi_history

logger = get_logger(__name__)


async def _observed_return(db: Session) -> tuple[float | None, set[int]]:
    """XIRR constaté des comptes valorisés par positions, et ces comptes (indisponible : None)."""
    try:
        overview = await portfolio_service.portfolio_overview(db)
        return overview.xirr_pct, {a.account_id for a in overview.accounts}
    except Exception:
        logger.warning("wealth_forecast: XIRR constaté indisponible", exc_info=True)
        return None, set()


def _balances(items: list[dict], measured_ids: set[int]) -> tuple[float, float, float]:
    """Soldes positifs : investissements mesurés (XIRR), non mesurés (relevés), autres comptes."""
    measured = unmeasured = other = 0.0
    for item in items:
        bal = float(item["balance_eur"])
        if bal <= 0:
            continue
        if item["type"] != "investissement":
            other += bal
        elif item["account_id"] in measured_ids:
            measured += bal
        else:
            unmeasured += bal
    return measured, unmeasured, other


async def compute_wealth_forecast(db: Session, years: int = 10, extra_monthly: float = 0.0,
                                  monthly_savings: float | None = None, investment_return_pct: float | None = None,
                                  savings_return_pct: float | None = None) -> WealthForecastResponse:
    """Patrimoine actuel (tous comptes actifs) + épargne mensuelle moyenne des 12 derniers mois complets, rendement
    des comptes valorisés par positions = XIRR constaté (modifiable), autres comptes à 0 % sauf saisie.
    `extra_monthly` ajoute un effort d'épargne hypothétique pour comparer.
    """
    allocation = await compute_patrimoine_allocation(db)
    current_wealth = float(allocation["total_patrimoine"])
    observed_pct, measured_ids = await _observed_return(db)
    measured, unmeasured, other = _balances(allocation["items"], measured_ids)
    breakdown = proj.return_breakdown(measured, unmeasured, other, observed_pct, investment_return_pct, savings_return_pct)
    annual_return_pct = proj.weighted_return(breakdown, measured + unmeasured + other)

    history = await compute_kpi_history(months_count=13, account_id=None, db=db)
    now = datetime.now()
    rows = proj.savings_window(history, now.year, now.month)
    computed_savings = sum(float(r["epargne_flow"]) for r in rows) / len(rows) if rows else 0.0
    avg_savings = computed_savings if monthly_savings is None else monthly_savings

    rate = proj.monthly_rate(annual_return_pct)
    base = proj.project_wealth(current_wealth, avg_savings, rate, years)
    boosted = proj.project_wealth(current_wealth, avg_savings + extra_monthly, rate, years)
    return WealthForecastResponse(
        current_wealth=round(current_wealth, 2),
        avg_monthly_savings=round(avg_savings, 2),
        months_used=len(rows),
        annual_return_pct=round(annual_return_pct, 2),
        years=years,
        extra_monthly=extra_monthly,
        final_base=round(base[-1], 2),
        final_boosted=round(boosted[-1], 2),
        gain_from_extra=round(boosted[-1] - base[-1], 2),
        points=[WealthForecastPoint(year=y, base=round(base[y], 2), boosted=round(boosted[y], 2)) for y in range(years + 1)],
        computed_monthly_savings=round(computed_savings, 2),
        observed_investment_return_pct=observed_pct,
        savings_overridden=monthly_savings is not None,
        savings_months=[
            WealthForecastSavingsMonth(
                label=r["label"],
                revenus=round(float(r["revenus"]), 2),
                depenses_reelles=round(float(r["revenus"]) - float(r["epargne_flow"]), 2),
                epargne_flow=round(float(r["epargne_flow"]), 2),
            )
            for r in rows
        ],
        return_breakdown=breakdown,
    )


async def compute_fire(db: Session, withdrawal_rate_pct: float = 4.0, inflation_pct: float = 2.0,
                       return_pct: float | None = None, monthly_savings: float | None = None,
                       annual_expenses: float | None = None) -> FireResponse:
    """Cible = dépenses annuelles ÷ taux de retrait ; dépenses, épargne et rendement nominal = ceux de la prévision
    de patrimoine (même fenêtre de 12 mois complets). Projection en euros d'aujourd'hui (rendement réel, cible constante).
    """
    forecast = await compute_wealth_forecast(db, years=1, extra_monthly=0.0, monthly_savings=monthly_savings)
    months = forecast.savings_months
    computed_expenses = sum(m.depenses_reelles for m in months) / len(months) * 12 if months else 0.0
    expenses = annual_expenses if annual_expenses is not None else computed_expenses
    nominal = return_pct if return_pct is not None else forecast.annual_return_pct
    real = proj.real_return(nominal, inflation_pct)
    rate = proj.monthly_rate(real)
    savings = forecast.avg_monthly_savings
    wealth = forecast.current_wealth
    target = proj.fire_target(expenses, withdrawal_rate_pct)
    years_to_fi = proj.years_to_fi(wealth, savings, expenses, rate, withdrawal_rate_pct)
    this_year = datetime.now().year
    return FireResponse(
        current_wealth=round(wealth, 2),
        annual_expenses=round(expenses, 2),
        expenses_overridden=annual_expenses is not None,
        withdrawal_rate_pct=withdrawal_rate_pct,
        target=round(target, 2),
        progress_pct=round(min(wealth / target * 100.0, 100.0), 1) if target > 0 else 100.0,
        monthly_savings=round(savings, 2),
        savings_overridden=monthly_savings is not None,
        nominal_return_pct=round(nominal, 2),
        inflation_pct=inflation_pct,
        real_return_pct=round(real, 2),
        months_used=forecast.months_used,
        years_to_fi=years_to_fi,
        fi_year=this_year + int(math.ceil(years_to_fi)) if years_to_fi is not None else None,
        points=proj.fire_points(wealth, savings, rate, target, years_to_fi, this_year),
        scenarios=proj.fire_scenarios(wealth, savings, expenses, rate, withdrawal_rate_pct),
    )


def compute_wealth_simulation(initial_capital: float, monthly_contribution: float, annual_return_pct: float,
                              years: int = 15, volatility_pct: float = 0.0, inflation_rate_pct: float = 0.0,
                              contribution_indexation_pct: float = 0.0, tax_rate_pct: float = 0.0,
                              tax_deferred: bool = True, events: str | None = None) -> WealthSimulationResponse:
    """Croissance avec versements, intérêts composés, inflation, fiscalité, indexation, événements et volatilité."""
    items = proj.simulate_wealth(
        initial_capital, monthly_contribution, annual_return_pct, years, volatility_pct, inflation_rate_pct,
        contribution_indexation_pct, tax_rate_pct, tax_deferred, proj.parse_events(events),
    )
    last_item = items[-1]
    return WealthSimulationResponse(
        items=items,
        total_final=last_item.total_value,
        total_interest=last_item.total_interest,
        total_contributions=last_item.total_contributions,
        total_final_real=last_item.total_value_real,
        total_tax_paid=last_item.total_tax_paid,
        pessimistic_final=last_item.total_value_p10,
        median_final=last_item.total_value_p50,
        optimistic_final=last_item.total_value_p90
    )
