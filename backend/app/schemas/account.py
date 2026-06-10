from datetime import datetime

from pydantic import BaseModel, Field


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: str
    color: str | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None


class AccountCreate(AccountBase):
    currency: str = "EUR"


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    color: str | None = None
    active: bool | None = None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None


class AccountRead(AccountBase):
    id: int
    currency: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
