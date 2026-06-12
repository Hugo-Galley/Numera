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
    expenses: float
    real_expenses: float
    savings: float
    savings_rate: float
    burn_rate: float
    net_worth: float
    net_worth_change: float
    top_categories: List[dict]
    top_merchants: List[dict]
    comparison: MonthlyComparison
    insights: List[Insight]
    health_score: HealthScore
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
    status: str  # "active", "potential", "changed"


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


class WealthSimulationResponse(BaseModel):
    items: List[WealthSimulationPoint]
    total_final: float
    total_interest: float
    total_contributions: float


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
