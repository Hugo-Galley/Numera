"""Réponses de `/analytics/{budget,resilience,budget-period}`."""
from pydantic import BaseModel


class BudgetOverview(BaseModel):
    month: int | None
    year: int | None
    base_currency: str
    revenus_totaux: float
    interets_totaux: float
    depenses_totales: float
    depenses_reelles: float
    investissements_du_mois: float
    revenus_apres_depenses: float
    epargne_realisee: float
    reste_tresorerie: float
    taux_epargne: float
    burn_rate: float
    patrimoine_net_total: float
    epargne_total: float
    solde_actuel: float


class Resilience(BaseModel):
    months: float | None  # None sans dépense réelle moyenne
    liquid_savings: float
    avg_monthly_real_expenses: float
    months_used: int


class BudgetPeriodCurrent(BaseModel):
    year: int
    month: int


class BudgetPeriod(BaseModel):
    year: int
    month: int
    mode: str
    start: str
    end: str
    current: BudgetPeriodCurrent
