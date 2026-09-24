from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.finance import month_label_from_date
from app.core.salary import generate_salary_transactions
from app.models.recurring_transaction import RecurringTransaction
from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.telecommuting_day import TelecommutingDay
from app.schemas.salary_config import (
    SalaryConfigCreate,
    SalaryConfigRead,
    SalaryConfigUpdate,
    SalaryMonthRead,
    SalaryMonthSummary,
    SalaryMonthUpdate,
    TelecommutingDayRead,
    TelecommutingDaysUpdate,
)


def sync_recurring_transactions(db: Session, config: SalaryConfig) -> None:
    """Create or update the linked RecurringTransaction for salary.

    TR recurring transactions are no longer created — TR is informational only.
    The salary RecurringTransaction is created with auto_generate=False because
    salary generation is handled by check_and_generate_pending_salaries() to
    avoid the double-generation bug.
    """
    now = datetime.utcnow()

    # --- Handle Salary RecurringTransaction ---
    rt_salary = None
    if config.salary_recurring_id:
        rt_salary = db.query(RecurringTransaction).filter_by(
            id=config.salary_recurring_id
        ).first()

    if rt_salary:
        rt_salary.amount = config.net_salary
        rt_salary.account_id = config.salary_account_id
        rt_salary.category_id = config.salary_category_id
        # Ensure auto_generate is False — salary engine handles this
        rt_salary.auto_generate = False
    else:
        start_date_salary = now.replace(day=25, hour=0, minute=0, second=0, microsecond=0)
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
            auto_generate=False,  # Salary engine handles generation
        )
        db.add(rt_salary)
        db.flush()
        config.salary_recurring_id = rt_salary.id

    # --- Deactivate TR recurring if it exists (TR is now informational only) ---
    if config.ticket_recurring_id:
        db.query(RecurringTransaction).filter_by(
            id=config.ticket_recurring_id
        ).update({"is_active": False, "auto_generate": False})


router = APIRouter(prefix="/salary", tags=["salary"])


@router.get("/config", response_model=SalaryConfigRead)
def get_salary_config(db: Session = Depends(get_db)) -> SalaryConfig:
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")
    return config


@router.post("/config", response_model=SalaryConfigRead)
def create_salary_config(
    config_in: SalaryConfigCreate, db: Session = Depends(get_db)
) -> SalaryConfig:
    # Deactivate existing config AND its recurring transactions (fix Bug 5)
    old_configs = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).all()
    for old in old_configs:
        old.is_active = False
        if old.salary_recurring_id:
            db.query(RecurringTransaction).filter_by(id=old.salary_recurring_id).update(
                {"is_active": False, "auto_generate": False}
            )
        if old.ticket_recurring_id:
            db.query(RecurringTransaction).filter_by(id=old.ticket_recurring_id).update(
                {"is_active": False, "auto_generate": False}
            )

    config_data = config_in.model_dump()
    # Default ticket_account_id to salary_account_id if not provided
    if config_data.get("ticket_account_id") is None:
        config_data["ticket_account_id"] = config_data["salary_account_id"]

    config = SalaryConfig(**config_data)
    db.add(config)
    db.flush()
    sync_recurring_transactions(db, config)
    db.commit()
    db.refresh(config)
    return config


@router.put("/config", response_model=SalaryConfigRead)
def update_salary_config(
    config_in: SalaryConfigUpdate, db: Session = Depends(get_db)
) -> SalaryConfig:
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
def get_salary_months(year: int, db: Session = Depends(get_db)) -> list[SalaryMonth]:
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        return []

    months = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label.startswith(f"{year}-"),
    ).all()

    return months


@router.put("/months/{year}/{month}", response_model=SalaryMonthRead)
def set_salary_month_date(
    year: int, month: int, data: SalaryMonthUpdate, db: Session = Depends(get_db)
) -> SalaryMonth:
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")

    month_label = f"{year}-{month:02d}"

    record = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label == month_label,
    ).first()

    if record:
        if data.salary_date is not None:
            record.salary_date = data.salary_date
        if data.ticket_date is not None:
            record.ticket_date = data.ticket_date
    else:
        if data.salary_date is None:
            raise HTTPException(
                status_code=400, detail="salary_date is required for new month"
            )
        record = SalaryMonth(
            salary_config_id=config.id,
            month_label=month_label,
            salary_date=data.salary_date,
            ticket_date=data.ticket_date,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


@router.get("/telecommuting/{year}/{month}", response_model=list[TelecommutingDayRead])
def get_telecommuting_days(
    year: int, month: int, db: Session = Depends(get_db)
) -> list[TelecommutingDay]:
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        return []

    month_label = f"{year}-{month:02d}"
    days = db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label,
    ).all()

    return days


