from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import Amount


class ProvisionBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: Amount
    interval_months: int = Field(default=12, ge=1, le=60)
    due_date: date
    category_id: int | None = None
    account_id: int | None = None
    note: str | None = Field(default=None, max_length=255)
    active: bool = True


class ProvisionCreate(ProvisionBase):
    pass


class ProvisionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    amount: Amount | None = None
    interval_months: int | None = Field(default=None, ge=1, le=60)
    due_date: date | None = None
    category_id: int | None = None
    account_id: int | None = None
    note: str | None = Field(default=None, max_length=255)
    active: bool | None = None


class ProvisionPayment(BaseModel):
    date: date
    amount: float  # EUR, net des remboursements


class ProvisionRead(ProvisionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_name: str | None = None
    account_name: str | None = None
    next_due: date
    previous_due: date
    months_left: int  # mois pleins restants avant l'échéance (au moins 1)
    monthly_amount: float  # rythme de croisière : montant ÷ intervalle
    target_now: float  # ce qui devrait déjà être de côté aujourd'hui
    monthly_needed: float  # à mettre de côté chaque mois pour être prêt à temps (depuis le constitué)
    funded: float | None = None  # part constituée (compte rattaché), None sans compte
    status: str  # on_track | behind | untracked | inactive
    last_payment: ProvisionPayment | None = None


class ProvisionAccountFunding(BaseModel):
    account_id: int
    account_name: str
    balance: float
    target_now: float
    gap: float  # > 0 : il manque cette somme sur le compte


class ProvisionSummary(BaseModel):
    monthly_total: float
    target_now_total: float
    upcoming: list[ProvisionRead]  # échéances des 90 prochains jours
    accounts: list[ProvisionAccountFunding]
    behind_count: int
