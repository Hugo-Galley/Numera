from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.category import CategoryRead

class RecurringTransactionBase(BaseModel):
    account_id: int
    name: str = Field(min_length=1, max_length=120)
    type: str  # Entree, Sortie, Interets
    amount: float = Field(gt=0)
    currency: str = "EUR"
    category_id: int | None = None
    frequency: str  # monthly, weekly, quarterly, yearly
    day_of_month: int | None = None
    start_date: datetime
    end_date: datetime | None = None
    last_generated_date: datetime | None = None
    is_active: bool = True
    auto_generate: bool = False
    note: str | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None

class RecurringTransactionCreate(RecurringTransactionBase):
    pass

class RecurringTransactionUpdate(BaseModel):
    account_id: int | None = None
    name: str | None = None
    type: str | None = None
    amount: float | None = None
    currency: str | None = None
    category_id: int | None = None
    frequency: str | None = None
    day_of_month: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    last_generated_date: datetime | None = None
    is_active: bool | None = None
    auto_generate: bool | None = None
    note: str | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None

class RecurringTransactionRead(RecurringTransactionBase):
    id: int
    category: CategoryRead | None = None

    model_config = {"from_attributes": True}
