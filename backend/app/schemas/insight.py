from typing import Any, Optional

from pydantic import BaseModel, Field


class MetricDetail(BaseModel):
    name: str
    score: float
    max_score: float
    value: float
    unit: str
    status: str  # "good", "warning", "critical"


class HealthScore(BaseModel):
    total_score: float  # 0-100
    metrics: list[MetricDetail]


class Insight(BaseModel):
    type: str  # "anomaly", "advice", "positive"
    key: str  # identifiant stable (nature + mois + objet), clé d'un insight écarté
    title: str
    description: str
    severity: str  # "low", "medium", "high"
    value: float | None = None
    unit: str = "€"  # unité de `value` : « € », « % » ou « mois »
    category_id: int | None = None


class IntelligentInsights(BaseModel):
    health_score: HealthScore
    insights: list[Insight]


class MonthlyComparison(BaseModel):
    income_diff: float
    income_diff_pct: float
    expenses_diff: float
    expenses_diff_pct: float
    savings_diff: float
    savings_diff_pct: float


class MonthlyReport(BaseModel):
    month: int
    year: int
    income: float
    expenses: float = Field(description="Sorties totales, sorties vers épargne/investissement non liées comprises")
    real_expenses: float = Field(description="Dépenses de consommation (hors épargne, investissement et virements)")
    savings: float = Field(description="Revenus − dépenses réelles : numérateur du taux d'épargne")
    savings_rate: float
    burn_rate: float
    net_worth: float
    net_worth_change: float
    top_categories: list[dict[str, Any]]
    top_merchants: list[dict[str, Any]]
    comparison: MonthlyComparison
    insights: list[Insight]
    health_score: HealthScore
    exceptional_expenses: float
    real_expenses_excl_exceptional: float
    savings_excl_exceptional: float
    savings_rate_excl_exceptional: float
    burn_rate_excl_exceptional: float
    money_flow: Optional["MoneyFlowReport"] = None


class ProjectionPoint(BaseModel):
    date: str
    balance: float
    change: float
    label: str | None = None


class ProjectionEvent(BaseModel):
    date: str
    name: str
    amount: float
    type: str  # "recurring", "scheduled"
    is_income: bool
    transaction_id: int | None = None  # "scheduled" : la transaction saisie à venir
    possible_duplicate: bool = False  # saisie à venir proche d'une échéance récurrente de même montant


class CashflowProjection(BaseModel):
    points: list[ProjectionPoint]
    events: list[ProjectionEvent]
    current_balance: float
    projected_balance: float
    low_point: float
    low_point_date: str | None
    days: int


class SubscriptionInsight(BaseModel):
    name: str
    category_name: str
    amount: float
    frequency: str  # "monthly", "annual", "other"
    monthly_cost: float
    annual_cost: float
    last_occurrence: str | None
    next_occurrence: str | None
    is_recurring_entity: bool
    status: str  # "active", "lapsed" (plus prélevée depuis 2 périodes), "paused", "potential"
    logo: str | None = None
    flow_type: str = "Sortie"  # type de la récurrence (Sortie, Entree, versement…)
    # Faux pour une récurrence en pause, un virement ou une alimentation d'épargne/d'investissement :
    # elle reste listée mais n'entre pas dans les totaux d'abonnements.
    counts_in_total: bool = True
    in_kind_total: bool = False  # compte dans le total de son onglet (`totals_by_kind`)
    kind: str = "subscriptions"  # onglet : subscriptions, investments (épargne) ou other (flux qui ne sont pas des sorties)


class SubscriptionIgnore(BaseModel):
    merchant: str
    amount: float


class SubscriptionPriceChange(BaseModel):
    id: str  # identifiant stable, repris par le Centre d'Actions
    name: str
    account_id: int
    currency: str  # devise du compte
    frequency: str  # monthly | quarterly | yearly
    old_amount: float
    new_amount: float
    delta: float
    delta_pct: float
    annual_impact: float  # surcoût sur un an, devise du compte
    changed_on: str


class CostTotals(BaseModel):
    monthly: float
    annual: float


class SubscriptionsResponse(BaseModel):
    subscriptions: list[SubscriptionInsight]
    total_monthly: float
    total_annual: float
    # Totaux des récurrences confirmées par onglet (`kind`), mêmes règles que l'affichage de la liste
    totals_by_kind: dict[str, CostTotals] = {}
    price_changes: list[SubscriptionPriceChange] = Field(default_factory=list)


