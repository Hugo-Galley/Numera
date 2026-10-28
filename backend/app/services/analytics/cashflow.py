"""Projection de trésorerie (échéances récurrentes à venir)."""
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.integrations.currency import get_exchange_rates
from app.models.account import Account
from app.schemas.insight import CashflowProjection, ProjectionPoint, ProjectionEvent
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.domain.finance import get_recurring_occurrences, is_lapsed
from app.core.logging import get_logger
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.core.errors import NotFoundError

logger = get_logger(__name__)


async def compute_cashflow_projection(db: Session, days: int = 30, account_id: int | None = None) -> CashflowProjection:
    """
    Projects balance for the next X days based on current balance and recurring transactions.
    """
    now = datetime.now()
    end_date = now + timedelta(days=days)
    rates = await get_exchange_rates("EUR")

    # 1. Current balance
    current_bal = 0.0
    counted_ids: set[int] = set()  # comptes dont le solde est dans `current_bal`
    if account_id:
        acc = db.query(Account).filter(Account.id == account_id).first()
        if not acc:
            raise NotFoundError("Account not found")
        last_tx = (
            db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .first()
        )
        if last_tx:
            current_bal = float(last_tx.running_balance)
    else:
        active_accounts = db.query(Account).filter(Account.active == True).all()
        tr_accounts = ticket_restaurant_account_ids(db)
        for acc in active_accounts:
            if tr_accounts and acc.id in tr_accounts:
                continue
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == acc.id)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                current_bal += float(last_tx.running_balance) / rates.get(acc.currency, 1.0)
                counted_ids.add(acc.id)

    # 2. Collect future occurrences
    projected_events_list: List[ProjectionEvent] = []
    
    recur_query = db.query(RecurringTransaction).filter(RecurringTransaction.is_active == True)
    if account_id:
        recur_query = recur_query.filter(RecurringTransaction.account_id == account_id)
    else:
        tr_accounts = ticket_restaurant_account_ids(db)
        if tr_accounts:
            recur_query = recur_query.filter(RecurringTransaction.account_id.notin_(tr_accounts))
    
    recurring_defs = recur_query.all()
    
    for rd in recurring_defs:
        # Vue globale : un virement vers un compte déjà compté dans le solde ne change pas le total
        if not account_id and rd.transfer_to_account_id in counted_ids:
            continue
        # Récurrence plus prélevée depuis deux périodes (abonnement arrêté sans être désactivé)
        last_occ = (
            db.query(func.max(Transaction.date)).filter(Transaction.recurring_transaction_id == rd.id).scalar()
        )
        if is_lapsed(rd.frequency, last_occ, now):
            continue
        occurrences = get_recurring_occurrences(rd, now, end_date)
        for occ in occurrences:
            is_income = rd.type in ["Entree", "Interets", "versement", "dividende"]
            
            proj_amount = rd.amount
            
            # Check if it's a salary/TR recurrence
            from app.models.salary_config import SalaryConfig
            from app.models.salary_month import SalaryMonth
            from app.models.telecommuting_day import TelecommutingDay
            from app.domain.finance import month_label_from_date
            
            salary_config = db.query(SalaryConfig).filter(
                (SalaryConfig.salary_recurring_id == rd.id) | 
                (SalaryConfig.ticket_recurring_id == rd.id)
            ).first()
            
            if salary_config:
                if rd.id == salary_config.ticket_recurring_id and occ.day < 15:
                    work_month_date = occ - timedelta(days=20)
                    salary_month_label = f"{work_month_date.year}-{work_month_date.month:02d}"
                else:
                    salary_month_label = f"{occ.year}-{occ.month:02d}"
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
                
                if rd.id == salary_config.salary_recurring_id:
                    deduction = tt_days_count * salary_config.ticket_employee_share
                    proj_amount = salary_config.net_salary - deduction
                elif rd.id == salary_config.ticket_recurring_id:
                    proj_amount = tt_days_count * salary_config.ticket_value

            # Convert amount to EUR if global view
            amount_target = float(proj_amount)
            if not account_id and rd.currency != "EUR":
                amount_target = amount_target / rates.get(rd.currency, 1.0)
                
            projected_events_list.append(ProjectionEvent(
                date=occ.isoformat(),
                name=rd.name,
                amount=amount_target,
                type="recurring",
                is_income=is_income
            ))

    # 3. Simulate day by day
    points: List[ProjectionPoint] = []
    simulated_bal = current_bal
    
    # Sort events by date
    projected_events_list.sort(key=lambda x: x.date)
    event_idx = 0
    
    low_point = current_bal
    low_point_date = now.date().isoformat()
    
    temp_date = now
    while temp_date <= end_date:
        daily_change = 0.0
        while event_idx < len(projected_events_list) and datetime.fromisoformat(projected_events_list[event_idx].date).date() == temp_date.date():
            ev = projected_events_list[event_idx]
            
            # Amount conversion for global view
            # Note: We don't have account currency here in ProjectionEvent, but we can assume EUR for now or fetch it
            # To be precise, we'd need rd.currency. Let's assume EUR if no account_id.
            # For simplicity, we'll re-fetch or use a more complex event structure.
            
            # Re-fetch rd currency if needed? No, let's keep it simple for now.
            # In a real app, I'd want the currency in ProjectionEvent.
            
            amt = ev.amount
            if ev.is_income:
                simulated_bal += amt
                daily_change += amt
            else:
                simulated_bal -= amt
                daily_change -= amt
            
            event_idx += 1
            
        if simulated_bal < low_point:
            low_point = simulated_bal
            low_point_date = temp_date.date().isoformat()
            
        points.append(ProjectionPoint(
            date=temp_date.date().isoformat(),
            balance=round(simulated_bal, 2),
            change=round(daily_change, 2)
        ))
        temp_date += timedelta(days=1)

    return CashflowProjection(
        points=points,
        events=projected_events_list,
        current_balance=round(current_bal, 2),
        projected_balance=round(simulated_bal, 2),
        low_point=round(low_point, 2),
        low_point_date=low_point_date,
        days=days
    )
