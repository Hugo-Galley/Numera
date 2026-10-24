from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.category import CategoryRead
from app.schemas.tag import TagRead
from app.schemas.merchant import MerchantRead
from app.schemas.types import AmountOrZero, Amount, BoundedDatetime


class TransactionBase(BaseModel):
    account_id: int
    date: BoundedDatetime
    type: str
    merchant: str = Field(min_length=1, max_length=120)
    merchant_id: int | None = None
    category_id: int | None = None
    amount: AmountOrZero
    currency: str = "EUR"
    original_amount: AmountOrZero | None = None
    note: str | None = None
    is_recurring: bool = False
    recurring_transaction_id: int | None = None
    is_transfer: bool = False
    is_transfer_ignored: bool = False
    linked_transaction_id: int | None = None
    linked_investment_transaction_id: int | None = None
    custom_icon: str | None = None
    custom_color: str | None = None
    is_exceptional: bool = False


class TransactionCreate(TransactionBase):
    tag_ids: list[int] | None = None


class TransactionUpdate(BaseModel):
    date: BoundedDatetime | None = None
    type: str | None = None
    merchant: str | None = Field(default=None, min_length=1, max_length=120)
    merchant_id: int | None = None
    category_id: int | None = None
    amount: AmountOrZero | None = None
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
    is_exceptional: bool | None = None
    tag_ids: list[int] | None = None


class TransactionBulkDelete(BaseModel):
    ids: list[int]


class TransactionBulkDeleteResult(BaseModel):
    deleted: int


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
    link_origin: str | None = None
    transfer_rule_id: int | None = None
    transfer_credit_due: datetime | None = None
    recurring_logo: str | None = None
    linked_account_id: int | None = None
    reimbursement_offset: float = 0.0
    reimbursement_expected: float = 0.0
    has_claims: bool = False
    category: CategoryRead | None = None
    merchant_obj: MerchantRead | None = Field(None, alias="merchant_obj")
    tags: list[TagRead] = []

    model_config = {"from_attributes": True, "populate_by_name": True}


class TransferCandidate(BaseModel):
    sortie_id: int
    other_id: int
    type: str  # regular | investment
    account_id: int
    date: datetime
    amount: float
    currency: str
    label: str | None = None
    day_gap: int
    amount_gap_pct: float


class TransferCounterpartCreate(BaseModel):
    account_id: int
    date: BoundedDatetime | None = None
    amount: Amount | None = None  # devise du compte de destination


class TransferCounterpartRead(BaseModel):
    id: int
    type: str  # regular | investment
