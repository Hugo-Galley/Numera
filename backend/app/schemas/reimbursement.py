from datetime import datetime

from pydantic import BaseModel, Field


class ClaimCreate(BaseModel):
    transaction_id: int
    debtor: str = Field(min_length=1, max_length=120)
    expected_amount: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)


class ClaimUpdate(BaseModel):
    debtor: str | None = Field(default=None, min_length=1, max_length=120)
    expected_amount: float | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=255)


class AllocationCreate(BaseModel):
    entree_id: int
    amount: float | None = Field(default=None, gt=0)


class ExpenseRef(BaseModel):
    id: int
    account_id: int
    date: datetime
    label: str
    amount: float


class AllocationRead(BaseModel):
    id: int
    entree_id: int
    amount: float
    date: datetime | None = None
    label: str | None = None
    account_id: int | None = None


class ClaimRead(BaseModel):
    id: int
    debtor: str
    expected_amount: float
    received: float
    remaining: float
    note: str | None = None
    created_at: datetime
    currency: str
    expense: ExpenseRef
    allocations: list[AllocationRead]


class DebtorDue(BaseModel):
    debtor: str
    claims: int
    due: float


class ReimbursementSummary(BaseModel):
    total_due: float
    debtors: list[DebtorDue]


class CandidateRead(BaseModel):
    id: int
    account_id: int
    date: datetime
    label: str
    amount: float
    available: float
    day_gap: int
    debtor_match: bool


class EntryAllocationRead(BaseModel):
    id: int
    claim_id: int
    amount: float
    debtor: str


class EntryClaims(BaseModel):
    entree_id: int
    amount: float
    available: float
    open_claims: list[ClaimRead]
    allocations: list[EntryAllocationRead]
