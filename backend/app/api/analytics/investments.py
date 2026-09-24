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

from .utils import (
    _tx_sample,
    _tx_read,
    _savings_account_ids,
    _savings_events_by_account,
    _savings_total_at,
    _get_ticket_restaurant_account_ids,
)


@router.get("/investments")
async def investments_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):
    # If account_id is provided, check if it's an investment account.
    # If not, ignore it to show a global investment overview on the dashboard.
    target_account = None
    if account_id:
        target_account = db.query(Account).filter(Account.id == account_id).first()
    
    query = db.query(Account).filter(Account.type.in_(["investissement", "assurance_vie"]), Account.active.is_(True))
    if target_account and target_account.type in ["investissement", "assurance_vie"]:
        query = query.filter(Account.id == account_id)
    
    investment_accounts = query.all()
    
    rates = await get_exchange_rates("EUR")

    start_date = None
    end_date = datetime.now()
    if month and year:
        start_date = datetime(year, month, 1)
        end_date = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

    latest_snapshots_subquery = (
        db.query(
            BalanceSnapshot.account_id.label("account_id"),
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .filter(BalanceSnapshot.date <= end_date)
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_snapshots_ids = (
        db.query(func.max(BalanceSnapshot.id).label("max_id"))
        .join(
            latest_snapshots_subquery,
            (BalanceSnapshot.account_id == latest_snapshots_subquery.c.account_id)
            & (BalanceSnapshot.date == latest_snapshots_subquery.c.max_date),
        )
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_values_rows = (
        db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
        .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
        .all()
    )
    latest_values = {row.account_id: float(row.current_value or 0.0) for row in latest_values_rows}

    # Fallback for accounts without snapshots
    for acc in investment_accounts:
        if acc.id not in latest_values:
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == acc.id, Transaction.date <= end_date)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                latest_values[acc.id] = float(last_tx.running_balance)

    items = []
    total_net_invested_eur = 0.0
    total_current_value_eur = 0.0
    
    for account in investment_accounts:
        flows = await _calculate_investment_flows(db, account, end_date, start_date=start_date, target_currency="EUR")
        net_invested_eur = flows["net_invested_target"]
        
        raw_current_value = latest_values.get(account.id)
        if raw_current_value is not None:
            current_value_eur = raw_current_value / rates.get(account.currency, 1.0)
        else:
            # Fallback: use net invested as current value if no snapshots exist
            current_value_eur = net_invested_eur
        
        gain_eur = current_value_eur - net_invested_eur
        performance_pct = (gain_eur / net_invested_eur * 100.0) if net_invested_eur > 0 else 0.0

        total_net_invested_eur += net_invested_eur
        total_current_value_eur += current_value_eur
        
        display_verse = flows["total_verse_target"]

        items.append(
            {
                "account_id": account.id,
                "account_name": account.name,
                "total_verse": round(display_verse, 2),
                "total_retire": round(flows["total_retire_target"], 2),
                "net_invested": round(net_invested_eur, 2),
                "current_value": round(current_value_eur, 2),
                "gain_eur": round(gain_eur, 2),
                "performance_pct": round(performance_pct, 2),
                "currency": account.currency
            }
        )

    total_gain_eur = total_current_value_eur - total_net_invested_eur
    total_performance_pct = (total_gain_eur / total_net_invested_eur * 100.0) if total_net_invested_eur > 0 else 0.0
    return {
        "total_net_invested": round(total_net_invested_eur, 2),
        "total_current_value": round(total_current_value_eur, 2),
        "total_gain_eur": round(total_gain_eur, 2),
        "total_performance_pct": round(total_performance_pct, 2),
        "items": items,
    }


async def _calculate_investment_flows(db: Session, account: Account, end_date: datetime, start_date: Optional[datetime] = None, target_currency: str = "EUR") -> dict:
    # 1. Determine the baseline
    # If start_date is provided, we want the value AT start_date as baseline
    # If start_date is None, we look for the latest is_zero_point snapshot
    
    baseline_date = None
    baseline_val_raw = 0.0
    
    if start_date:
        # We want the value at the beginning of the period
        # Check for latest snapshot at or before start_date
        last_snap = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.date < start_date)
            .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
            .first()
        )
        if last_snap:
            baseline_val_raw = float(last_snap.current_value)
            baseline_date = last_snap.date
        else:
            # Fallback to latest transaction balance before start_date
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == account.id, Transaction.date < start_date)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                baseline_val_raw = float(last_tx.running_balance)
                baseline_date = last_tx.date
        
        # If still nothing, it means the account started DURING or AFTER start_date
        # So baseline is 0 and we will pick up the Solde Initial/versements in the loop
    else:
        # All-time baseline: latest is_zero_point snapshot
        zero_point = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.is_zero_point.is_(True))
            .filter(BalanceSnapshot.date <= end_date)
            .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
            .first()
        )
        if zero_point:
            baseline_val_raw = float(zero_point.current_value)
            baseline_date = zero_point.date

    # Convert baseline value to target currency
    baseline_val_target = 0.0
    if baseline_val_raw != 0:
        baseline_val_target = await convert_amount(baseline_val_raw, account.currency, target_currency, date=baseline_date.date() if baseline_date else None, db=db)
    
    total_verse_target = 0.0
    total_retire_target = 0.0

    # Fetch flows
    itx_query = db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account.id, InvestmentTransaction.date <= end_date)
    if start_date:
        itx_query = itx_query.filter(InvestmentTransaction.date >= start_date)
    elif baseline_date:
        # For all-time, we only take transactions strictly after the zero-point snapshot
        itx_query = itx_query.filter(InvestmentTransaction.date > baseline_date)
    
    itxs = itx_query.all()
    for tx in itxs:
        amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
        if tx.type == "versement":
            total_verse_target += amount_target
        elif tx.type == "retrait":
            total_retire_target += amount_target
            
    # Regular Transactions
    rtx_query = db.query(Transaction).outerjoin(Category, Transaction.category_id == Category.id).filter(Transaction.account_id == account.id, Transaction.date <= end_date)
    if start_date:
        rtx_query = rtx_query.filter(Transaction.date >= start_date)
    elif baseline_date:
        rtx_query = rtx_query.filter(Transaction.date > baseline_date)
        
    rtxs = rtx_query.all()
    for tx in rtxs:
        merchant_lower = (tx.merchant or "").lower()
        # On investment accounts, "Solde Initial" OR "Entree" (that are NOT interests/dividends) are versements
        if tx.type == "Solde Initial" or tx.type == "Entree":
            # Exclude interests/dividends from net invested (they are gains)
            if tx.category and tx.category.name in ["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"]:
                continue
            if "dividende" in merchant_lower:
                continue
            # "vente" is often a withdrawal or internal move, but let's be careful. 
            # Usually "Vente" on an investment account means you got cash back (retrait from the market).
            if "vente" in merchant_lower:
                amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
                total_retire_target += amount_target
                continue

            amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
            total_verse_target += amount_target
        elif tx.type == "Sortie":
            # Exclude fees/taxes from net invested (they are losses/expenses, but part of performance, not capital flow)
            if any(k in merchant_lower for k in ["achat", "frais", "commission", "tax"]):
                continue
            amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
            total_retire_target += amount_target
            
    return {
        "baseline_val_target": baseline_val_target,
        "baseline_date": baseline_date,
        "total_verse_target": total_verse_target,
        "total_retire_target": total_retire_target,
        "net_invested_target": baseline_val_target + total_verse_target - total_retire_target
    }


