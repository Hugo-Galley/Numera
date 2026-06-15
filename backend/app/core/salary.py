from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import extract

from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.telecommuting_day import TelecommutingDay
from app.models.transaction import Transaction
from app.api.transactions import recalculate_running_balances
from app.core.logging import get_logger

logger = get_logger(__name__)

def generate_salary_transactions(db: Session, config: SalaryConfig, month_record: SalaryMonth, month_label: str) -> bool:
    if month_record.is_generated:
        return False
        
    tt_days = db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label
    ).count()
    
    nb_tickets = tt_days
    ticket_deduction = nb_tickets * config.ticket_employee_share
    real_salary = config.net_salary - ticket_deduction
    ticket_credit = nb_tickets * config.ticket_value
    
    # 1. Salary Transaction
    tx_salary = Transaction(
        account_id=config.salary_account_id,
        date=month_record.salary_date,
        month_label=month_label,
        type="Entree",
        merchant="Salaire",
        category_id=config.salary_category_id,
        amount=real_salary,
        original_amount=real_salary,
        currency="EUR",
        running_balance=0.0,
        note=f"Net après primes: {config.net_salary:.2f}€ - TR({nb_tickets}x{config.ticket_employee_share:.2f}€): {real_salary:.2f}€",
        is_recurring=True
    )
    db.add(tx_salary)
    
    # 2. Tickets Restaurant Transaction
    tx_tr = Transaction(
        account_id=config.ticket_account_id,
        date=month_record.ticket_date if month_record.ticket_date else month_record.salary_date,
        month_label=month_label,
        type="Entree",
        merchant="Tickets Restaurant",
        category_id=config.ticket_category_id,
        amount=ticket_credit,
        original_amount=ticket_credit,
        currency="EUR",
        running_balance=0.0,
        note=f"{nb_tickets} tickets x {config.ticket_value:.2f}€",
        is_recurring=True
    )
    db.add(tx_tr)
    
    # Update month record
    month_record.is_generated = True
    month_record.generated_at = datetime.utcnow()
    
    db.commit()
    
    # Recalculate balances
    recalculate_running_balances(db, config.salary_account_id)
    if config.salary_account_id != config.ticket_account_id:
        recalculate_running_balances(db, config.ticket_account_id)
        
    logger.info(f"Generated salary transactions for {month_label}")
    return True

def check_and_generate_pending_salaries(db: Session):
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        return 0
        
    today = date.today()
    pending_months = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.is_generated == False,
        SalaryMonth.salary_date <= today
    ).all()
    
    generated_count = 0
    for pm in pending_months:
        if generate_salary_transactions(db, config, pm, pm.month_label):
            generated_count += 1
            
    return generated_count
