from pydantic import BaseModel, Field
from typing import List, Optional


class MetricDetail(BaseModel):
    name: str
    score: float
    max_score: float
    value: float
    unit: str
    status: str  # "good", "warning", "critical"


class HealthScore(BaseModel):
    total_score: float  # 0-100
    metrics: List[MetricDetail]


class Insight(BaseModel):
    type: str  # "anomaly", "advice", "positive"
    title: str
    description: str
    severity: str  # "low", "medium", "high"
    value: Optional[float] = None
    unit: str = "€"  # unité de `value` : « € », « % » ou « mois »
    category_id: Optional[int] = None


class IntelligentInsights(BaseModel):
    health_score: HealthScore
    insights: List[Insight]


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
    top_categories: List[dict]
    top_merchants: List[dict]
    comparison: MonthlyComparison
    insights: List[Insight]
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
    label: Optional[str] = None


class ProjectionEvent(BaseModel):
    date: str
    name: str
    amount: float
    type: str  # "recurring", "scheduled"
    is_income: bool


class CashflowProjection(BaseModel):
    points: List[ProjectionPoint]
    events: List[ProjectionEvent]
    current_balance: float
    projected_balance: float
    low_point: float
    low_point_date: Optional[str]
    days: int


class SubscriptionInsight(BaseModel):
    name: str
    category_name: str
    amount: float
    frequency: str  # "monthly", "annual", "other"
    monthly_cost: float
    annual_cost: float
    last_occurrence: Optional[str]
    next_occurrence: Optional[str]
    is_recurring_entity: bool
    status: str  # "active", "lapsed" (plus prélevée depuis 2 périodes), "paused", "potential"
    logo: Optional[str] = None
    flow_type: str = "Sortie"  # type de la récurrence (Sortie, Entree, versement…)
    # Faux pour une récurrence en pause, un virement ou une alimentation d'épargne/d'investissement :
    # elle reste listée mais n'entre pas dans les totaux d'abonnements.
    counts_in_total: bool = True


class SubscriptionIgnore(BaseModel):
    merchant: str
    amount: float


class SubscriptionsResponse(BaseModel):
    subscriptions: List[SubscriptionInsight]
    total_monthly: float
    total_annual: float


class WealthSimulationPoint(BaseModel):
    year: int
    initial_capital: float
    total_contributions: float
    total_interest: float
    total_value: float
    total_value_real: Optional[float] = None
    total_value_p10: Optional[float] = None
    total_value_p50: Optional[float] = None
    total_value_p90: Optional[float] = None
    total_value_p10_real: Optional[float] = None
    total_value_p50_real: Optional[float] = None
    total_value_p90_real: Optional[float] = None
    total_tax_paid: Optional[float] = 0.0
    event_applied: Optional[str] = None


class WealthSimulationResponse(BaseModel):
    items: List[WealthSimulationPoint]
    total_final: float
    total_interest: float
    total_contributions: float
    total_final_real: Optional[float] = None
    total_tax_paid: Optional[float] = None
    pessimistic_final: Optional[float] = None
    median_final: Optional[float] = None
    optimistic_final: Optional[float] = None


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
    points: List[WealthForecastPoint]
    computed_monthly_savings: float = 0.0
    observed_investment_return_pct: Optional[float] = None
    savings_overridden: bool = False
    savings_months: List[WealthForecastSavingsMonth] = []
    return_breakdown: List[WealthForecastReturnItem] = []


class MoneyFlowItem(BaseModel):
    name: str
    amount: float
    category: Optional[str] = None
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
    
    top_fixed: List[MoneyFlowItem]
    top_variable: List[MoneyFlowItem]
    top_savings: List[MoneyFlowItem]
    top_investments: List[MoneyFlowItem]


class DataAuditIssue(BaseModel):
    id: str
    type: str
    severity: str  # "low", "medium", "high"
    title: str
    description: str
    count: int = 1
    amount: Optional[float] = None
    action_label: Optional[str] = None
    action_url: Optional[str] = None
    samples: List[dict] = Field(default_factory=list)


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
    issues: List[DataAuditIssue]


class ActionItem(BaseModel):
    id: str
    type: str  # "audit", "budget", "rule", "subscription"
    severity: str  # "low", "medium", "high"
    title: str
    description: str
    action_label: Optional[str] = None
    action_url: Optional[str] = None
    action_type: str  # "link", "modal_categorize", "modal_rule", "modal_snapshot", "modal_merchant"
    metadata: Optional[dict] = Field(default_factory=dict)
    samples: List[dict] = Field(default_factory=list)


class ActionCenterSummary(BaseModel):
    total_actions: int
    high_priority: int
    medium_priority: int
    low_priority: int
    checked_at: str


class ActionCenterResponse(BaseModel):
    summary: ActionCenterSummary
    actions: List[ActionItem]


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
