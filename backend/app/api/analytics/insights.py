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
from .budget import budget_analytics, budget_alerts
from .subscriptions import get_subscription_total_for_period
from .metrics import expenses_by_category

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


@router.get("/insights", response_model=IntelligentInsights)
async def get_intelligent_insights(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rates = await get_exchange_rates("EUR")
    start_month = datetime(year, month, 1)
    end_month = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    
    # 1. Fetch current month data for Score
    budget_data = await budget_analytics(month=month, year=year, account_id=account_id, db=db)
    revenus = budget_data["revenus_totaux"]
    depenses_reelles = budget_data["depenses_reelles"]
    epargne_total = budget_data["epargne_total"]
    burn_rate = budget_data["burn_rate"]
    investissements = budget_data["investissements_du_mois"]
    
    # --- Health Score Calculation ---
    metrics = []
    
    # A. Savings Rate (30 pts)
    # Target: 20%
    savings_rate = budget_data["taux_epargne"]
    sr_score = min(max(savings_rate / 20.0 * 30.0, 0.0), 30.0)
    metrics.append(MetricDetail(
        name="Taux d'Épargne",
        score=round(sr_score, 1),
        max_score=30.0,
        value=round(savings_rate, 1),
        unit="%",
        status="good" if savings_rate >= 20 else "warning" if savings_rate >= 10 else "critical"
    ))

    # B. Runway / Safety Fund (30 pts)
    # Target: 6 months of burn rate
    runway_months = (epargne_total / burn_rate / 30.5) if (burn_rate > 0 and epargne_total > 0) else 0.0
    runway_score = min(runway_months / 6.0 * 30.0, 30.0)
    metrics.append(MetricDetail(
        name="Fonds de Sécurité",
        score=round(runway_score, 1),
        max_score=30.0,
        value=round(runway_months, 1),
        unit="mois",
        status="good" if runway_months >= 6 else "warning" if runway_months >= 3 else "critical"
    ))

    # C. Positive Cashflow (20 pts)
    # Target: Revenus > Depenses Reelles
    cashflow = revenus - depenses_reelles
    cf_score = 20.0 if cashflow > 0 else 0.0
    metrics.append(MetricDetail(
        name="Flux de Trésorerie",
        score=cf_score,
        max_score=20.0,
        value=round(cashflow, 2),
        unit="€",
        status="good" if cashflow > 0 else "critical"
    ))

    # D. Investment Ratio (20 pts)
    # Target: 10% of income
    inv_ratio = (investissements / revenus * 100.0) if revenus > 0 else 0.0
    inv_score = min(inv_ratio / 10.0 * 20.0, 20.0)
    metrics.append(MetricDetail(
        name="Ratio d'Investissement",
        score=round(inv_score, 1),
        max_score=20.0,
        value=round(inv_ratio, 1),
        unit="%",
        status="good" if inv_ratio >= 10 else "warning" if inv_ratio >= 5 else "critical"
    ))

    total_score = sum(m.score for m in metrics)
    health_score = HealthScore(total_score=round(total_score, 1), metrics=metrics)

    # --- Anomalies Detection ---
    insights = []

    # 1. Subscription increase
    # Compare with previous month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    
    current_subs_total = await get_subscription_total_for_period(month=month, year=year, db=db)
    prev_subs_total = await get_subscription_total_for_period(month=prev_month, year=prev_year, db=db)
    
    if current_subs_total > prev_subs_total:
        diff = current_subs_total - prev_subs_total
        insights.append(Insight(
            type="anomaly",
            title="Hausse des abonnements",
            description=f"Vos abonnements ont augmenté de {round(diff, 2)}€ par rapport au mois dernier.",
            severity="medium",
            value=diff
        ))

    # 2. Large isolated transactions
    # Threshold: any transaction > 10% of monthly income OR > 500€
    large_tx_query = db.query(Transaction, Account.currency).join(Account).filter(
        Transaction.date >= start_month,
        Transaction.date < end_month,
        Transaction.type == "Sortie",
        Transaction.is_transfer == False
    )
    if account_id:
        large_tx_query = large_tx_query.filter(Transaction.account_id == account_id)
    else:
        tr_accounts = _get_ticket_restaurant_account_ids(db)
        if tr_accounts:
            large_tx_query = large_tx_query.filter(Transaction.account_id.notin_(tr_accounts))
    
    all_txs = large_tx_query.all()
    for tx, curr in all_txs:
        val_eur = tx.amount / rates.get(curr, 1.0)
        # Exclude internal transfers or investments already tracked
        if tx.category and tx.category.name == "Investissement":
            continue
            
        threshold = max(revenus * 0.1, 500.0)
        if val_eur > threshold:
            insights.append(Insight(
                type="anomaly",
                title="Grosse dépense isolée",
                description=f"La transaction '{tx.merchant}' de {round(val_eur, 2)}€ est exceptionnellement élevée.",
                severity="high" if val_eur > revenus * 0.3 else "medium",
                value=val_eur
            ))

    # 3. Category spending anomalies (Sprint 4: > 2x average of last 3 months)
    # Get current month category totals
    current_cat_data = await expenses_by_category(month=month, year=year, account_id=account_id, db=db)
    current_cat_totals = {item["category"]["id"]: item["total"] for item in current_cat_data["items"]}
    
    # Get last 3 months averages
    last_3_months = []
    for i in range(1, 4):
        m_idx = month - i
        y_idx = year
        if m_idx <= 0:
            m_idx += 12
            y_idx -= 1
        last_3_months.append((m_idx, y_idx))
    
    cat_histories = {} # cat_id -> [totals]
    for m_idx, y_idx in last_3_months:
        hist_data = await expenses_by_category(month=m_idx, year=y_idx, account_id=account_id, db=db)
        for item in hist_data["items"]:
            cat_id = item["category"]["id"]
            if cat_id not in cat_histories:
                cat_histories[cat_id] = []
            cat_histories[cat_id].append(item["total"])
            
    for cat_id, current_total in current_cat_totals.items():
        history = cat_histories.get(cat_id, [])
        if len(history) >= 2: # Need at least 2 months to have a meaningful average
            avg = sum(history) / len(history)
            if avg > 20 and current_total > (avg * 2.0): # Only alert if avg > 20€ and 2x increase
                cat_obj = db.query(Category).filter(Category.id == cat_id).first()
                insights.append(Insight(
                    type="anomaly",
                    title=f"Alerte catégorie : {cat_obj.name}",
                    description=f"Vos dépenses en '{cat_obj.name}' ({round(current_total, 2)}€) sont plus de 2x supérieures à votre moyenne habituelle ({round(avg, 2)}€).",
                    severity="medium",
                    value=current_total
                ))

    # 4. Positive Insights
    if savings_rate > 30:
        insights.append(Insight(
            type="positive",
            title="Excellent taux d'épargne",
            description="Félicitations ! Vous épargnez plus de 30% de vos revenus ce mois-ci.",
            severity="low",
            value=savings_rate
        ))
    
    if runway_months > 12:
        insights.append(Insight(
            type="positive",
            title="Sérénité financière",
            description="Votre fonds de sécurité couvre plus d'un an de dépenses. Vous êtes très bien protégé.",
            severity="low",
            value=runway_months
        ))

    from app.models.dismissed_insight import DismissedInsight
    dismissed = db.query(DismissedInsight.title).all()
    dismissed_titles = {d.title for d in dismissed}
    
    final_insights = [i for i in insights if i.title not in dismissed_titles]

    return IntelligentInsights(health_score=health_score, insights=final_insights)


class DismissInsightRequest(BaseModel):
    title: str


@router.post("/insights/dismiss")
async def dismiss_insight(request: DismissInsightRequest, db: Session = Depends(get_db)):
    from app.models.dismissed_insight import DismissedInsight
    existing = db.query(DismissedInsight).filter(DismissedInsight.title == request.title).first()
    if not existing:
        new_dismissed = DismissedInsight(title=request.title)
        db.add(new_dismissed)
        db.commit()
    return {"status": "success"}