@router.get("/investments/{account_id}")
async def investment_account_analytics(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.type not in ["investissement", "assurance_vie"]:
        raise HTTPException(status_code=422, detail="Account must be investissement or assurance_vie")
    
    rates = await get_exchange_rates("EUR")

    zero_point = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.is_zero_point.is_(True))
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )

    baseline_date = zero_point.date if zero_point else None
    
    # Use helper for flows in account currency
    flows = await _calculate_investment_flows(db, account, datetime.now(), target_currency=account.currency)
    net_invested = flows["net_invested_target"]
    baseline_date = flows["baseline_date"]

    tx_query = db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account_id)
    if baseline_date is not None:
        tx_query = tx_query.filter(InvestmentTransaction.date >= baseline_date)
    txs = tx_query.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).all()

    # Also include regular transactions for this account
    regular_tx_query = db.query(Transaction).outerjoin(Category, Transaction.category_id == Category.id).filter(Transaction.account_id == account_id)
    if baseline_date is not None:
        regular_tx_query = regular_tx_query.filter(Transaction.date >= baseline_date)
    regular_txs = regular_tx_query.order_by(Transaction.date.asc(), Transaction.id.asc()).all()

    latest_snapshot = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )
    if latest_snapshot:
        current_value = float(latest_snapshot.current_value)
    else:
        # Fallback 1: Sum of investment transactions (net flows)
        # We already have this in net_invested (calculated in account currency)
        current_value = net_invested
        
        # Fallback 2: Regular transactions if any (rare for investment accounts but possible)
        last_tx = db.query(Transaction).filter(Transaction.account_id == account_id).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
        if last_tx:
            current_value = float(last_tx.running_balance)

    gain = current_value - net_invested
    performance_pct = (gain / net_invested * 100.0) if net_invested > 0 else 0.0

    snapshots = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc())
        .all()
    )

    value_series = []
    for snap in snapshots:
        # For single account detail, we show values in account currency
        val = float(snap.current_value)
        value_series.append(
            {
                "id": snap.id,
                "date": snap.date.isoformat(),
                "current_value": round(val, 2),
                "current_value_raw": round(val, 2),
                "is_zero_point": bool(snap.is_zero_point),
                "note": snap.note,
            }
        )

    all_txs = []
    for tx in txs:
        # Convert to account currency
        amount = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        all_txs.append({
            "id": tx.id,
            "date": tx.date.isoformat(),
            "type": tx.type,
            "amount": round(amount, 2),
            "original_amount": round(float(tx.original_amount), 2),
            "currency": tx.currency,
            "note": tx.note,
            "asset_class": tx.asset_class,
            "sector": tx.sector,
            "geographic_zone": tx.geographic_zone,
        })
    for tx in regular_txs:
        # Convert to account currency
        amount = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        
        tx_type_display = "versement"
        if tx.type == "Sortie":
            tx_type_display = "retrait"
        elif tx.type == "Solde Initial":
            tx_type_display = "versement"
            
        all_txs.append({
            "id": tx.id,
            "date": tx.date.isoformat(),
            "type": tx_type_display,
            "amount": round(amount, 2),
            "original_amount": round(float(tx.original_amount), 2),
            "currency": tx.currency,
            "note": f"{tx.merchant}{' (' + tx.note + ')' if tx.note else ''}",
            "is_regular": True
        })
    all_txs.sort(key=lambda x: x["date"])

    return {
        "account_id": account.id,
        "account_name": account.name,
        "currency": account.currency,
        "baseline": {
            "date": baseline_date.isoformat() if baseline_date else None,
            "value": round(flows["baseline_val_target"], 2),
        },
        "totals": {
            "total_verse": round(flows["total_verse_target"], 2),
            "total_retire": round(flows["total_retire_target"], 2),
            "net_invested": round(net_invested, 2),
            "current_value": round(current_value, 2),
            "gain_eur": round(gain, 2),
            "performance_pct": round(performance_pct, 2),
        },
        "transactions": all_txs,
        "value_series": value_series,
    }


