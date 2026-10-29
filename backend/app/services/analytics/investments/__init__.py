"""Investissements : vue d'ensemble, détail d'un compte, répartitions et projections."""
from app.services.analytics.investments.account import compute_investment_account, compute_performance_history
from app.services.analytics.investments.allocation import (
    compute_allocation,
    compute_allocation_advanced,
    compute_allocation_suggestions,
    compute_patrimoine_allocation,
)
from app.services.analytics.investments.projections import compute_fire, compute_wealth_forecast, compute_wealth_simulation
from app.services.analytics.investments.summary import compute_investments

__all__ = [
    "compute_allocation",
    "compute_allocation_advanced",
    "compute_allocation_suggestions",
    "compute_fire",
    "compute_investment_account",
    "compute_investments",
    "compute_patrimoine_allocation",
    "compute_performance_history",
    "compute_wealth_forecast",
    "compute_wealth_simulation",
]
