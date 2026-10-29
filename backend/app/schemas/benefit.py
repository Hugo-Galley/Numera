from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import Amount


class BenefitBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    organization: str = Field(min_length=1, max_length=60)
    amount: Amount
    payment_day: int = Field(default=5, ge=1, le=31)
    match_pattern: str = Field(min_length=2, max_length=120)
    account_id: int | None = None
    start_date: date | None = None
    declaration_interval_months: int | None = Field(default=None, ge=1, le=12)
    next_declaration_date: date | None = None
    note: str | None = Field(default=None, max_length=255)
    active: bool = True


class BenefitCreate(BenefitBase):
    pass


class BenefitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    organization: str | None = Field(default=None, min_length=1, max_length=60)
    amount: Amount | None = None
    payment_day: int | None = Field(default=None, ge=1, le=31)
    match_pattern: str | None = Field(default=None, min_length=2, max_length=120)
    account_id: int | None = None
    start_date: date | None = None
    declaration_interval_months: int | None = Field(default=None, ge=1, le=12)
    next_declaration_date: date | None = None
    note: str | None = Field(default=None, max_length=255)
    active: bool | None = None


class BenefitDeclared(BaseModel):
    """Déclaration faite : l'échéance avance d'un intervalle ; `amount` = nouveau montant notifié (facultatif)."""
    amount: Amount | None = None


class BenefitPayment(BaseModel):
    transaction_id: int
    date: date
    amount: float
    merchant: str


class BenefitRead(BenefitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_name: str | None = None
    status: str  # received | pending | late | inactive
    expected_date: date  # versement attendu ce mois-ci
    next_payment_date: date
    last_payment: BenefitPayment | None = None
    amount_changed: bool  # dernier versement différent du montant attendu
    received_this_year: float
    payments: list[BenefitPayment]  # 12 derniers versements, du plus récent au plus ancien
    declaration_days_left: int | None = None  # < 0 : déclaration en retard


class BenefitSummary(BaseModel):
    monthly_expected_total: float
    received_this_year: float
    received_last_12_months: float
    late_count: int
    next_declaration: BenefitRead | None = None
