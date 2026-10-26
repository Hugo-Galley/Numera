from datetime import datetime
from typing import Annotated, Literal
import re
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.category import CategoryRead
from app.schemas.types import Amount, Quantity, BoundedDatetime

LOGO_REF_RE = re.compile(r"^(si:[a-z0-9]{1,60}|file:[0-9a-f]{16}\.png)$")


def _check_logo(v: str | None) -> str | None:
    if v is not None and not LOGO_REF_RE.match(v):
        raise ValueError("invalid logo reference")
    return v


# Types bancaires + types d'investissement (compte titres ou achat programmé)
RecurringType = Literal[
    "Entree", "Sortie", "Interets",
    "versement", "retrait", "achat", "vente", "dividende",
]
RecurringFrequency = Literal["daily", "weekly", "monthly", "quarterly", "yearly"]
Month = Annotated[int, Field(ge=1, le=12)]


def _check_period(start: datetime | None, end: datetime | None) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("end_date doit être postérieure à start_date")


class RecurringTransactionBase(BaseModel):
    account_id: int
    name: str = Field(min_length=1, max_length=120)
    type: str  # Entree, Sortie, Interets
    amount: float = Field(ge=0)
    currency: str = "EUR"
    category_id: int | None = None
    frequency: str  # daily, weekly, monthly, quarterly, yearly
    day_of_month: int | None = None
    excluded_months: list[int] | None = None  # Months (1-12) to skip
    start_date: datetime
    end_date: datetime | None = None
    last_generated_date: datetime | None = None
    is_active: bool = True
    auto_generate: bool = False
    note: str | None = None
    transfer_to_account_id: int | None = None
    transfer_credit_day: int | None = Field(default=None, ge=1, le=31)
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None
    ticker: str | None = None
    isin: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    whole_shares: bool = False
    etf_profile_id: int | None = None
    logo: str | None = None

    _validate_logo = field_validator("logo")(_check_logo)


class RecurringTransactionCreate(RecurringTransactionBase):
    # Entrées strictes ; la lecture (Base) reste tolérante pour d'anciennes lignes.
    type: RecurringType
    amount: Amount
    frequency: RecurringFrequency
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    excluded_months: list[Month] | None = None
    start_date: BoundedDatetime
    end_date: BoundedDatetime | None = None
    quantity: Quantity | None = None
    unit_price: Quantity | None = None

    @model_validator(mode="after")
    def _validate_period(self):
        _check_period(self.start_date, self.end_date)
        return self

class RecurringTransactionUpdate(BaseModel):
    account_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: RecurringType | None = None
    amount: Amount | None = None
    currency: str | None = None
    category_id: int | None = None
    frequency: RecurringFrequency | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    excluded_months: list[Month] | None = None
    start_date: BoundedDatetime | None = None
    end_date: BoundedDatetime | None = None
    last_generated_date: datetime | None = None
    is_active: bool | None = None
    auto_generate: bool | None = None
    note: str | None = None
    transfer_to_account_id: int | None = None
    transfer_credit_day: int | None = Field(default=None, ge=1, le=31)
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None
    ticker: str | None = None
    isin: str | None = None
    quantity: Quantity | None = None
    unit_price: Quantity | None = None
    whole_shares: bool | None = None
    etf_profile_id: int | None = None
    logo: str | None = None

    _validate_logo = field_validator("logo")(_check_logo)

class RecurringTransactionRead(RecurringTransactionBase):
    id: int
    category: CategoryRead | None = None

    model_config = {"from_attributes": True}

    @field_validator("excluded_months", mode="before")
    @classmethod
    def parse_excluded_months(cls, v: str | list[int] | None) -> list[int] | None:
        """Convert CSV string from DB to list[int] for API response."""
        if v is None:
            return None
        if isinstance(v, str):
            if not v.strip():
                return None
            return [int(m) for m in v.split(",") if m.strip()]
        return v
