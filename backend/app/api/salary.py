from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract, and_

from app.api.deps import get_db
from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.telecommuting_day import TelecommutingDay
from app.schemas.salary_config import (
    SalaryConfigCreate,
    SalaryConfigRead,
    SalaryConfigUpdate,
    SalaryMonthRead,
    SalaryMonthUpdate,
    SalaryMonthSummary,
    TelecommutingDaysUpdate,
    TelecommutingDayRead,
)
from app.core.salary import generate_salary_transactions

router = APIRouter(prefix="/salary", tags=["salary"])

@router.get("/config", response_model=SalaryConfigRead)
def get_salary_config(db: Session = Depends(get_db)):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")
    return config

@router.post("/config", response_model=SalaryConfigRead)
def create_salary_config(config_in: SalaryConfigCreate, db: Session = Depends(get_db)):
    # Deactivate existing
    db.query(SalaryConfig).filter(SalaryConfig.is_active == True).update({"is_active": False})
    
    config = SalaryConfig(**config_in.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

@router.put("/config", response_model=SalaryConfigRead)
def update_salary_config(config_in: SalaryConfigUpdate, db: Session = Depends(get_db)):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")
        
    update_data = config_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
        
    db.commit()
    db.refresh(config)
    return config

@router.get("/months/{year}", response_model=list[SalaryMonthRead])
def get_salary_months(year: int, db: Session = Depends(get_db)):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        return []
        
    months = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label.startswith(f"{year}-")
    ).all()
    
    return months

@router.put("/months/{year}/{month}", response_model=SalaryMonthRead)
def set_salary_month_date(year: int, month: int, data: SalaryMonthUpdate, db: Session = Depends(get_db)):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")
        
    month_label = f"{year}-{month:02d}"
    
    record = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label == month_label
    ).first()
    
    if record:
        if data.salary_date is not None:
            record.salary_date = data.salary_date
        if data.ticket_date is not None:
            record.ticket_date = data.ticket_date
    else:
        # Require salary_date for new record
        if data.salary_date is None:
            raise HTTPException(status_code=400, detail="salary_date is required for new month")
        record = SalaryMonth(
            salary_config_id=config.id,
            month_label=month_label,
            salary_date=data.salary_date,
            ticket_date=data.ticket_date
        )
        db.add(record)
        
    db.commit()
    db.refresh(record)
    return record

@router.get("/telecommuting/{year}/{month}", response_model=list[TelecommutingDayRead])
def get_telecommuting_days(year: int, month: int, db: Session = Depends(get_db)):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        return []
        
    month_label = f"{year}-{month:02d}"
    days = db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label
    ).all()
    
    return days

@router.put("/telecommuting/{year}/{month}")
def set_telecommuting_days(year: int, month: int, data: TelecommutingDaysUpdate, db: Session = Depends(get_db)):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")
        
    month_label = f"{year}-{month:02d}"
    
    # Delete existing for this month
    db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label
    ).delete()
    
    # Check if a date falls on weekend
    for d in data.dates:
        if d.weekday() >= 5: # 5=Sat, 6=Sun
            raise HTTPException(status_code=400, detail=f"Date {d} is a weekend")
            
    # Add new
    new_days = [
        TelecommutingDay(
            salary_config_id=config.id,
            date=d,
            month_label=month_label
        ) for d in data.dates
    ]
    db.add_all(new_days)
    db.commit()
    return {"status": "ok"}

@router.get("/summary/{year}/{month}", response_model=SalaryMonthSummary)
def get_month_summary(year: int, month: int, db: Session = Depends(get_db)):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")
        
    month_label = f"{year}-{month:02d}"
    
    month_record = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label == month_label
    ).first()
    
    tt_days = db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label
    ).count()
    
    ticket_deduction = tt_days * config.ticket_employee_share
    real_salary = config.net_salary - ticket_deduction
    ticket_credit = tt_days * config.ticket_value
    
    return {
        "month_label": month_label,
        "salary_date": month_record.salary_date if month_record else None,
        "ticket_date": month_record.ticket_date if month_record else None,
        "net_salary": config.net_salary,
        "tt_days_count": tt_days,
        "ticket_deduction": ticket_deduction,
        "real_salary": real_salary,
        "ticket_credit": ticket_credit,
        "is_generated": month_record.is_generated if month_record else False
    }

@router.post("/generate/{year}/{month}")
def trigger_generation(year: int, month: int, db: Session = Depends(get_db)):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")
        
    month_label = f"{year}-{month:02d}"
    month_record = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label == month_label
    ).first()
    
    if not month_record:
        raise HTTPException(status_code=400, detail="Salary date not configured for this month")
        
    if month_record.is_generated:
        # User wants to re-generate -> they must delete the old ones manually for now
        # OR we could offer a way to reset
        raise HTTPException(status_code=400, detail="Already generated for this month")
        
    success = generate_salary_transactions(db, config, month_record, month_label)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to generate")
        
    return {"status": "ok"}
