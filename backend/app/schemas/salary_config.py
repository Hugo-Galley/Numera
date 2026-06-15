from datetime import date, datetime

from pydantic import BaseModel, Field


class SalaryConfigCreate(BaseModel):
    salary_account_id: int
    ticket_account_id: int
    net_salary: float = Field(..., gt=0)
    ticket_value: float = Field(10.50, gt=0)
    ticket_employee_share: float = Field(4.20, gt=0)
    salary_category_id: int | None = None
    ticket_category_id: int | None = None


class SalaryConfigUpdate(BaseModel):
    salary_account_id: int | None = None
    ticket_account_id: int | None = None
    net_salary: float | None = Field(None, gt=0)
    ticket_value: float | None = Field(None, gt=0)
    ticket_employee_share: float | None = Field(None, gt=0)
    salary_category_id: int | None = None
    ticket_category_id: int | None = None


class SalaryConfigRead(SalaryConfigCreate):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SalaryMonthUpdate(BaseModel):
    salary_date: date | None = None
    ticket_date: date | None = None

class SalaryMonthRead(BaseModel):
    month_label: str
    salary_date: date
    ticket_date: date | None
    is_generated: bool

    model_config = {"from_attributes": True}

class TelecommutingDaysUpdate(BaseModel):
    dates: list[date]

class TelecommutingDayRead(BaseModel):
    date: date

    model_config = {"from_attributes": True}

class SalaryMonthSummary(BaseModel):
    month_label: str
    salary_date: date | None
    ticket_date: date | None
    net_salary: float
    tt_days_count: int
    ticket_deduction: float
    real_salary: float
    ticket_credit: float
    is_generated: bool