@router.get("/investments/{account_id}/performance-history")
async def investment_performance_history(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.type not in ["investissement", "assurance_vie"]:
        raise HTTPException(status_code=422, detail="Account must be investissement or assurance_vie")

    zero_point = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.is_zero_point.is_(True))
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )
    baseline_date = zero_point.date if zero_point else None
    baseline_value_raw = float(zero_point.current_value) if zero_point else 0.0
    
    # Baseline in account currency
    baseline_value = await convert_amount(baseline_value_raw, account.currency, account.currency, date=baseline_date.date() if baseline_date else None, db=db)

    txs = db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account_id)
    rtxs = db.query(Transaction).filter(Transaction.account_id == account_id)
    snaps = db.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account_id)
    if baseline_date is not None:
        txs = txs.filter(InvestmentTransaction.date >= baseline_date)
        rtxs = rtxs.filter(Transaction.date >= baseline_date)
        snaps = snaps.filter(BalanceSnapshot.date >= baseline_date)

    txs = txs.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).all()
    rtxs = rtxs.order_by(Transaction.date.asc(), Transaction.id.asc()).all()
    snaps = snaps.order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc()).all()

    tx_events_by_day: dict[str, dict[str, float]] = {}
    for tx in txs:
        key = tx.date.date().isoformat()
        if key not in tx_events_by_day:
            tx_events_by_day[key] = {"versement_target": 0.0, "retrait_target": 0.0}
        if tx.type == "dividende":
            continue
            
        amount_target = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        if tx.type == "versement":
            tx_events_by_day[key]["versement_target"] += amount_target
        elif tx.type == "retrait":
            tx_events_by_day[key]["retrait_target"] += amount_target
    
    rtx_q = db.query(Transaction).outerjoin(Category, Transaction.category_id == Category.id).filter(Transaction.account_id == account_id)
    if baseline_date:
        rtx_q = rtx_q.filter(Transaction.date >= baseline_date)
    for tx in rtx_q.all():
        key = tx.date.date().isoformat()
        if key not in tx_events_by_day:
            tx_events_by_day[key] = {"versement_target": 0.0, "retrait_target": 0.0}
        
        merchant_lower = (tx.merchant or "").lower()
        if tx.type in ["Entree", "Solde Initial"]:
            if tx.type == "Entree":
                if tx.category and tx.category.name in ["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"]:
                    continue
                if "vente" in merchant_lower or "dividende" in merchant_lower:
                    continue
            amount_target = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
            tx_events_by_day[key]["versement_target"] += amount_target
        elif tx.type == "Sortie":
            if any(k in merchant_lower for k in ["achat", "frais", "commission", "tax"]):
                continue
            amount_target = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
            tx_events_by_day[key]["retrait_target"] += amount_target

    # We need to collect ALL events and snapshots dates to calculate cumulative flows correctly
    all_dates = sorted(set(tx_events_by_day.keys()) | {s.date.date().isoformat() for s in snaps})
    
    running_verse = 0.0
    running_retire = 0.0
    series = []
    
    # Map snapshots by day for easy lookup
    snaps_by_day = {s.date.date().isoformat(): s for s in snaps}

    for day_str in all_dates:
        event = tx_events_by_day.get(day_str, {"versement_target": 0.0, "retrait_target": 0.0})
        running_verse += event["versement_target"]
        running_retire += event["retrait_target"]
        
        snap = snaps_by_day.get(day_str)
        if snap:
            net_invested = baseline_value + running_verse - running_retire
            current_value = float(snap.current_value)
            gain = current_value - net_invested
            performance_pct = (gain / net_invested * 100.0) if net_invested > 0 else 0.0
            series.append(
                {
                    "date": snap.date.isoformat(),
                    "net_invested": round(net_invested, 2),
                    "current_value": round(current_value, 2),
                    "gain_eur": round(gain, 2), # Named gain_eur but in account currency
                    "performance_pct": round(performance_pct, 2),
                    "is_zero_point": bool(snap.is_zero_point),
                }
            )

    return {"items": series}


