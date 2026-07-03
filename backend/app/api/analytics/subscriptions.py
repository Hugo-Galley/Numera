import calendar
import traceback
from datetime import date, datetime, timedelta

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.core.currency import get_exchange_rates, convert_amount
from app.db.session import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.categorization_rule import CategorizationRule
from app.schemas.category import BudgetAlert
from app.schemas.insight import (
    IntelligentInsights, 
    HealthScore, 
    MetricDetail, 
    Insight, 
    MonthlyReport, 
    MonthlyComparison, 
    CashflowProjection, 
    ProjectionPoint, 
    ProjectionEvent, 
    SubscriptionsResponse, 
    SubscriptionInsight, 
    SubscriptionIgnore,
    WealthSimulationResponse,
    WealthSimulationPoint,
    MoneyFlowReport,
    MoneyFlowBlock,
    MoneyFlowItem,
    DataAuditResponse,
    DataAuditSummary,
    DataAuditIssue,
    ActionCenterResponse,
    ActionCenterSummary,
    ActionItem,
)
from app.models.balance_snapshot import BalanceSnapshot
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.core.finance import get_recurring_occurrences
from app.core.logging import get_logger
from app.schemas.transaction import TransactionRead


logger = get_logger(__name__)

router = APIRouter()

def _tx_sample(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "account_id": tx.account_id,
        "date": tx.date.date().isoformat(),
        "merchant": tx.merchant,
        "type": tx.type,
        "amount": round(float(tx.amount), 2),
        "currency": tx.currency,
    }

def _tx_read(tx: Transaction) -> dict:
    return TransactionRead.model_validate(tx).model_dump(mode="json")

def _savings_account_ids(db: Session) -> list[int]:
    return [acc.id for acc in db.query(Account).filter(Account.type == "epargne", Account.active.is_(True)).all()]

def _savings_events_by_account(db: Session, account_ids: list[int], end_date: datetime) -> dict[int, list[tuple[datetime, int, float]]]:
    events: dict[int, list[tuple[datetime, int, float]]] = {acc_id: [] for acc_id in account_ids}
    if not account_ids:
        return events

    snapshots = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id.in_(account_ids), BalanceSnapshot.date <= end_date)
        .order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc())
        .all()
    )
    for snap in snapshots:
        events[snap.account_id].append((snap.date, 1, float(snap.current_value)))

    transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids), Transaction.date <= end_date)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
    for tx in transactions:
        events[tx.account_id].append((tx.date, 0, float(tx.running_balance)))

    for acc_id, items in events.items():
        items.sort(key=lambda item: (item[0], item[1]))
        events[acc_id] = items
    return events

def _savings_total_at(db: Session, account_ids: list[int], end_date: datetime) -> float:
    events = _savings_events_by_account(db, account_ids, end_date)
    total = 0.0
    for items in events.values():
        total += items[-1][2] if items else 0.0
    return total

def _get_ticket_restaurant_account_ids(db: Session) -> set[int]:
    from app.models.salary_config import SalaryConfig
    ticket_account_ids = set()
    try:
        salary_config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
        if salary_config and salary_config.ticket_account_id:
            ticket_account_ids.add(salary_config.ticket_account_id)
            
        matching_accounts = db.query(Account.id).filter(
            (Account.name.ilike("%ticket%restaurant%")) | 
            (Account.name.ilike("%tickets%restaurant%")) |
            (Account.type == "ticket_restaurant")
        ).all()
        for acc_id_tuple in matching_accounts:
            ticket_account_ids.add(acc_id_tuple[0])
    except Exception as e:
        print(f"Error getting ticket restaurant accounts: {e}")
        
    return ticket_account_ids


