import datetime as dt
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class FinancialEventBase(BaseModel):
    date: dt.date
    title: Title
    note: str | None = Field(default=None, max_length=1000)
    account_id: int | None = None


class FinancialEventCreate(FinancialEventBase):
    pass


class FinancialEventUpdate(BaseModel):
    date: dt.date | None = None
    title: Title | None = None
    note: str | None = Field(default=None, max_length=1000)
    account_id: int | None = None


class FinancialEventRead(FinancialEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_name: str | None = None