class WealthSimulationPoint(BaseModel):
    year: int
    initial_capital: float
    total_contributions: float
    total_interest: float
    total_value: float
    total_value_real: float | None = None
    total_value_p10: float | None = None
    total_value_p50: float | None = None
    total_value_p90: float | None = None
    total_value_p10_real: float | None = None
    total_value_p50_real: float | None = None
    total_value_p90_real: float | None = None
    total_tax_paid: float | None = 0.0
    event_applied: str | None = None


class WealthSimulationResponse(BaseModel):
    items: list[WealthSimulationPoint]
    total_final: float
    total_interest: float
    total_contributions: float
    total_final_real: float | None = None
    total_tax_paid: float | None = None
    pessimistic_final: float | None = None
    median_final: float | None = None
    optimistic_final: float | None = None


class WealthForecastPoint(BaseModel):
    year: int
    base: float
    boosted: float


class WealthForecastSavingsMonth(BaseModel):
    label: str
    revenus: float
    depenses_reelles: float
    epargne_flow: float


class WealthForecastReturnItem(BaseModel):
    type: str
    balance: float
    rate_pct: float
    source: str  # observed | manual | none


class WealthForecastResponse(BaseModel):
    current_wealth: float
    avg_monthly_savings: float
    months_used: int
    annual_return_pct: float
    years: int
    extra_monthly: float
    final_base: float
    final_boosted: float
    gain_from_extra: float
    points: list[WealthForecastPoint]
    computed_monthly_savings: float = 0.0
    observed_investment_return_pct: float | None = None
    savings_overridden: bool = False
    savings_months: list[WealthForecastSavingsMonth] = []
    return_breakdown: list[WealthForecastReturnItem] = []


class MoneyFlowItem(BaseModel):
    name: str
    amount: float
    category: str | None = None
    is_recurring: bool = False


class MoneyFlowBlock(BaseModel):
    amount: float
    percentage: float  # % of income
    diff_prev_month: float
    diff_prev_month_pct: float


class MoneyFlowReport(BaseModel):
    month: int
    year: int
    income: float
    fixed_charges: MoneyFlowBlock
    variable_expenses: MoneyFlowBlock
    savings: MoneyFlowBlock
    investments: MoneyFlowBlock
    remainder: MoneyFlowBlock

    top_fixed: list[MoneyFlowItem]
    top_variable: list[MoneyFlowItem]
    top_savings: list[MoneyFlowItem]
    top_investments: list[MoneyFlowItem]


class DataAuditIssue(BaseModel):
    id: str
    type: str
    severity: str  # "low", "medium", "high"
    title: str
    description: str
    count: int = 1
    amount: float | None = None
    action_label: str | None = None
    action_url: str | None = None
    samples: list[dict[str, Any]] = Field(default_factory=list)


class DataAuditSummary(BaseModel):
    total_issues: int
    high_count: int
    medium_count: int
    low_count: int
    total_transactions: int
    active_accounts: int
    checked_at: str


class DataAuditResponse(BaseModel):
    summary: DataAuditSummary
    issues: list[DataAuditIssue]


class ActionItem(BaseModel):
    id: str
    type: str  # "audit", "budget", "rule", "subscription"
    severity: str  # "low", "medium", "high"
    title: str
    description: str
    action_label: str | None = None
    action_url: str | None = None
    action_type: str  # "link", "modal_categorize", "modal_rule", "modal_snapshot", "modal_merchant"
    metadata: dict[str, Any] | None = Field(default_factory=dict)
    samples: list[dict[str, Any]] = Field(default_factory=list)


class ActionCenterSummary(BaseModel):
    total_actions: int
    high_priority: int
    medium_priority: int
    low_priority: int
    checked_at: str


class ActionCenterResponse(BaseModel):
    summary: ActionCenterSummary
    actions: list[ActionItem]


class FireScenario(BaseModel):
    label: str
    monthly_savings: float
    annual_expenses: float
    years_to_fi: float | None


class FirePoint(BaseModel):
    year: int
    wealth: float  # euros d'aujourd'hui (rendement réel)
    target: float


class FireResponse(BaseModel):
    current_wealth: float
    annual_expenses: float  # dépenses réelles moyennes × 12 (ou saisie)
    expenses_overridden: bool
    withdrawal_rate_pct: float
    target: float  # patrimoine nécessaire = dépenses annuelles ÷ taux de retrait
    progress_pct: float
    monthly_savings: float
    savings_overridden: bool
    nominal_return_pct: float
    inflation_pct: float
    real_return_pct: float
    months_used: int
    years_to_fi: float | None  # None : objectif non atteint en 80 ans
    fi_year: int | None
    points: list[FirePoint]
    scenarios: list[FireScenario]
