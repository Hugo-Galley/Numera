from datetime import datetime
from sqlalchemy.orm import Session
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.investment_transaction import InvestmentTransaction
from app.core.finance import get_recurring_occurrences, month_label_from_date
from app.core.currency import convert_amount
from app.core.logging import get_logger

logger = get_logger(__name__)

async def generate_recurring_transactions(db: Session) -> int:
    """
    Check all active recurring transactions and generate pending real transactions.
    Returns the number of transactions generated.
    """
    now = datetime.now()
    # We set a limit to avoid generating too many transactions if start_date is very old
    # But usually, we want to catch up.
    
    recurring_defs = db.query(RecurringTransaction).filter(
        RecurringTransaction.is_active == True,
        RecurringTransaction.auto_generate == True
    ).all()
    
    generated_count = 0
    affected_account_ids = set()
    
    for rd in recurring_defs:
        # We look for occurrences between the last generation and now
        # If last_generated_date is None, we start from start_date
        start_search = rd.last_generated_date if rd.last_generated_date else rd.start_date
        
        # Avoid double counting the last generated date
        if rd.last_generated_date:
            # We add a small delta to avoid repeating the same date if it's exact
            # Actually get_recurring_occurrences includes the start_period if it matches.
            # So if we use last_generated_date, we might duplicate.
            # Let's use start_search + 1 day (or 1 second)
            from datetime import timedelta
            start_search = start_search + timedelta(seconds=1)

        if start_search >= now:
            continue
            
        occurrences = get_recurring_occurrences(rd, start_search, now)
        
        for occ in occurrences:
            # Create the transaction
            # Note: convert_amount is async
            
            # Fetch account to get target currency
            from app.models.account import Account
            account = db.query(Account).filter(Account.id == rd.account_id).first()
            if not account:
                logger.warning(f"Account {rd.account_id} not found for recurring tx {rd.id}")
                continue
                
            # Check if this rd is tied to SalaryConfig
            from app.models.salary_config import SalaryConfig
            from app.models.salary_month import SalaryMonth
            from app.models.telecommuting_day import TelecommutingDay
            
            salary_config = db.query(SalaryConfig).filter(
                (SalaryConfig.salary_recurring_id == rd.id) | 
                (SalaryConfig.ticket_recurring_id == rd.id)
            ).first()
            
            original_amount = rd.amount
            currency = rd.currency
            note = rd.note or rd.name
            
            if salary_config:
                month_label = month_label_from_date(occ)
                salary_month_label = f"{occ.year}-{occ.month:02d}"
                # Check if calendar was filled for this month
                salary_month = db.query(SalaryMonth).filter(
                    SalaryMonth.salary_config_id == salary_config.id,
                    SalaryMonth.month_label == salary_month_label
                ).first()
                
                tt_days_count = 0
                if salary_month:
                    tt_days_count = db.query(TelecommutingDay).filter(
                        TelecommutingDay.salary_config_id == salary_config.id,
                        TelecommutingDay.month_label == salary_month_label
                    ).count()
                    
                    # Also use the precise date if defined!
                    if rd.id == salary_config.salary_recurring_id and salary_month.salary_date:
                        occ = datetime.combine(salary_month.salary_date, datetime.min.time())
                    if rd.id == salary_config.ticket_recurring_id and salary_month.ticket_date:
                        occ = datetime.combine(salary_month.ticket_date, datetime.min.time())
                    
                if rd.id == salary_config.salary_recurring_id:
                    deduction = tt_days_count * salary_config.ticket_employee_share
                    original_amount = salary_config.net_salary - deduction
                    note = f"Net après primes: {salary_config.net_salary:.2f}€ - TR({tt_days_count}x{salary_config.ticket_employee_share:.2f}€): {original_amount:.2f}€"
                elif rd.id == salary_config.ticket_recurring_id:
                    original_amount = tt_days_count * salary_config.ticket_value
                    note = f"{tt_days_count} tickets x {salary_config.ticket_value:.2f}€"
                    
            if currency != account.currency:
                converted_amount = await convert_amount(
                    amount=original_amount,
                    from_currency=currency,
                    to_currency=account.currency,
                    date=occ.date(),
                    db=db
                )
            else:
                converted_amount = original_amount
                
            if account.type == "investissement" and rd.type.lower() in ["versement", "retrait", "dividende"]:
                new_tx = InvestmentTransaction(
                    account_id=rd.account_id,
                    date=occ,
                    type=rd.type.lower(),
                    amount=converted_amount,
                    currency=currency,
                    original_amount=original_amount,
                    note=note,
                    asset_class=rd.asset_class,
                    sector=rd.sector,
                    geographic_zone=rd.geographic_zone,
                    recurring_transaction_id=rd.id
                )
            else:
                new_tx = Transaction(
                    account_id=rd.account_id,
                    date=occ,
                    month_label=month_label_from_date(occ),
                    type=rd.type,
                    merchant=rd.name,
                    category_id=rd.category_id,
                    amount=converted_amount,
                    currency=currency,
                    original_amount=original_amount,
                    running_balance=0.0, # Will be recalculated
                    note=note,
                    is_recurring=True,
                    recurring_transaction_id=rd.id
                )
            db.add(new_tx)
            generated_count += 1
            affected_account_ids.add(rd.account_id)
            
            # Update last_generated_date
            rd.last_generated_date = occ
            
        db.commit()
        
    if generated_count > 0:
        # Recalculate balances
        from app.api.transactions import recalculate_running_balances
        for acc_id in affected_account_ids:
            recalculate_running_balances(db, acc_id)
        logger.info(f"Generated {generated_count} recurring transactions")
        
    return generated_count
