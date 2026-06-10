from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: str
    icon: str | None = None
    color: str | None = None
    group: str | None = None
    monthly_limit: float | None = None
    annual_limit: float | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: str | None = None
    icon: str | None = None
    color: str | None = None
    group: str | None = None
    monthly_limit: float | None = None
    annual_limit: float | None = None


class CategoryRead(CategoryBase):
    id: int

    model_config = {"from_attributes": True}


class BudgetAlert(BaseModel):
    category_id: int
    category_name: str
    category_icon: str | None
    category_color: str | None
    monthly_limit: float | None
    annual_limit: float | None
    monthly_spent: float
    annual_spent: float
    monthly_ratio: float | None
    annual_ratio: float | None