@router.get("/investments-allocation")
async def investments_allocation(account_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Account).filter(Account.type.in_(["investissement", "assurance_vie"]), Account.active.is_(True))
    if account_id:
        query = query.filter(Account.id == account_id)
    
    investment_accounts = query.all()
    rates = await get_exchange_rates("EUR")
    now = datetime.now()
    
    latest_snapshots_subquery = (
        db.query(
            BalanceSnapshot.account_id.label("account_id"),
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .filter(BalanceSnapshot.date <= now)
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_snapshots_ids = (
        db.query(func.max(BalanceSnapshot.id).label("max_id"))
        .join(
            latest_snapshots_subquery,
            (BalanceSnapshot.account_id == latest_snapshots_subquery.c.account_id)
            & (BalanceSnapshot.date == latest_snapshots_subquery.c.max_date),
        )
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_values_rows = (
        db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
        .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
        .all()
    )
    current_by_account = {row.account_id: float(row.current_value or 0.0) for row in latest_values_rows}
    
    # Fallback for accounts without snapshots: use last running_balance from Transaction table
    for acc in investment_accounts:
        if acc.id not in current_by_account:
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == acc.id, Transaction.date <= now)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                current_by_account[acc.id] = float(last_tx.running_balance)

    total_current_value_eur = 0.0
    total_net_invested_eur = 0.0

    items = []
    for acc in investment_accounts:
        # Net invested converted with historical rates
        flows = await _calculate_investment_flows(db, acc, now, target_currency="EUR")
        net_invested_eur = flows["net_invested_target"]
        total_net_invested_eur += net_invested_eur

        raw_value = current_by_account.get(acc.id)
        if raw_value is not None:
            # Current value converted with latest rates
            value_eur = raw_value / rates.get(acc.currency, 1.0)
        else:
            # Fallback: use net invested as current value
            value_eur = net_invested_eur
            
        total_current_value_eur += value_eur

        items.append(
            {
                "account_id": acc.id,
                "account_name": acc.name,
                "current_value": round(value_eur, 2),
                "net_invested": round(net_invested_eur, 2),
                "gain_eur": round(value_eur - net_invested_eur, 2),
                "currency": acc.currency,
            }
        )

    # Re-calculate percentages based on EUR values
    for item in items:
        item["percentage"] = round((item["current_value"] / total_current_value_eur * 100.0), 2) if total_current_value_eur > 0 else 0.0

    total_gain_eur = total_current_value_eur - total_net_invested_eur
    total_perf_pct = (total_gain_eur / total_net_invested_eur * 100.0) if total_net_invested_eur > 0 else 0.0

    items.sort(key=lambda i: i["current_value"], reverse=True)
    return {
        "total_current_value": round(total_current_value_eur, 2),
        "total_net_invested": round(total_net_invested_eur, 2),
        "total_gain_eur": round(total_gain_eur, 2),
        "total_performance_pct": round(total_perf_pct, 2),
        "items": items
    }


@router.get("/investments-allocation-advanced")
async def investments_allocation_advanced(db: Session = Depends(get_db)):
    """
    Returns advanced asset allocation: by asset class, sector and geographic zone.
    """
    investment_accounts = db.query(Account).filter(Account.type.in_(["investissement", "assurance_vie"]), Account.active.is_(True)).all()
    rates = await get_exchange_rates("EUR")
    now = datetime.now()
    
    latest_snapshots_subquery = (
        db.query(
            BalanceSnapshot.account_id.label("account_id"),
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .filter(BalanceSnapshot.date <= now)
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_snapshots_ids = (
        db.query(func.max(BalanceSnapshot.id).label("max_id"))
        .join(
            latest_snapshots_subquery,
            (BalanceSnapshot.account_id == latest_snapshots_subquery.c.account_id)
            & (BalanceSnapshot.date == latest_snapshots_subquery.c.max_date),
        )
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_values_rows = (
        db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
        .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
        .all()
    )
    current_by_account = {row.account_id: float(row.current_value or 0.0) for row in latest_values_rows}
    
    # Fallback for accounts without snapshots
    for acc in investment_accounts:
        if acc.id not in current_by_account:
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == acc.id, Transaction.date <= now)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                current_by_account[acc.id] = float(last_tx.running_balance)

    # Aggregations
    # Structure: { "Category Name": { "value": 0.0, "items": { account_id: { name: "", value: 0.0 } } } }
    by_asset_class = {}
    by_sector = {}
    by_zone = {}
    total_value_eur = 0.0

    def _add_to_agg(agg_dict, cat_name, val, acc):
        if cat_name not in agg_dict:
            agg_dict[cat_name] = {"value": 0.0, "items": {}}
        
        agg_dict[cat_name]["value"] += val
        
        acc_id = acc.id
        if acc_id not in agg_dict[cat_name]["items"]:
            agg_dict[cat_name]["items"][acc_id] = {"account_id": acc_id, "account_name": acc.name, "value": 0.0}
        
        agg_dict[cat_name]["items"][acc_id]["value"] += val

    for acc in investment_accounts:
        raw_val = current_by_account.get(acc.id, 0.0)
        val_eur = raw_val / rates.get(acc.currency, 1.0)
        total_value_eur += val_eur

        txs_with_allocation = db.query(InvestmentTransaction).filter(
            InvestmentTransaction.account_id == acc.id,
            InvestmentTransaction.asset_class.isnot(None)
        ).all()

        if txs_with_allocation:
            total_tx_amount = sum(abs(tx.amount) for tx in txs_with_allocation)
            if total_tx_amount > 0:
                for tx in txs_with_allocation:
                    weight = abs(tx.amount) / total_tx_amount
                    tx_val_eur = val_eur * weight
                    
                    _add_to_agg(by_asset_class, tx.asset_class or "Non classé", tx_val_eur, acc)
                    _add_to_agg(by_sector, tx.sector or "Non classé", tx_val_eur, acc)
                    _add_to_agg(by_zone, tx.geographic_zone or "Non classé", tx_val_eur, acc)
            else:
                _add_to_agg(by_asset_class, acc.asset_class or "Non classé", val_eur, acc)
                _add_to_agg(by_sector, acc.sector or "Non classé", val_eur, acc)
                _add_to_agg(by_zone, acc.geographic_zone or "Non classé", val_eur, acc)
        else:
            _add_to_agg(by_asset_class, acc.asset_class or "Non classé", val_eur, acc)
            _add_to_agg(by_sector, acc.sector or "Non classé", val_eur, acc)
            _add_to_agg(by_zone, acc.geographic_zone or "Non classé", val_eur, acc)

    def _format_agg(agg_dict):
        result = []
        for name, data in agg_dict.items():
            val = data["value"]
            pct = (val / total_value_eur * 100.0) if total_value_eur > 0 else 0.0
            
            # Format items and sort them by value
            items = []
            for item in data["items"].values():
                item_pct = (item["value"] / val * 100.0) if val > 0 else 0.0
                items.append({
                    "account_id": item["account_id"],
                    "account_name": item["account_name"],
                    "value": round(item["value"], 2),
                    "percentage_of_group": round(item_pct, 2)
                })
            items.sort(key=lambda x: x["value"], reverse=True)

            result.append({
                "name": name,
                "value": round(val, 2),
                "percentage": round(pct, 2),
                "items": items
            })
        return sorted(result, key=lambda x: x["value"], reverse=True)

    return {
        "total_value_eur": round(total_value_eur, 2),
        "by_asset_class": _format_agg(by_asset_class),
        "by_sector": _format_agg(by_sector),
        "by_geographic_zone": _format_agg(by_zone)
    }


@router.get("/patrimoine-allocation")
async def patrimoine_allocation(db: Session = Depends(get_db)):
    """
    Returns the distribution of active wealth (all accounts: courant, epargne, investissement).
    """
    accounts = db.query(Account).filter(Account.active.is_(True)).all()
    rates = await get_exchange_rates("EUR")
    now = datetime.now()
    
    # Pre-fetch latest snapshots for all accounts to optimize queries
    latest_snapshots_subquery = (
        db.query(
            BalanceSnapshot.account_id.label("account_id"),
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .filter(BalanceSnapshot.date <= now)
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_snapshots_ids = (
        db.query(func.max(BalanceSnapshot.id).label("max_id"))
        .join(
            latest_snapshots_subquery,
            (BalanceSnapshot.account_id == latest_snapshots_subquery.c.account_id)
            & (BalanceSnapshot.date == latest_snapshots_subquery.c.max_date),
        )
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_snapshots_rows = (
        db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
        .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
        .all()
    )
    current_by_snapshot = {row.account_id: float(row.current_value or 0.0) for row in latest_snapshots_rows}

    # Pre-fetch latest transaction running balance for all accounts to optimize queries
    account_last_tx = (
        db.query(
            Transaction.account_id.label("account_id"),
            func.max(Transaction.date).label("max_date"),
        )
        .filter(Transaction.date <= now)
        .group_by(Transaction.account_id)
        .subquery()
    )

    latest_tx_ids = (
        db.query(func.max(Transaction.id).label("max_id"))
        .join(
            account_last_tx,
            (Transaction.account_id == account_last_tx.c.account_id) & (Transaction.date == account_last_tx.c.max_date),
        )
        .group_by(Transaction.account_id)
        .subquery()
    )

    latest_tx_rows = (
        db.query(Transaction.account_id, Transaction.running_balance)
        .join(latest_tx_ids, Transaction.id == latest_tx_ids.c.max_id)
        .all()
    )
    current_by_tx = {row.account_id: float(row.running_balance or 0.0) for row in latest_tx_rows}

    total_patrimoine_eur = 0.0
    items = []
    
    for acc in accounts:
        val = 0.0
        if acc.id in current_by_snapshot:
            val = current_by_snapshot[acc.id]
        elif acc.id in current_by_tx:
            val = current_by_tx[acc.id]
            
        val_eur = val / rates.get(acc.currency, 1.0)
        total_patrimoine_eur += val_eur
        
        if acc.type == "assurance_vie":
            euros_pct = acc.fonds_euros_pct if acc.fonds_euros_pct is not None else 100.0
            investis_pct = acc.fonds_investis_pct if acc.fonds_investis_pct is not None else 0.0
            
            val_euros = val * (euros_pct / 100.0)
            val_euros_eur = val_eur * (euros_pct / 100.0)
            
            val_investis = val * (investis_pct / 100.0)
            val_investis_eur = val_eur * (investis_pct / 100.0)
            
            items.append({
                "account_id": acc.id,
                "account_name": f"{acc.name} - Fonds Euro",
                "type": "epargne",
                "currency": acc.currency,
                "balance": round(val_euros, 2),
                "balance_eur": round(val_euros_eur, 2),
                "institution": acc.institution,
            })
            
            items.append({
                "account_id": acc.id,
                "account_name": f"{acc.name} - Investi",
                "type": "investissement",
                "currency": acc.currency,
                "balance": round(val_investis, 2),
                "balance_eur": round(val_investis_eur, 2),
                "institution": acc.institution,
            })
        else:
            items.append({
                "account_id": acc.id,
                "account_name": acc.name,
                "type": acc.type,
                "currency": acc.currency,
                "balance": round(val, 2),
                "balance_eur": round(val_eur, 2),
                "institution": acc.institution,
            })
            
    for item in items:
        item["percentage"] = round((item["balance_eur"] / total_patrimoine_eur * 100.0), 2) if total_patrimoine_eur > 0 else 0.0

    items.sort(key=lambda i: i["balance_eur"], reverse=True)
    
    return {
        "total_patrimoine": round(total_patrimoine_eur, 2),
        "items": items
    }


@router.get("/asset-allocation/suggestions")
def get_asset_allocation_suggestions(db: Session = Depends(get_db)):
    """
    Returns unique values for asset classes, sectors and geographic zones
    to be used for autocompletion in the frontend.
    """
    # Unique values from accounts
    acc_classes = db.query(Account.asset_class).filter(Account.asset_class.isnot(None)).distinct().all()
    acc_sectors = db.query(Account.sector).filter(Account.sector.isnot(None)).distinct().all()
    acc_zones = db.query(Account.geographic_zone).filter(Account.geographic_zone.isnot(None)).distinct().all()
    
    # Unique values from investment transactions
    tx_classes = db.query(InvestmentTransaction.asset_class).filter(InvestmentTransaction.asset_class.isnot(None)).distinct().all()
    tx_sectors = db.query(InvestmentTransaction.sector).filter(InvestmentTransaction.sector.isnot(None)).distinct().all()
    tx_zones = db.query(InvestmentTransaction.geographic_zone).filter(InvestmentTransaction.geographic_zone.isnot(None)).distinct().all()
    
    # Flatten and unique
    classes = sorted(list(set([c[0] for c in acc_classes + tx_classes if c[0]])))
    sectors = sorted(list(set([s[0] for s in acc_sectors + tx_sectors if s[0]])))
    zones = sorted(list(set([z[0] for z in acc_zones + tx_zones if z[0]])))
    
    # Default common values
    default_classes = ["Actions", "Obligations", "Immobilier", "Liquidités", "Crypto", "Or & Matières Premières", "Private Equity"]
    default_sectors = ["Tech", "Santé", "Finance", "Energie", "Industrie", "Consommation", "Télécoms", "Luxe", "SaaS", "E-commerce", "Tourisme"]
    default_zones = ["Europe", "USA", "Asie", "Marchés Émergents", "France", "Monde", "Chine", "Japon"]
    
    return {
        "asset_classes": sorted(list(set(classes + default_classes))),
        "sectors": sorted(list(set(sectors + default_sectors))),
        "geographic_zones": sorted(list(set(zones + default_zones)))
    }


@router.get("/wealth-simulation", response_model=WealthSimulationResponse)
async def wealth_simulation(
    initial_capital: float = Query(ge=0),
    monthly_contribution: float = Query(ge=0),
    annual_return_pct: float = Query(ge=-100, le=1000),
    years: int = Query(ge=1, le=50, default=15),
    volatility_pct: float = Query(ge=0, le=100, default=0.0),
    inflation_rate_pct: float = Query(ge=-50, le=100, default=0.0),
    contribution_indexation_pct: float = Query(ge=-50, le=100, default=0.0),
    tax_rate_pct: float = Query(ge=0, le=100, default=0.0),
    tax_deferred: bool = Query(default=True),
    events: Optional[str] = Query(default=None),
):
    """
    Simulates wealth growth over time with monthly contributions, compounded interest,
    inflation adjustment, tax drag, contribution indexation, one-off events, and Monte Carlo volatility.
    """
    import json
    import random

    parsed_events = []
    if events:
        try:
            parsed_events = json.loads(events)
            if not isinstance(parsed_events, list):
                parsed_events = []
        except Exception:
            parsed_events = []

    events_by_year = {}
    for ev in parsed_events:
        try:
            y = int(ev.get("year", 0))
            amt = float(ev.get("amount", 0.0))
            lbl = str(ev.get("label", "Événement"))
            if y not in events_by_year:
                events_by_year[y] = []
            events_by_year[y].append({"amount": amt, "label": lbl})
        except (ValueError, TypeError):
            continue

    num_trials = 1000 if volatility_pct > 0 else 1

    trials_value_by_year = {y: [] for y in range(years + 1)}
    trials_real_value_by_year = {y: [] for y in range(years + 1)}
    trials_interest_by_year = {y: [] for y in range(years + 1)}
    trials_tax_by_year = {y: [] for y in range(years + 1)}
    trials_contributions_by_year = {y: [] for y in range(years + 1)}

    # Initialize year 0
    for _ in range(num_trials):
        trials_value_by_year[0].append(initial_capital)
        trials_real_value_by_year[0].append(initial_capital)
        trials_interest_by_year[0].append(0.0)
        trials_tax_by_year[0].append(0.0)
        trials_contributions_by_year[0].append(0.0)

    # Convert rates
    annual_rate_decimal = annual_return_pct / 100.0
    monthly_rate_det = (1 + annual_rate_decimal) ** (1/12) - 1 if annual_rate_decimal > -1 else -1.0
    
    volatility_decimal = volatility_pct / 100.0
    monthly_mean = annual_rate_decimal / 12.0
    monthly_std = volatility_decimal / (12.0 ** 0.5)

    for trial in range(num_trials):
        current_total = initial_capital
        cumulative_contributions = 0.0
        cumulative_interest = 0.0
        cumulative_tax_paid = 0.0
        cumulative_events = 0.0

        for y in range(1, years + 1):
            contrib_rate = (1 + contribution_indexation_pct / 100.0) ** (y - 1)
            monthly_contrib = monthly_contribution * contrib_rate

            interest_this_year = 0.0
            contributions_this_year = 0.0

            for m in range(1, 13):
                if volatility_pct > 0:
                    r_m = random.normalvariate(monthly_mean, monthly_std)
                else:
                    r_m = monthly_rate_det

                interest_m = current_total * r_m
                interest_this_year += interest_m
                current_total += interest_m + monthly_contrib
                contributions_this_year += monthly_contrib

            cumulative_interest += interest_this_year
            cumulative_contributions += contributions_this_year

            # Apply annual tax if not deferred
            if not tax_deferred and tax_rate_pct > 0:
                if interest_this_year > 0:
                    tax_y = interest_this_year * (tax_rate_pct / 100.0)
                    current_total -= tax_y
                    cumulative_tax_paid += tax_y
                    cumulative_interest -= tax_y

            # Apply events
            if y in events_by_year:
                for ev in events_by_year[y]:
                    current_total += ev["amount"]
                    cumulative_events += ev["amount"]
                if current_total < 0:
                    current_total = 0.0

            inflation_factor = (1 + inflation_rate_pct / 100.0) ** y

            if tax_deferred and tax_rate_pct > 0:
                gain_y = current_total - initial_capital - cumulative_contributions - cumulative_events
                tax_due_y = max(0.0, gain_y * (tax_rate_pct / 100.0))
                
                net_nominal = current_total - tax_due_y
                net_real = net_nominal / inflation_factor
                net_interest = cumulative_interest - tax_due_y
                tax_val = tax_due_y
            else:
                net_nominal = current_total
                net_real = current_total / inflation_factor
                net_interest = cumulative_interest
                tax_val = cumulative_tax_paid

            trials_value_by_year[y].append(net_nominal)
            trials_real_value_by_year[y].append(net_real)
            trials_interest_by_year[y].append(net_interest)
            trials_tax_by_year[y].append(tax_val)
            trials_contributions_by_year[y].append(cumulative_contributions)

    items = []
    p10_idx = int(0.10 * num_trials)
    p50_idx = int(0.50 * num_trials)
    p90_idx = int(0.90 * num_trials)

    if volatility_pct > 0:
        for y in range(years + 1):
            trials_value_by_year[y].sort()
            trials_real_value_by_year[y].sort()
            trials_interest_by_year[y].sort()
            trials_tax_by_year[y].sort()

            p10_val = trials_value_by_year[y][p10_idx]
            p50_val = trials_value_by_year[y][p50_idx]
            p90_val = trials_value_by_year[y][p90_idx]

            p10_real = trials_real_value_by_year[y][p10_idx]
            p50_real = trials_real_value_by_year[y][p50_idx]
            p90_real = trials_real_value_by_year[y][p90_idx]

            contrib_median = trials_contributions_by_year[y][p50_idx]
            interest_median = trials_interest_by_year[y][p50_idx]
            tax_median = trials_tax_by_year[y][p50_idx]

            event_applied_str = None
            if y in events_by_year:
                event_applied_str = ", ".join([
                    f"{ev['label']} ({'+' if ev['amount'] >= 0 else ''}{int(ev['amount'])}€)"
                    for ev in events_by_year[y]
                ])

            items.append(WealthSimulationPoint(
                year=y,
                initial_capital=round(initial_capital, 2),
                total_contributions=round(contrib_median, 2),
                total_interest=round(interest_median, 2),
                total_value=round(p50_val, 2),
                total_value_real=round(p50_real, 2),
                total_value_p10=round(p10_val, 2),
                total_value_p50=round(p50_val, 2),
                total_value_p90=round(p90_val, 2),
                total_value_p10_real=round(p10_real, 2),
                total_value_p50_real=round(p50_real, 2),
                total_value_p90_real=round(p90_real, 2),
                total_tax_paid=round(tax_median, 2),
                event_applied=event_applied_str
            ))
    else:
        for y in range(years + 1):
            val = trials_value_by_year[y][0]
            real_val = trials_real_value_by_year[y][0]
            interest_val = trials_interest_by_year[y][0]
            tax_val = trials_tax_by_year[y][0]
            contrib_val = trials_contributions_by_year[y][0]

            event_applied_str = None
            if y in events_by_year:
                event_applied_str = ", ".join([
                    f"{ev['label']} ({'+' if ev['amount'] >= 0 else ''}{int(ev['amount'])}€)"
                    for ev in events_by_year[y]
                ])

            items.append(WealthSimulationPoint(
                year=y,
                initial_capital=round(initial_capital, 2),
                total_contributions=round(contrib_val, 2),
                total_interest=round(interest_val, 2),
                total_value=round(val, 2),
                total_value_real=round(real_val, 2),
                total_value_p10=round(val, 2),
                total_value_p50=round(val, 2),
                total_value_p90=round(val, 2),
                total_value_p10_real=round(real_val, 2),
                total_value_p50_real=round(real_val, 2),
                total_value_p90_real=round(real_val, 2),
                total_tax_paid=round(tax_val, 2),
                event_applied=event_applied_str
            ))

    last_item = items[-1]
    
    return WealthSimulationResponse(
        items=items,
        total_final=last_item.total_value,
        total_interest=last_item.total_interest,
        total_contributions=last_item.total_contributions,
        total_final_real=last_item.total_value_real,
        total_tax_paid=last_item.total_tax_paid,
        pessimistic_final=last_item.total_value_p10,
        median_final=last_item.total_value_p50,
        optimistic_final=last_item.total_value_p90
    )


def _apply_account_level(acc, val_eur, by_asset_class, by_sector, by_zone):
    # Asset Class
    ac = acc.asset_class or "Non classé"
    by_asset_class[ac] = by_asset_class.get(ac, 0.0) + val_eur

    # Sector
    sec = acc.sector or "Non classé"
    by_sector[sec] = by_sector.get(sec, 0.0) + val_eur

    # Zone
    zone = acc.geographic_zone or "Non classé"
    by_zone[zone] = by_zone.get(zone, 0.0) + val_eur