@router.get("/subscriptions", response_model=SubscriptionsResponse)
async def get_subscriptions_analytics(
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Analyzes subscriptions and fixed charges.
    """
    subscriptions: List[SubscriptionInsight] = []
    
    # 1. Explicit recurring transactions
    recur_query = db.query(RecurringTransaction).filter(RecurringTransaction.type == "Sortie")
    if account_id:
        recur_query = recur_query.filter(RecurringTransaction.account_id == account_id)
    
    recurring_defs = recur_query.all()
    for rd in recurring_defs:
        monthly_cost = 0.0
        annual_cost = 0.0
        if rd.frequency == "monthly":
            monthly_cost = float(rd.amount)
            annual_cost = float(rd.amount) * 12
        elif rd.frequency == "annual":
            monthly_cost = float(rd.amount) / 12
            annual_cost = float(rd.amount)
        elif rd.frequency == "weekly":
            monthly_cost = float(rd.amount) * 4.33
            annual_cost = float(rd.amount) * 52
        elif rd.frequency == "quarterly":
            monthly_cost = float(rd.amount) / 3
            annual_cost = float(rd.amount) * 4

        # Find last occurrence in real transactions
        last_tx = db.query(Transaction).filter(
            Transaction.recurring_transaction_id == rd.id
        ).order_by(Transaction.date.desc()).first()
        
        last_occ = last_tx.date.isoformat() if last_tx else None
        
        # Next occurrence
        next_occs = get_recurring_occurrences(rd, datetime.now(), datetime.now() + timedelta(days=60))
        next_occ = next_occs[0].isoformat() if next_occs else None

        subscriptions.append(SubscriptionInsight(
            name=rd.name,
            category_name=rd.category.name if rd.category else "Abonnement",
            amount=float(rd.amount),
            frequency=rd.frequency,
            monthly_cost=round(monthly_cost, 2),
            annual_cost=round(annual_cost, 2),
            last_occurrence=last_occ,
            next_occurrence=next_occ,
            is_recurring_entity=True,
            status="active" if rd.is_active else "paused"
        ))

    # 2. Detect potential subscriptions (Repeated transactions same merchant + same amount)
    limit_date = datetime.now() - timedelta(days=90)
    potential_query = db.query(
        Transaction.merchant,
        Transaction.amount,
        Category.name.label("category_name"),
        func.count(Transaction.id).label("count"),
        func.max(Transaction.date).label("last_date")
    ).join(Category, Transaction.category_id == Category.id, isouter=True) \
     .filter(Transaction.type == "Sortie") \
     .filter(Transaction.date >= limit_date) \
     .filter(Transaction.recurring_transaction_id == None) \
     .filter(Transaction.is_subscription_ignored == False) \
     .group_by(Transaction.merchant, Transaction.amount, Category.id) \
     .having(func.count(Transaction.id) >= 2)
    
    if account_id:
        potential_query = potential_query.filter(Transaction.account_id == account_id)
        
    potentials = potential_query.all()
    for p in potentials:
        if any(s.name.lower() == p.merchant.lower() for s in subscriptions):
            continue
            
        monthly_cost = float(p.amount)
        subscriptions.append(SubscriptionInsight(
            name=p.merchant,
            category_name=p.category_name or "Abonnement",
            amount=float(p.amount),
            frequency="monthly (detected)",
            monthly_cost=round(monthly_cost, 2),
            annual_cost=round(monthly_cost * 12, 2),
            last_occurrence=p.last_date.isoformat(),
            next_occurrence=None,
            is_recurring_entity=False,
            status="potential"
        ))

    total_monthly = sum(s.monthly_cost for s in subscriptions)
    total_annual = sum(s.annual_cost for s in subscriptions)

    return SubscriptionsResponse(
        subscriptions=subscriptions,
        total_monthly=round(total_monthly, 2),
        total_annual=round(total_annual, 2)
    )


@router.post("/subscriptions/ignore")
async def ignore_subscription_detection(
    data: SubscriptionIgnore,
    db: Session = Depends(get_db),
):
    """
    Marks all matching transactions as ignored for subscription detection.
    """
    db.query(Transaction).filter(
        Transaction.merchant == data.merchant,
        Transaction.amount == data.amount,
        Transaction.recurring_transaction_id == None
    ).update({"is_subscription_ignored": True}, synchronize_session=False)
    
    db.commit()
    return {"status": "ok"}


async def get_subscription_total_for_period(month: int, year: int, db: Session) -> float:
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")

    tr_accounts = _get_ticket_restaurant_account_ids(db)
    query = (
        db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            Category.name == "Abonnement",
        )
    )
    if tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))

    rows = query.group_by(Account.currency).all()

    total_eur = 0.0
    for row in rows:
        total_eur += row.total / rates.get(row.currency, 1.0)
    
    return total_eur


