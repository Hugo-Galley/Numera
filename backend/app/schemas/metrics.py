"""Réponses de `/analytics/{tags,expenses-by-category,top-merchants,account-flow-summary,kpi-history,timeseries,calendar}`."""
from pydantic import BaseModel


class TagSpending(BaseModel):
    id: int
    name: str
    color: str | None
    total_eur: float


class CategoryRef(BaseModel):
    id: int | None
    name: str
    icon: str | None
    color: str | None
    monthly_limit: float | None
    annual_limit: float | None


class CategoryExpense(BaseModel):
    category: CategoryRef
    total: float
    percentage: float


class ExpensesByCategory(BaseModel):
    month: int
    year: int
    total: float
    items: list[CategoryExpense]


class MerchantTotal(BaseModel):
    merchant: str
    total: float


class TopMerchants(BaseModel):
    month: int
    year: int
    items: list[MerchantTotal]


class AccountFlowSummary(BaseModel):
    currency: str
    monthly_net_flow: float
    prev_monthly_net_flow: float
    monthly_variation: float | None
    avg_expense: float


class KpiHistoryPoint(BaseModel):
    month: int
    year: int
    label: str
    base_currency: str
    revenus: float
    interets: float
    depenses: float
    depenses_reelles: float
    investissements: float
    epargne: float
    epargne_flow: float
    cash_flow: float
    taux_epargne: float | None


class BalancePoint(BaseModel):
    account_id: int
    date: str
    running_balance: float


class MonthlyFlow(BaseModel):
    month: int
    income: float
    expense: float
    burn_rate: float


class SalaryPoint(BaseModel):
    month: int
    salary: float


class Timeseries(BaseModel):
    year: int
    account_id: int | None
    monthly_flows: list[MonthlyFlow]
    balance_points: list[BalancePoint]
    salary_series: list[SalaryPoint]


class CalendarEvent(BaseModel):
    """Transaction réelle, opération de placement ou occurrence projetée d'une récurrence."""

    id: str
    date: str
    name: str
    amount: float
    type: str
    category_id: int | None = None
    is_projected: bool
    is_upcoming: bool
    currency: str
    account_id: int
    running_balance: float | None = None
    recurring_id: int | None = None
    ticker: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    logo: str | None = None


class CalendarDailyBalance(BaseModel):
    date: str
    balance: float


class Calendar(BaseModel):
    month: int
    year: int
    events: list[CalendarEvent]
    daily_balances: list[CalendarDailyBalance]
