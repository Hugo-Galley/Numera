import calendar
import traceback
from datetime import date, datetime, timedelta

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.core.budget_period import period_bounds
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
    SubscriptionPriceChange,
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
from app.core.finance import get_recurring_occurrences, is_lapsed
from app.core.subscription_prices import PriceChange, detect_price_changes
from app.core.logging import get_logger
from app.schemas.transaction import TransactionRead


logger = get_logger(__name__)

router = APIRouter()

from .utils import (
    _tx_sample,
    _tx_read,
    _savings_account_ids,
    _savings_events_by_account,
    _savings_total_at,
    _get_ticket_restaurant_account_ids,
)


# Multiplicateurs (coût mensuel, coût annuel) par fréquence de récurrence
MONTHS_PER_PERIOD_FACTOR = {
    "daily": {"monthly": 30.0, "annual": 365.0},
    "weekly": {"monthly": 4.33, "annual": 52.0},
    "monthly": {"monthly": 1.0, "annual": 12.0},
    "quarterly": {"monthly": 1 / 3, "annual": 4.0},
    "yearly": {"monthly": 1 / 12, "annual": 1.0},
    "annual": {"monthly": 1 / 12, "annual": 1.0},  # ancien libellé
}


@router.get("/subscriptions", response_model=SubscriptionsResponse)
async def get_subscriptions_analytics(
    account_id: int | None = Query(default=None),
    include_other: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """
    Analyzes subscriptions and fixed charges.
    include_other : ajoute les récurrences qui ne sont pas des sorties (salaire, etc.),
    marquées par flow_type ; elles sont exclues des totaux.
    """
    subscriptions: List[SubscriptionInsight] = []
    
    # 1. Explicit recurring transactions
    recur_query = db.query(RecurringTransaction)
    if not include_other:
        recur_query = recur_query.filter(RecurringTransaction.type == "Sortie")
    if account_id:
        recur_query = recur_query.filter(RecurringTransaction.account_id == account_id)
    
    rates = await get_exchange_rates("EUR")
    recurring_defs = recur_query.all()
    for rd in recurring_defs:
        # Coût mensuel/annuel en EUR : le montant d'une récurrence est dans sa propre devise
        rate = rates.get(rd.currency or "EUR", 1.0) or 1.0
        factor = MONTHS_PER_PERIOD_FACTOR.get(rd.frequency)
        monthly_cost = float(rd.amount) * factor["monthly"] / rate if factor else 0.0
        annual_cost = float(rd.amount) * factor["annual"] / rate if factor else 0.0
        is_savings_flow = bool(rd.transfer_to_account_id) or (
            rd.category is not None and rd.category.name in ("Investissement", "Epargne")
        )

        # Find last occurrence in real transactions
        last_tx = db.query(Transaction).filter(
            Transaction.recurring_transaction_id == rd.id
        ).order_by(Transaction.date.desc()).first()
        
        last_occ = last_tx.date.isoformat() if last_tx else None
        
        # Next occurrence (sur un peu plus d'un an : une récurrence annuelle a aussi sa prochaine date)
        next_occs = get_recurring_occurrences(rd, datetime.now(), datetime.now() + timedelta(days=400))
        next_occ = next_occs[0].isoformat() if next_occs else None
        lapsed = bool(rd.is_active) and is_lapsed(rd.frequency, last_tx.date if last_tx else None, datetime.now())

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
            status=("lapsed" if lapsed else "active") if rd.is_active else "paused",
            logo=rd.logo,
            flow_type=rd.type,
            # Plus prélevée depuis deux périodes : affichée à part, hors des totaux
            counts_in_total=bool(rd.is_active) and not lapsed and not is_savings_flow,
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

    outflows = [s for s in subscriptions if s.flow_type == "Sortie" and s.counts_in_total]
    total_monthly = sum(s.monthly_cost for s in outflows)
    total_annual = sum(s.annual_cost for s in outflows)

    return SubscriptionsResponse(
        subscriptions=subscriptions,
        total_monthly=round(total_monthly, 2),
        total_annual=round(total_annual, 2),
        price_changes=[price_change_read(c) for c in detect_price_changes(db, account_id=account_id)],
    )


def price_change_id(change: PriceChange) -> str:
    return f"subscription-price-{change.account_id}-{change.key}-{change.changed_on.isoformat()}"


def price_change_read(change: PriceChange) -> SubscriptionPriceChange:
    return SubscriptionPriceChange(
        id=price_change_id(change),
        name=change.name,
        account_id=change.account_id,
        currency=change.currency,
        frequency=change.frequency,
        old_amount=change.old_amount,
        new_amount=change.new_amount,
        delta=change.delta,
        delta_pct=change.delta_pct,
        annual_impact=change.annual_impact,
        changed_on=change.changed_on.isoformat(),
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
    start, end = period_bounds(db, year, month)
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


