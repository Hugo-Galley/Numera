from pydantic import BaseModel


class WrappedMonth(BaseModel):
    month: int
    income: float
    real_expenses: float
    saved: float


class WrappedCategory(BaseModel):
    name: str
    icon: str | None = None
    color: str | None = None
    total: float
    percentage: float
    work_hours: float | None = None


class WrappedMerchant(BaseModel):
    merchant: str
    total: float
    work_hours: float | None = None


class WrappedExpense(BaseModel):
    merchant: str
    amount: float
    date: str
    category: str | None = None
    work_hours: float | None = None


class WrappedSubscription(BaseModel):
    name: str
    monthly_cost: float


class WrappedTotals(BaseModel):
    """Chiffres comparables d'une année à l'autre (sur la même période)."""

    income: float
    real_expenses: float
    saved: float
    savings_rate: float
    invested: float
    dividends: float
    net_worth_start: float
    net_worth_end: float
    net_worth_change: float
    subscriptions_cost: float
    expense_count: int


class WrappedComparison(BaseModel):
    year: int
    totals: WrappedTotals
    income_change_pct: float | None
    real_expenses_change_pct: float | None
    savings_rate_change_pts: float
    net_worth_change_diff: float
    invested_change_pct: float | None


class WrappedReport(BaseModel):
    year: int
    available_years: list[int]
    has_data: bool
    is_partial: bool
    months_covered: int
    totals: WrappedTotals
    months: list[WrappedMonth]
    most_expensive_month: WrappedMonth | None
    thriftiest_month: WrappedMonth | None
    top_categories: list[WrappedCategory]
    top_merchants: list[WrappedMerchant]
    biggest_expense: WrappedExpense | None
    hourly_rate: float | None
    real_expenses_work_hours: float | None
    net_worth_change_pct: float | None
    new_subscriptions: list[WrappedSubscription]
    stopped_subscriptions: list[WrappedSubscription]
    stopped_subscriptions_yearly_saving: float
    previous: WrappedComparison | None
