from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TransferRuleBase(BaseModel):
    source_account_id: int
    dest_account_id: int
    pattern: str | None = Field(default=None, max_length=255)
    amount: float | None = Field(default=None, gt=0)
    amount_tolerance_pct: float = Field(default=1.0, ge=0, le=50)
    day_tolerance: int = Field(default=5, ge=0, le=30)
    is_active: bool = True


class TransferRuleCreate(TransferRuleBase):
    pass


class TransferRuleUpdate(BaseModel):
    source_account_id: int | None = None
    dest_account_id: int | None = None
    pattern: str | None = Field(default=None, max_length=255)
    amount: float | None = Field(default=None, gt=0)
    amount_tolerance_pct: float | None = Field(default=None, ge=0, le=50)
    day_tolerance: int | None = Field(default=None, ge=0, le=30)
    is_active: bool | None = None


class TransferRuleRead(TransferRuleBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransferLegPreview(BaseModel):
    id: int
    account_id: int
    date: datetime
    amount: float
    currency: str
    label: str | None = None


class TransferPairPreview(BaseModel):
    rule_id: int | None
    kind: str
    sortie: TransferLegPreview
    entree: TransferLegPreview
    day_gap: int


class TransferApplyResult(BaseModel):
    dry_run: bool
    count: int
    pairs: list[TransferPairPreview]
