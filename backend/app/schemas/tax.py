from typing import Literal

from pydantic import BaseModel, Field

Household = Literal["single", "couple"]


class TaxSettings(BaseModel):
    tmi_pct: float = 30.0
    prior_year_pro_income: float = 0.0
    household: Household = "single"


class TaxSettingsUpdate(BaseModel):
    tmi_pct: float | None = Field(default=None, ge=0, le=45)
    prior_year_pro_income: float | None = Field(default=None, ge=0)
    household: Household | None = None


class WrapperCard(BaseModel):
    kind: Literal["pea", "per", "cto", "assurance_vie", "livret_a"]
    account_id: int
    account_name: str
    opened_at: str | None = None
    current: float | None = None
    ceiling: float | None = None
    remaining: float | None = None
    used_pct: float | None = None
    age_years: float | None = None
    milestone_years: int | None = None
    milestone_reached: bool | None = None
    estimated_tax_saving: float | None = None
    allowance: float | None = None
    alerts: list[str] = []


class TaxOverview(BaseModel):
    year: int
    settings: TaxSettings
    wrappers: list[WrapperCard]
