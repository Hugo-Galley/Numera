from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.salary_config import (
    SalaryConfigCreate,
    SalaryConfigRead,
    SalaryConfigUpdate,
    SalaryMonthRead,
    SalaryMonthSummary,
    SalaryMonthUpdate,
    TelecommutingDayRead,
    TelecommutingDaysUpdate,
    WorkTimeRead,
    WorkTimeUpdate,
)
from app.services import salary as service

router = APIRouter(prefix="/salary", tags=["salary"])


@router.get("/config", response_model=SalaryConfigRead)
def get_salary_config(db: Session = Depends(get_db)):
    return service.get_salary_config(db)


@router.post("/config", response_model=SalaryConfigRead)
def create_salary_config(config_in: SalaryConfigCreate, db: Session = Depends(get_db)):
    return service.create_salary_config(db, config_in)


@router.put("/config", response_model=SalaryConfigRead)
def update_salary_config(config_in: SalaryConfigUpdate, db: Session = Depends(get_db)):
    return service.update_salary_config(db, config_in)


@router.get("/work-time", response_model=WorkTimeRead)
def get_work_time(db: Session = Depends(get_db)) -> WorkTimeRead:
    return service.get_work_time(db)


@router.patch("/work-time", response_model=WorkTimeRead)
def update_work_time(update: WorkTimeUpdate, db: Session = Depends(get_db)) -> WorkTimeRead:
    return service.update_work_time(db, update)


@router.get("/months/{year}", response_model=list[SalaryMonthRead])
def get_salary_months(year: int, db: Session = Depends(get_db)):
    return service.get_salary_months(db, year)


@router.put("/months/{year}/{month}", response_model=SalaryMonthRead)
def set_salary_month_date(year: int, month: int, data: SalaryMonthUpdate, db: Session = Depends(get_db)):
    return service.set_salary_month_date(db, year, month, data)


@router.get("/telecommuting/{year}/{month}", response_model=list[TelecommutingDayRead])
def get_telecommuting_days(year: int, month: int, db: Session = Depends(get_db)):
    return service.get_telecommuting_days(db, year, month)


@router.put("/telecommuting/{year}/{month}")
def set_telecommuting_days(year: int, month: int, data: TelecommutingDaysUpdate, db: Session = Depends(get_db)) -> dict:
    return service.set_telecommuting_days(db, year, month, data)


@router.get("/summary/{year}/{month}", response_model=SalaryMonthSummary)
def get_month_summary(year: int, month: int, db: Session = Depends(get_db)) -> dict:
    return service.get_month_summary(db, year, month)


@router.post("/generate/{year}/{month}")
def trigger_generation(year: int, month: int, db: Session = Depends(get_db)) -> dict:
    """Manually trigger salary transaction generation for a specific month."""
    return service.trigger_generation(db, year, month)


@router.delete("/generate/{year}/{month}")
def reset_generation(year: int, month: int, db: Session = Depends(get_db)) -> dict:
    """Reset a generated month, deleting the associated salary transaction."""
    return service.reset_generation(db, year, month)
