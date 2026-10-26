import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.recurring_transaction import _check_logo

LoanKind = Literal["immobilier", "auto", "consommation", "etudiant", "autre"]
PrepaymentMode = Literal["reduce_duration", "reduce_payment"]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Amount = Annotated[float, Field(gt=0, lt=1e9, allow_inf_nan=False)]
Rate = Annotated[float, Field(ge=0, le=50, allow_inf_nan=False)]
Months = Annotated[int, Field(ge=1, le=600)]
Insurance = Annotated[float, Field(ge=0, lt=1e6, allow_inf_nan=False)]


class LoanCreate(BaseModel):
    name: Name
    institution: str | None = Field(default=None, max_length=64)
    logo: str | None = None
    color: str | None = None
    kind: LoanKind = "autre"
    principal: Amount
    annual_rate_pct: Rate
    duration_months: Months
    start_date: dt.date
    insurance_monthly: Insurance = 0.0

    _validate_logo = field_validator("logo")(_check_logo)


class LoanUpdate(BaseModel):
    name: Name | None = None
    institution: str | None = Field(default=None, max_length=64)
    logo: str | None = None
    color: str | None = None
    kind: LoanKind | None = None
    principal: Amount | None = None
    annual_rate_pct: Rate | None = None
    duration_months: Months | None = None
    start_date: dt.date | None = None
    insurance_monthly: Insurance | None = None

    _validate_logo = field_validator("logo")(_check_logo)


class PrepaymentCreate(BaseModel):
    date: dt.date
    amount: Amount
    mode: PrepaymentMode = "reduce_duration"


class PrepaymentRead(PrepaymentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LoanSummary(BaseModel):
    id: int
    account_id: int
    name: str
    institution: str | None
    logo: str | None
    color: str | None
    kind: str
    principal: float
    annual_rate_pct: float
    duration_months: int
    start_date: dt.date
    insurance_monthly: float
    monthly_payment: float  # mensualité courante, hors assurance
    remaining_principal: float
    repaid_pct: float
    end_date: dt.date
    total_interest: float
    total_insurance: float
    total_cost: float  # intérêts + assurance
    prepayments: list[PrepaymentRead]


class ScheduleRowRead(BaseModel):
    n: int
    date: dt.date
    payment: float
    interest: float
    principal: float
    insurance: float
    remaining: float
    prepayment: float


class SimulationRequest(PrepaymentCreate):
    pass


class SimulationResult(BaseModel):
    interest_saved: float
    total_interest_before: float
    total_interest_after: float
    new_end_date: dt.date
    months_saved: int
    new_payment: float
    max_penalty: float