@router.put("/telecommuting/{year}/{month}")
def set_telecommuting_days(
    year: int, month: int, data: TelecommutingDaysUpdate, db: Session = Depends(get_db)
) -> dict:
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")

    month_label = f"{year}-{month:02d}"

    # Delete existing for this month
    db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label,
    ).delete()

    # Check if a date falls on weekend
    for d in data.dates:
        if d.weekday() >= 5:  # 5=Sat, 6=Sun
            raise HTTPException(status_code=400, detail=f"Date {d} is a weekend")

    # Add new
    new_days = [
        TelecommutingDay(
            salary_config_id=config.id,
            date=d,
            month_label=month_label,
        )
        for d in data.dates
    ]
    db.add_all(new_days)

    # Update existing generated salary transaction if applicable
    month_record = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label == month_label,
    ).first()

    if month_record and month_record.is_generated:
        nb_tickets = len(data.dates)
        ticket_deduction = nb_tickets * config.ticket_employee_share
        real_salary = config.net_salary - ticket_deduction

        from app.api.transactions import recalculate_running_balances
        from app.models.transaction import Transaction

        # Update salary transaction only (TR transactions no longer exist)
        tx_salary = db.query(Transaction).filter(
            Transaction.recurring_transaction_id == config.salary_recurring_id,
            Transaction.month_label == month_label,
        ).first()
        if tx_salary:
            tx_salary.amount = real_salary
            tx_salary.original_amount = real_salary
            tx_salary.note = (
                f"Net: {config.net_salary:.2f}\u20ac "
                f"- TR({nb_tickets}\u00d7{config.ticket_employee_share:.2f}\u20ac): "
                f"{real_salary:.2f}\u20ac"
            )

        db.commit()

        if tx_salary:
            recalculate_running_balances(db, tx_salary.account_id)
    else:
        db.commit()

    return {"status": "ok"}


@router.get("/summary/{year}/{month}", response_model=SalaryMonthSummary)
def get_month_summary(
    year: int, month: int, db: Session = Depends(get_db)
) -> dict:
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")

    month_label = f"{year}-{month:02d}"

    month_record = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label == month_label,
    ).first()

    tt_days = db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label,
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
        "is_generated": month_record.is_generated if month_record else False,
    }


@router.post("/generate/{year}/{month}")
def trigger_generation(
    year: int, month: int, db: Session = Depends(get_db)
) -> dict:
    """Manually trigger salary transaction generation for a specific month."""
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")

    month_label = f"{year}-{month:02d}"
    month_record = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label == month_label,
    ).first()

    if not month_record:
        raise HTTPException(
            status_code=400, detail="Salary date not configured for this month"
        )

    if month_record.is_generated:
        raise HTTPException(status_code=400, detail="Already generated for this month")

    # Actually generate the transaction (fix Bug 4)
    success = generate_salary_transactions(db, config, month_record, month_label)
    if not success:
        raise HTTPException(
            status_code=400, detail="Generation failed or transaction already exists"
        )

    return {"status": "ok"}


@router.delete("/generate/{year}/{month}")
def reset_generation(
    year: int, month: int, db: Session = Depends(get_db)
) -> dict:
    """Reset a generated month, deleting the associated salary transaction."""
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Salary config not found")

    month_label_iso = f"{year}-{month:02d}"
    # Also compute the French month name to handle legacy transactions (fix Bug 3)
    month_label_fr = month_label_from_date(datetime(year, month, 1))
    both_labels = [month_label_iso, month_label_fr]

    month_record = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.month_label == month_label_iso,
    ).first()

    if not month_record:
        raise HTTPException(status_code=400, detail="Month record not found")

    month_record.is_generated = False

    from app.models.transaction import Transaction

    # Delete salary transactions (matching EITHER month_label format)
    if config.salary_recurring_id:
        db.query(Transaction).filter(
            Transaction.recurring_transaction_id == config.salary_recurring_id,
            Transaction.month_label.in_(both_labels),
        ).delete(synchronize_session="fetch")

    # Delete legacy TR transactions too (matching EITHER format)
    if config.ticket_recurring_id:
        db.query(Transaction).filter(
            Transaction.recurring_transaction_id == config.ticket_recurring_id,
            Transaction.month_label.in_(both_labels),
        ).delete(synchronize_session="fetch")

    # Delete orphan transactions (no recurring_transaction_id)
    db.query(Transaction).filter(
        Transaction.merchant.in_(["Salaire", "Tickets Restaurant"]),
        Transaction.month_label.in_(both_labels),
        Transaction.is_recurring == True,
        Transaction.recurring_transaction_id == None,
    ).delete(synchronize_session="fetch")

    db.commit()

    # Recalculate balances
    from app.api.transactions import recalculate_running_balances

    if config.salary_account_id:
        recalculate_running_balances(db, config.salary_account_id)
    if (
        config.ticket_account_id
        and config.ticket_account_id != config.salary_account_id
    ):
        recalculate_running_balances(db, config.ticket_account_id)

    return {"status": "ok"}
