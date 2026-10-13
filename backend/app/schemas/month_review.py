from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.category import BudgetAlert


class ReviewTransaction(BaseModel):
    id: int
    date: datetime
    merchant: str
    amount: float  # net des remboursements, devise du compte
    category_name: str | None = None
    is_exceptional: bool = False


class CategorizeStep(BaseModel):
    count: int
    total: float
    items: list[ReviewTransaction]


class AccountCheck(BaseModel):
    id: int
    name: str
    currency: str
    balance: float
    last_verified_at: datetime
    verified_since_month_end: bool


class AccountsStep(BaseModel):
    unverified_count: int
    accounts: list[AccountCheck]


class BudgetStep(BaseModel):
    income: float
    real_expenses: float
    savings: float
    savings_rate: float
    burn_rate: float
    exceptional_expenses: float
    real_expenses_excl_exceptional: float
    savings_excl_exceptional: float
    savings_rate_excl_exceptional: float
    burn_rate_excl_exceptional: float
    previous_real_expenses: float
    alerts: list[BudgetAlert]
    top_expenses: list[ReviewTransaction]


class ClosureRead(BaseModel):
    year: int
    month: int
    closed_at: datetime
    highlight: str | None = None
    tx_count: int
    income: float
    expenses: float
    unresolved_count: int

    model_config = {"from_attributes": True}


class MonthReviewRead(BaseModel):
    year: int
    month: int
    closed: bool
    closure: ClosureRead | None = None
    modified_since_close: bool
    categorize: CategorizeStep
    accounts: AccountsStep
    budget: BudgetStep


class CloseRequest(BaseModel):
    year: int = Field(ge=2000, le=2200)
    month: int = Field(ge=1, le=12)
    highlight: str | None = Field(default=None, max_length=500)
