from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.category import CategoryRead
from app.schemas.tag import TagRead
from app.schemas.merchant import MerchantRead


class TransactionBase(BaseModel):
    account_id: int
    date: datetime
    type: str
    merchant: str = Field(min_length=1, max_length=120)
    merchant_id: int | None = None
    category_id: int | None = None
    amount: float = Field(ge=0)
    currency: str = "EUR"
    original_amount: float | None = None
    note: str | None = None
    is_recurring: bool = False
    recurring_transaction_id: int | None = None
    is_transfer: bool = False
    is_transfer_ignored: bool = False
    linked_transaction_id: int | None = None
    linked_investment_transaction_id: int | None = None
    custom_icon: str | None = None
    custom_color: str | None = None


class TransactionCreate(TransactionBase):
    tag_ids: list[int] | None = None


class TransactionUpdate(BaseModel):
    date: datetime | None = None
    type: str | None = None
    merchant: str | None = None
    merchant_id: int | None = None
    category_id: int | None = None
    amount: float | None = None
    currency: str | None = None
    note: str | None = None
    is_recurring: bool | None = None
    recurring_transaction_id: int | None = None
    is_transfer: bool | None = None
    is_transfer_ignored: bool | None = None
    linked_transaction_id: int | None = None
    linked_investment_transaction_id: int | None = None
    custom_icon: str | None = None
    custom_color: str | None = None
    tag_ids: list[int] | None = None


class TransactionBulkUpdate(BaseModel):
    ids: list[int]
    category_id: int | None = None
    merchant_id: int | None = None
    is_recurring: bool | None = None
    type: str | None = None
    merchant: str | None = None
    tag_ids: list[int] | None = None


class TransactionRead(TransactionBase):
    id: int
    month_label: str
    running_balance: float
    is_subscription_ignored: bool = False
    is_transfer: bool = False
    is_transfer_ignored: bool = False
    linked_transaction_id: int | None = None
    linked_investment_transaction_id: int | None = None
    category: CategoryRead | None = None
    merchant_obj: MerchantRead | None = Field(None, alias="merchant_obj")
    tags: list[TagRead] = []

    model_config = {"from_attributes": True, "populate_by_name": True}
