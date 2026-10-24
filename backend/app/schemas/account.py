from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.recurring_transaction import _check_logo


TaxWrapper = Literal["pea", "per", "cto", "assurance_vie", "livret_a", "livret_jeune", "pee"]
# Types reconnus par les calculs ; un type inconnu (ex. « bank ») était classé au hasard selon les vues.
# La lecture reste en `str` pour ne pas casser d'anciens comptes déjà enregistrés avec un autre type.
AccountType = Literal["courant", "epargne", "investissement", "assurance_vie"]


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: str
    color: str | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None
    institution: str | None = None
    logo: str | None = None
    is_main: bool = False
    fonds_euros_pct: float | None = None
    fonds_investis_pct: float | None = None
    valuation_mode: Literal["positions", "snapshot"] = "positions"
    tax_wrapper: TaxWrapper | None = None
    opened_at: date | None = None

    _validate_logo = field_validator("logo")(_check_logo)


class AccountCreate(AccountBase):
    type: AccountType
    currency: str = "EUR"


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: AccountType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    color: str | None = None
    active: bool | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None
    institution: str | None = None
    logo: str | None = None
    is_main: bool | None = None
    fonds_euros_pct: float | None = None
    fonds_investis_pct: float | None = None
    valuation_mode: Literal["positions", "snapshot"] | None = None
    tax_wrapper: TaxWrapper | None = None
    opened_at: date | None = None

    _validate_logo = field_validator("logo")(_check_logo)


class AccountRead(AccountBase):
    id: int
    currency: str
    active: bool
    created_at: datetime
    last_verified_at: datetime
    balance: float = 0.0

    model_config = {"from_attributes": True}
