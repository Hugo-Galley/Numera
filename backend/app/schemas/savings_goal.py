from datetime import date
from pydantic import BaseModel, Field


class SavingsGoalBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: float = Field(gt=0)
    keyword: str | None = Field(None, max_length=50)
    icon: str | None = None
    color: str | None = None
    deadline: date | None = None
    account_id: int | None = None
    category_id: int | None = None


class SavingsGoalCreate(SavingsGoalBase):
    pass


class SavingsGoalUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    target_amount: float | None = Field(None, gt=0)
    keyword: str | None = Field(None, max_length=50)
    icon: str | None = None
    color: str | None = None
    deadline: date | None = None
    account_id: int | None = None
    category_id: int | None = None


class SavingsGoalProgress(SavingsGoalBase):
    id: int
    current_amount: float
    percentage: float
    monthly_required: float | None = None
    status: str | None = None  # "on_track", "ahead", "behind", "completed"
    days_remaining: int | None = None

    model_config = {"from_attributes": True}


class SavingsGoal(SavingsGoalBase):
    id: int

    model_config = {"from_attributes": True}
