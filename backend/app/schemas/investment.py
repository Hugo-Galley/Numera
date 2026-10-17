from pydantic import BaseModel, Field

from app.core.time import NaiveUTCDatetime


class InvestmentTransactionBase(BaseModel):
    account_id: int
    date: NaiveUTCDatetime
    type: str
    amount: float = Field(gt=0)
    currency: str = "EUR"
    original_amount: float | None = None
    note: str | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None
    ticker: str | None = None
    isin: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    price_currency: str | None = None
    fees: float | None = Field(default=None, ge=0)
    withholding_tax: float | None = Field(default=None, ge=0)
    reinvested: bool = False
    etf_profile_id: int | None = None
    is_transfer: bool = False
    is_transfer_ignored: bool = False
    linked_transaction_id: int | None = None


class InvestmentTransactionCreate(InvestmentTransactionBase):
    pass


class InvestmentTransactionRead(InvestmentTransactionBase):
    id: int
    reinvest_of_id: int | None = None

    model_config = {"from_attributes": True}


class InvestmentTransactionUpdate(BaseModel):
    date: NaiveUTCDatetime | None = None
    type: str | None = None
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = None
    note: str | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None
    ticker: str | None = None
    isin: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    price_currency: str | None = None
    fees: float | None = Field(default=None, ge=0)
    withholding_tax: float | None = Field(default=None, ge=0)
    reinvested: bool | None = None
    etf_profile_id: int | None = None
    is_transfer: bool | None = None
    is_transfer_ignored: bool | None = None
    linked_transaction_id: int | None = None


class BalanceSnapshotBase(BaseModel):
    account_id: int
    date: NaiveUTCDatetime
    current_value: float = Field(ge=0)
    note: str | None = None
    is_zero_point: bool = False


class BalanceSnapshotCreate(BalanceSnapshotBase):
    pass


class BalanceSnapshotRead(BalanceSnapshotBase):
    id: int

    model_config = {"from_attributes": True}


class BalanceSnapshotUpdate(BaseModel):
    date: NaiveUTCDatetime | None = None
    current_value: float | None = Field(default=None, ge=0)
    note: str | None = None
    is_zero_point: bool | None = None


class SetZeroPointRequest(BaseModel):
    account_id: int
    current_value: float | None = Field(default=None, ge=0)
    date: NaiveUTCDatetime | None = None
    note: str | None = None
