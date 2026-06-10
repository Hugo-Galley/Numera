from datetime import datetime

from pydantic import BaseModel, Field


class InvestmentTransactionBase(BaseModel):
    account_id: int
    date: datetime
    type: str
    amount: float = Field(gt=0)
    currency: str = "EUR"
    original_amount: float | None = None
    note: str | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None
    is_transfer: bool = False
    is_transfer_ignored: bool = False
    linked_transaction_id: int | None = None


class InvestmentTransactionCreate(InvestmentTransactionBase):
    pass


class InvestmentTransactionRead(InvestmentTransactionBase):
    id: int

    model_config = {"from_attributes": True}


class InvestmentTransactionUpdate(BaseModel):
    date: datetime | None = None
    type: str | None = None
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = None
    note: str | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None
    is_transfer: bool | None = None
    is_transfer_ignored: bool | None = None
    linked_transaction_id: int | None = None


class BalanceSnapshotBase(BaseModel):
    account_id: int
    date: datetime
    current_value: float = Field(ge=0)
    note: str | None = None
    is_zero_point: bool = False


class BalanceSnapshotCreate(BalanceSnapshotBase):
    pass


class BalanceSnapshotRead(BalanceSnapshotBase):
    id: int

    model_config = {"from_attributes": True}


class BalanceSnapshotUpdate(BaseModel):
    date: datetime | None = None
    current_value: float | None = Field(default=None, ge=0)
    note: str | None = None
    is_zero_point: bool | None = None


class SetZeroPointRequest(BaseModel):
    account_id: int
    current_value: float | None = Field(default=None, ge=0)
    date: datetime | None = None
    note: str | None = None
