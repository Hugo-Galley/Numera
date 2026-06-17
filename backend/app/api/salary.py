from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract, and_
from datetime import datetime

from app.api.deps import get_db
from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.telecommuting_day import TelecommutingDay
from app.models.recurring_transaction import RecurringTransaction
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

def sync_recurring_transactions(db: Session, config: SalaryConfig) -> None:
    """Create or update linked RecurringTransaction entries for salary and TR.

    Amount is set from config values:
    - Salary: config.net_salary
    - TR: computed from TT days count * config.ticket_value (defaults to 0 if no TT days set)

    day_of_month, account_id, category_id etc. on the RecurringTransaction are only set
    at creation time; afterwards the user manages them through the normal recurring
    transaction edit form.
    """
    now = datetime.utcnow()

    # Compute deduction from default TT days if present, else just use a generic default or 0
    # Actually wait, when syncing the config originally, tt_days_count might be 0, so amount is net_salary.
    # It will be recalculated at generation time anyway.
    # But let's set it to net_salary.
    
    # Handle Salary
    rt_salary = None
    if config.salary_recurring_id:
        rt_salary = db.query(RecurringTransaction).filter_by(id=config.salary_recurring_id).first()
        
    if rt_salary:
        rt_salary.amount = config.net_salary
        rt_salary.account_id = config.salary_account_id
        rt_salary.category_id = config.salary_category_id
    else:
        # Determine appropriate start_date for the 25th
        start_date_salary = now.replace(day=25, hour=0, minute=0, second=0, microsecond=0)
        if start_date_salary < now:
            # If we are past the 25th, maybe start next month, but it's fine, it won't generate past ones if last_generated_date is set.
            # Actually just start it this month so we can see it in calendar
            pass
            
        rt_salary = RecurringTransaction(
            account_id=config.salary_account_id,
            name="Salaire",
            type="Entree",
            amount=config.net_salary,
            currency="EUR",
            category_id=config.salary_category_id,
            frequency="monthly",
            day_of_month=25,
            start_date=start_date_salary,
            auto_generate=True,
        )
        db.add(rt_salary)
        db.flush()
        config.salary_recurring_id = rt_salary.id

    # Handle Ticket Restaurant
    # Compute current month TT days count for the note
    today = date.today()
    month_label = f"{today.year}-{today.month:02d}"
    tt_days_count = db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label
    ).count()
    ticket_credit = tt_days_count * config.ticket_value

    rt_ticket = None
    if config.ticket_recurring_id:
        rt_ticket = db.query(RecurringTransaction).filter_by(id=config.ticket_recurring_id).first()
        
    if rt_ticket:
        rt_ticket.amount = ticket_credit
        rt_ticket.account_id = config.ticket_account_id
        rt_ticket.category_id = config.ticket_category_id
    else:
        start_date_ticket = now.replace(day=5, hour=0, minute=0, second=0, microsecond=0)
        rt_ticket = RecurringTransaction(
            account_id=config.ticket_account_id,
            name="Tickets Restaurant",
            type="Entree",
            amount=ticket_credit,
            currency="EUR",
            category_id=config.ticket_category_id,
            frequency="monthly",
            day_of_month=5,
            start_date=start_date_ticket,
            auto_generate=True,
        )
        db.add(rt_ticket)
        db.flush()
        config.ticket_recurring_id = rt_ticket.id

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
    db.flush()
    sync_recurring_transactions(db, config)
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
        
    sync_recurring_transactions(db, config)
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
    
    ticket_credit = tt_days * config.ticket_value
    ticket_deduction = tt_days * config.ticket_employee_share
    real_salary = config.net_salary - ticket_deduction
    
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
        raise HTTPException(status_code=400, detail="Already generated for this month")
        
    # Instead of generating instantly, we just mark it as generated.
    # The recurring transaction engine will actually generate it when the date arrives.
    month_record.is_generated = True
    db.commit()
        
    return {"status": "ok"}

@router.delete("/generate/{year}/{month}")
def reset_generation(year: int, month: int, db: Session = Depends(get_db)):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")
        
    month_label = f"{year}-{month:02d}"
    month_record = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label == month_label
    ).first()
    
    if not month_record:
        raise HTTPException(status_code=400, detail="Month record not found")
        
    month_record.is_generated = False
    
    # Delete any generated transactions for this month from the recurring job
    from app.models.transaction import Transaction
    if config.salary_recurring_id:
        db.query(Transaction).filter(
            Transaction.recurring_transaction_id == config.salary_recurring_id,
            Transaction.month_label == month_label
        ).delete()
        
    if config.ticket_recurring_id:
        db.query(Transaction).filter(
            Transaction.recurring_transaction_id == config.ticket_recurring_id,
            Transaction.month_label == month_label
        ).delete()
        
    # Also delete any manually generated ones if they exist
    db.query(Transaction).filter(
        Transaction.merchant.in_(["Salaire", "Tickets Restaurant"]),
        Transaction.month_label == month_label,
        Transaction.is_recurring == True,
        Transaction.recurring_transaction_id == None
    ).delete()

    db.commit()
    
    # Recalculate balances
    from app.api.transactions import recalculate_running_balances
    if config.salary_account_id:
        recalculate_running_balances(db, config.salary_account_id)
    if config.ticket_account_id:
        recalculate_running_balances(db, config.ticket_account_id)
        
    return {"status": "ok"}
