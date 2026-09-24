from datetime import date, datetime
from sqlalchemy.orm import Session

from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.telecommuting_day import TelecommutingDay
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.api.transactions import recalculate_running_balances
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_salary_transactions(
    db: Session, config: SalaryConfig, month_record: SalaryMonth, month_label: str
) -> bool:
    """Generate salary transaction for a given month. Idempotent — will not create duplicates."""
    if month_record.is_generated:
        return False

    # IDEMPOTENCE GUARD: Check if a transaction already exists for this month
    if config.salary_recurring_id:
        existing = db.query(Transaction).filter(
            Transaction.recurring_transaction_id == config.salary_recurring_id,
            Transaction.date == month_record.salary_date,
        ).first()
        if existing:
            logger.warning(
                f"Salary transaction already exists for {month_label} (tx id={existing.id}), "
                f"marking as generated without creating duplicate"
            )
            month_record.is_generated = True
            month_record.generated_at = datetime.utcnow()
            db.commit()
            return False

    tt_days = db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config.id,
        TelecommutingDay.month_label == month_label,
    ).count()

    nb_tickets = tt_days
    ticket_deduction = nb_tickets * config.ticket_employee_share
    real_salary = config.net_salary - ticket_deduction

    # Create salary transaction ONLY (no TR transaction — TR is informational only)
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
        note=f"Net: {config.net_salary:.2f}\u20ac - TR({nb_tickets}\u00d7{config.ticket_employee_share:.2f}\u20ac): {real_salary:.2f}\u20ac",
        is_recurring=True,
        recurring_transaction_id=config.salary_recurring_id,
    )
    db.add(tx_salary)

    # Update month record
    month_record.is_generated = True
    month_record.generated_at = datetime.utcnow()

    db.commit()

    # Recalculate balances for salary account only
    recalculate_running_balances(db, config.salary_account_id)

    logger.info(f"Generated salary transaction for {month_label}")
    return True


def check_and_generate_pending_salaries(db: Session) -> int:
    """Auto-generate salary transactions for months whose salary_date has passed."""
    config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
    if not config:
        return 0

    today = date.today()
    pending_months = db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config.id,
        SalaryMonth.is_generated == False,
        SalaryMonth.salary_date <= today,
    ).all()

    generated_count = 0
    for pm in pending_months:
        if generate_salary_transactions(db, config, pm, pm.month_label):
            generated_count += 1

    return generated_count
