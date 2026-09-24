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


@router.get("/tags")
async def tags_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        from app.models.tag import Tag, transaction_tags
        
        start = start_date
        end = end_date or datetime.now()
        base_currency = "EUR"
        rates = await get_exchange_rates(base_currency)
        
        if month and year and not start_date:
            start = datetime(year, month, 1)
            end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

        query = db.query(
            Tag.id,
            Tag.name,
            Tag.color,
            Account.currency,
            func.sum(Transaction.amount).label("total")
        ).join(transaction_tags, Tag.id == transaction_tags.c.tag_id) \
         .join(Transaction, Transaction.id == transaction_tags.c.transaction_id) \
         .join(Account, Transaction.account_id == Account.id) \
         .filter(Transaction.type == "Sortie", Transaction.is_transfer == False)

        if start:
            query = query.filter(Transaction.date >= start)
        query = query.filter(Transaction.date < end)
        
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        else:
            query = query.filter(Account.type.in_(["courant", "epargne"]))
            tr_accounts = _get_ticket_restaurant_account_ids(db)
            if tr_accounts:
                query = query.filter(Transaction.account_id.notin_(tr_accounts))

        rows = query.group_by(Tag.id, Account.currency).all()

        tag_totals = {}
        for row in rows:
            if row.id not in tag_totals:
                tag_totals[row.id] = {
                    "id": row.id,
                    "name": row.name,
                    "color": row.color,
                    "total_eur": 0.0
                }
            
            val_eur = row.total / rates.get(row.currency, 1.0)
            tag_totals[row.id]["total_eur"] += val_eur

        results = sorted(tag_totals.values(), key=lambda x: x["total_eur"], reverse=True)
        for r in results:
            r["total_eur"] = round(r["total_eur"], 2)
            
        return results
    except Exception as e:
        logger.error(f"Error in tags_analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/expenses-by-category")
async def expenses_by_category(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")

    query = (
        db.query(
            Category,
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
        )
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    else:
        tr_accounts = _get_ticket_restaurant_account_ids(db)
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    
    rows = query.group_by(Category.id, Account.currency).all()

    # Aggregate by category after conversion
    category_totals = {}
    for row in rows:
        cat_id = row.Category.id
        if cat_id not in category_totals:
            category_totals[cat_id] = {"category": row.Category, "total_eur": 0.0}
        
        val_eur = row.total / rates.get(row.currency, 1.0)
        category_totals[cat_id]["total_eur"] += val_eur

    total_amount_eur = sum(item["total_eur"] for item in category_totals.values())

    # ADD: Investment versements as a virtual "Investissement" category
    itx_inv_query = db.query(
        Account.currency,
        func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total"),
    ).join(Account, InvestmentTransaction.account_id == Account.id).filter(
        InvestmentTransaction.date >= start,
        InvestmentTransaction.date < end,
        InvestmentTransaction.type == "versement",
    )
    if account_id:
        itx_inv_query = itx_inv_query.filter(InvestmentTransaction.account_id == account_id)

    itx_rows = itx_inv_query.group_by(Account.currency).all()
    if itx_rows:
        inv_cat = db.query(Category).filter(Category.name == "Investissement").first()
        if inv_cat:
            if inv_cat.id not in category_totals:
                category_totals[inv_cat.id] = {"category": inv_cat, "total_eur": 0.0}

            for row in itx_rows:
                category_totals[inv_cat.id]["total_eur"] += row.total / rates.get(row.currency, 1.0)

            # Recalculate total amount
            total_amount_eur = sum(item["total_eur"] for item in category_totals.values())

    data = []
    for item in sorted(category_totals.values(), key=lambda x: x["total_eur"], reverse=True):
        amount = item["total_eur"]
        pct = (amount / total_amount_eur * 100.0) if total_amount_eur > 0 else 0.0
        cat = item["category"]
        data.append(
            {
                "category": {
                    "id": cat.id,
                    "name": cat.name,
                    "icon": cat.icon,
                    "color": cat.color,
                    "monthly_limit": cat.monthly_limit,
                    "annual_limit": cat.annual_limit,
                },
                "total": round(amount, 2),
                "percentage": round(pct, 2),
            }
        )

    return {
        "month": month,
        "year": year,
        "total": round(total_amount_eur, 2),
        "items": data,
    }


@router.get("/top-merchants")
async def top_merchants(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    limit: int = Query(default=5, ge=1, le=50),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    from app.models.merchant import Merchant
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")

    query = (
        db.query(
            func.coalesce(Merchant.name, Transaction.merchant).label("merchant"),
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .outerjoin(Merchant, Transaction.merchant_id == Merchant.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            func.coalesce(Category.name, "") != "Investissement"
        )
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    else:
        tr_accounts = _get_ticket_restaurant_account_ids(db)
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    
    rows = query.group_by(func.coalesce(Merchant.name, Transaction.merchant), Account.currency).all()

    # Aggregate by merchant after conversion
    merchant_totals = {}
    for row in rows:
        if row.merchant not in merchant_totals:
            merchant_totals[row.merchant] = 0.0
        val_eur = row.total / rates.get(row.currency, 1.0)
        merchant_totals[row.merchant] += val_eur

    sorted_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:limit]
    items = [{"merchant": name, "total": round(float(total), 2)} for name, total in sorted_merchants]
    return {"month": month, "year": year, "items": items}


@router.get("/kpi-history")
async def kpi_history(
    months_count: int = Query(default=6, ge=1, le=24), 
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):
    # Returns history of KPIs for sparklines
    now = datetime.now()
    savings_account_ids = _savings_account_ids(db)
    if account_id:
        savings_account_ids = [account_id] if account_id in savings_account_ids else []
    
    savings_account_map = {
        acc.id: acc
        for acc in db.query(Account).filter(Account.id.in_(savings_account_ids)).all()
    } if savings_account_ids else {}
    base_currency = "EUR"
    rates = await get_exchange_rates(base_currency)
    tr_accounts = _get_ticket_restaurant_account_ids(db)

    # Find the earliest transaction date to avoid showing empty future or past months
    earliest_tx_query = db.query(func.min(Transaction.date))
    if account_id:
        earliest_tx_query = earliest_tx_query.filter(Transaction.account_id == account_id)
    earliest_tx = earliest_tx_query.scalar()
    
    if not earliest_tx:
        return []

    results = []
    earliest_allowed_total = now.year * 12 + (now.month - 1) - (months_count - 1)
    overall_start = datetime(earliest_allowed_total // 12, (earliest_allowed_total % 12) + 1, 1)
    overall_end = datetime(now.year + (1 if now.month == 12 else 0), 1 if now.month == 12 else now.month + 1, 1)

    # 1. Batch query regular transactions grouped by month, currency, and type
    tx_month_label = func.strftime("%Y-%m", Transaction.date).label("m_label")
    tx_query = db.query(
        tx_month_label,
        Account.currency,
        Transaction.type,
        func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
    ).select_from(Transaction).join(Account, Transaction.account_id == Account.id).filter(
        Transaction.date >= overall_start, Transaction.date < overall_end
    )
    if not account_id:
        tx_query = tx_query.filter(Account.type.in_(["courant", "epargne"]))
        if tr_accounts:
            tx_query = tx_query.filter(Transaction.account_id.notin_(tr_accounts))
    else:
        tx_query = tx_query.filter(Transaction.account_id == account_id)
    
    tx_rows = tx_query.group_by(tx_month_label, Account.currency, Transaction.type).all()

    rev_map: dict[str, float] = {}
    dep_map: dict[str, float] = {}
    inte_map: dict[str, float] = {}
    inv_map: dict[str, float] = {}

    for row in tx_rows:
        m_lbl = row.m_label
        amount_eur = row.total / rates.get(row.currency, 1.0)
        if row.type in ("Entree", "Interets"):
            rev_map[m_lbl] = rev_map.get(m_lbl, 0.0) + amount_eur
        if row.type == "Interets":
            inte_map[m_lbl] = inte_map.get(m_lbl, 0.0) + amount_eur
        if row.type == "Sortie":
            dep_map[m_lbl] = dep_map.get(m_lbl, 0.0) + amount_eur

    # 2. Batch query investment transactions (dividends and versements)
    itx_month_label = func.strftime("%Y-%m", InvestmentTransaction.date).label("m_label")
    itx_query = db.query(
        itx_month_label,
        Account.currency,
        InvestmentTransaction.type,
        func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")
    ).join(Account, InvestmentTransaction.account_id == Account.id).filter(
        InvestmentTransaction.date >= overall_start, 
        InvestmentTransaction.date < overall_end,
        InvestmentTransaction.type.in_(["dividende", "versement"])
    )
    if account_id:
        itx_query = itx_query.filter(InvestmentTransaction.account_id == account_id)
    itx_rows = itx_query.group_by(itx_month_label, Account.currency, InvestmentTransaction.type).all()

    for row in itx_rows:
        m_lbl = row.m_label
        amount_eur = row.total / rates.get(row.currency, 1.0)
        if row.type == "dividende":
            rev_map[m_lbl] = rev_map.get(m_lbl, 0.0) + amount_eur
            inte_map[m_lbl] = inte_map.get(m_lbl, 0.0) + amount_eur
        elif row.type == "versement":
            inv_map[m_lbl] = inv_map.get(m_lbl, 0.0) + amount_eur

    # 3. Batch query category exclusions for Sortie -> Investissement/Epargne
    inv_cat_query = db.query(
        tx_month_label,
        Account.currency,
        func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
    ).select_from(Transaction).join(Account, Transaction.account_id == Account.id).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.date >= overall_start, Transaction.date < overall_end,
        Transaction.type == "Sortie",
        Category.name.in_(["Investissement", "Epargne"])
    )
    if not account_id:
        if tr_accounts:
            inv_cat_query = inv_cat_query.filter(Transaction.account_id.notin_(tr_accounts))
    else:
        inv_cat_query = inv_cat_query.filter(Transaction.account_id == account_id)
    inv_cat_rows = inv_cat_query.group_by(tx_month_label, Account.currency).all()

    for row in inv_cat_rows:
        m_lbl = row.m_label
        amount_eur = row.total / rates.get(row.currency, 1.0)
        inv_map[m_lbl] = inv_map.get(m_lbl, 0.0) + amount_eur

    # 4. Batch query category-based interests (excluding type Interets to avoid double count)
    inte_cat_query = db.query(
        tx_month_label,
        Account.currency,
        func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
    ).select_from(Transaction).join(Account, Transaction.account_id == Account.id).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.date >= overall_start, Transaction.date < overall_end,
        Transaction.type != "Interets",
        Category.name.in_(["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"])
    )
    if not account_id:
        inte_cat_query = inte_cat_query.filter(Account.type.in_(["courant", "epargne"]))
        if tr_accounts:
            inte_cat_query = inte_cat_query.filter(Transaction.account_id.notin_(tr_accounts))
    else:
        inte_cat_query = inte_cat_query.filter(Transaction.account_id == account_id)
    inte_cat_rows = inte_cat_query.group_by(tx_month_label, Account.currency).all()

    for row in inte_cat_rows:
        m_lbl = row.m_label
        amount_eur = row.total / rates.get(row.currency, 1.0)
        inte_map[m_lbl] = inte_map.get(m_lbl, 0.0) + amount_eur

    # 5. Preload savings events for all savings accounts up to overall_end
    all_savings_events = _savings_events_by_account(db, savings_account_ids, overall_end) if savings_account_ids else {}

    for i in range(months_count - 1, -1, -1):
        total_months = now.year * 12 + (now.month - 1) - i
        y = total_months // 12
        m = (total_months % 12) + 1

        start = datetime(y, m, 1)
        end = datetime(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)

        # Only include if month is NOT in the future AND there's data after the earliest tx
        if start > now:
            continue

        m_key = f"{y:04d}-{m:02d}"
        rev = rev_map.get(m_key, 0.0)
        inte = inte_map.get(m_key, 0.0)
        dep = dep_map.get(m_key, 0.0)
        inv = inv_map.get(m_key, 0.0)

        # If no revenue and no expense, and it's not the current month, skip to keep chart tight
        if rev == 0 and dep == 0 and not (now.year == y and now.month == m):
            continue

        # Epargne totale at end of month (calculated from in-memory preloaded events)
        epargne_total = 0.0
        for acc_id, items in all_savings_events.items():
            matching = [val for date_val, _, val in items if date_val <= end]
            if matching:
                val = matching[-1]
                acc = savings_account_map.get(acc_id)
                epargne_total += val / rates.get(acc.currency, 1.0) if acc else val
        
        real_dep = dep - inv
        results.append({
            "month": m,
            "year": y,
            "label": f"{m}/{y}",
            "base_currency": base_currency,
            "revenus": round(float(rev), 2),
            "interets": round(float(inte), 2),
            "depenses": round(float(dep), 2),
            "investissements": round(float(inv), 2),
            "epargne": round(float(epargne_total), 2),
            "epargne_flow": round(float(rev - real_dep), 2),
            "cash_flow": round(float(rev - dep), 2)
        })
        
    return results


@router.get("/timeseries")
async def timeseries_analytics(
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    now = datetime.now()
    monthly = []
    
    # Check if there's any transaction for the year to avoid empty charts
    any_tx = db.query(Transaction).filter(func.strftime("%Y", Transaction.date) == str(year))
    if account_id:
        any_tx = any_tx.filter(Transaction.account_id == account_id)
    
    if not any_tx.first():
        # If no data for the year, return empty instead of 12 zeros
        return {
            "year": year,
            "account_id": account_id,
            "monthly_flows": [],
            "balance_points": [],
            "salary_series": [],
        }

    rates = await get_exchange_rates("EUR")
    tr_accounts = _get_ticket_restaurant_account_ids(db)

    for month in range(1, 13):
        start = datetime(year, month, 1)
        end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

        # Don't show future months
        if start > now:
            continue

        # Correctly handle multi-currency for global view
        income_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type.in_(["Entree", "Interets"]),
        )
        
        expense_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
        )

        if account_id is not None:
            income_by_curr = income_by_curr.filter(Transaction.account_id == account_id)
            expense_by_curr = expense_by_curr.filter(Transaction.account_id == account_id)
        else:
            income_by_curr = income_by_curr.filter(Account.type.in_(["courant", "epargne"]))
            expense_by_curr = expense_by_curr.filter(Account.type.in_(["courant", "epargne"]))
            if tr_accounts:
                income_by_curr = income_by_curr.filter(Transaction.account_id.notin_(tr_accounts))
                expense_by_curr = expense_by_curr.filter(Transaction.account_id.notin_(tr_accounts))

        income_rows = income_by_curr.group_by(Account.currency).all()
        income = sum(row.total / rates.get(row.currency, 1.0) for row in income_rows)
        
        # ADD: Investment dividends
        itx_inc_query = db.query(Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.date >= start, InvestmentTransaction.date < end, InvestmentTransaction.type == "dividende"
        )
        if account_id:
            itx_inc_query = itx_inc_query.filter(InvestmentTransaction.account_id == account_id)
        
        itx_inc_rows = itx_inc_query.group_by(Account.currency).all()
        income += sum(row.total / rates.get(row.currency, 1.0) for row in itx_inc_rows)

        expense_rows = expense_by_curr.group_by(Account.currency).all()
        expense = sum(row.total / rates.get(row.currency, 1.0) for row in expense_rows)

        # ADD: Investment versements (if looking at this account, they are outflows of cash part?)
        # Actually, for global view, versements are already Sortie on bank accounts.
        # But if specifically on investment account, we might want to see them as "expense" of the budget?
        # Let's include versements in 'expense' only if account_id is specifically an investment account.
        if account_id:
            acc_obj = db.query(Account).filter(Account.id == account_id).first()
            if acc_obj and acc_obj.type == "investissement":
                itx_exp_query = db.query(Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")).join(Account, InvestmentTransaction.account_id == Account.id).filter(
                    InvestmentTransaction.date >= start, InvestmentTransaction.date < end, InvestmentTransaction.type == "versement"
                ).filter(InvestmentTransaction.account_id == account_id)
                itx_exp_rows = itx_exp_query.group_by(Account.currency).all()
                expense += sum(row.total / rates.get(row.currency, 1.0) for row in itx_exp_rows)
        
        # Only add month if it has data or is the current month
        if income > 0 or expense > 0 or (now.year == year and now.month == month):
            days = calendar.monthrange(year, month)[1]
            if now.year == year and now.month == month:
                days = now.day
                
            monthly.append(
                {
                    "month": month,
                    "income": round(float(income), 2),
                    "expense": round(float(expense), 2),
                    "burn_rate": round(float(expense) / max(days, 1), 2),
                }
            )

    # For balance points, if it's a global view, we should probably aggregate them or not show them.
    # But if account_id is provided, it's definitely fine.
    balance_points_query = db.query(Transaction).order_by(Transaction.date.asc(), Transaction.id.asc())
    if account_id is not None:
        balance_points_query = balance_points_query.filter(Transaction.account_id == account_id)
        balance_points = [
            {
                "date": tx.date.isoformat(),
                "running_balance": round(float(tx.running_balance), 2),
                "account_id": tx.account_id,
            }
            for tx in balance_points_query.all()
        ]
    else:
        # For global view, balance points are less meaningful if just interleaved.
        # Maybe we should return empty or aggregate them by day?
        # For now, let's keep it as is but it's a known limitation for global charts.
        balance_points = []

    salary_rows_query = (
        db.query(
            func.strftime("%m", Transaction.date).label("month"),
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            func.strftime("%Y", Transaction.date) == str(year),
            Category.name == "Salaire",
            Transaction.type == "Entree",
        )
        .group_by(func.strftime("%m", Transaction.date), Account.currency)
    )
    if account_id is not None:
        salary_rows_query = salary_rows_query.filter(Transaction.account_id == account_id)

    salary_data = salary_rows_query.all()
    salary_by_month = {}
    for row in salary_data:
        m = int(row.month)
        val_eur = row.total / rates.get(row.currency, 1.0)
        salary_by_month[m] = salary_by_month.get(m, 0.0) + val_eur
    
    salary_series = []
    for month in range(1, 13):
        # Only add to salary series if month has data and is not in future
        if datetime(year, month, 1) <= now and (salary_by_month.get(month, 0) > 0):
             salary_series.append({"month": month, "salary": salary_by_month.get(month, 0.0)})

    return {
        "year": year,
        "account_id": account_id,
        "monthly_flows": monthly,
        "balance_points": balance_points,
        "salary_series": salary_series,
    }


@router.get("/calendar")
async def calendar_analytics(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    start_month = datetime(year, month, 1)
    # End of month is start of next month
    if month == 12:
        end_month = datetime(year + 1, 1, 1)
    else:
        end_month = datetime(year, month + 1, 1)
        
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    sim_start = min(start_month, today)
    
    # 1. Fetch real transactions
    tx_query = db.query(Transaction).filter(
        Transaction.date >= sim_start,
        Transaction.date < end_month
    )
    inv_tx_query = db.query(InvestmentTransaction).filter(
        InvestmentTransaction.date >= sim_start,
        InvestmentTransaction.date < end_month
    )
    
    tr_accounts = _get_ticket_restaurant_account_ids(db)
    if account_id:
        tx_query = tx_query.filter(Transaction.account_id == account_id)
        inv_tx_query = inv_tx_query.filter(InvestmentTransaction.account_id == account_id)
    else:
        if tr_accounts:
            tx_query = tx_query.filter(Transaction.account_id.notin_(tr_accounts))
    
    real_txs = tx_query.all()
    real_inv_txs = inv_tx_query.all()
    
    # 2. Fetch recurring transactions and project them
    recur_query = db.query(RecurringTransaction).filter(RecurringTransaction.is_active == True)
    if account_id:
        recur_query = recur_query.filter(RecurringTransaction.account_id == account_id)
    else:
        if tr_accounts:
            recur_query = recur_query.filter(RecurringTransaction.account_id.notin_(tr_accounts))
    
    recurring_defs = recur_query.all()
    projected_events = []
    
    # Create a set of (recurring_id, date) for real transactions to deduplicate
    # We use date.date() to ignore time
    realized_recurrences = {
        (tx.recurring_transaction_id, tx.date.date()) 
        for tx in real_txs 
        if tx.recurring_transaction_id is not None
    }
    # Also include investment transactions
    for tx in real_inv_txs:
        if hasattr(tx, "recurring_transaction_id") and tx.recurring_transaction_id is not None:
            realized_recurrences.add((tx.recurring_transaction_id, tx.date.date()))
    
    for rd in recurring_defs:
        # Project for the whole month, but deduplicate
        occurrences = get_recurring_occurrences(rd, sim_start, end_month)
        for occ in occurrences:
            proj_date = occ
            proj_amount = rd.amount
            proj_note = rd.name
            
            # Check if it's a salary/TR recurrence
            from app.models.salary_config import SalaryConfig
            from app.models.salary_month import SalaryMonth
            from app.models.telecommuting_day import TelecommutingDay
            from app.core.finance import month_label_from_date
            
            salary_config = db.query(SalaryConfig).filter(
                (SalaryConfig.salary_recurring_id == rd.id) | 
                (SalaryConfig.ticket_recurring_id == rd.id)
            ).first()
            
            if salary_config:
                month_label = month_label_from_date(occ)
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
                    
                    if rd.id == salary_config.salary_recurring_id and salary_month.salary_date:
                        proj_date = datetime.combine(salary_month.salary_date, datetime.min.time())
                    if rd.id == salary_config.ticket_recurring_id and salary_month.ticket_date:
                        proj_date = datetime.combine(salary_month.ticket_date, datetime.min.time())
                
                if rd.id == salary_config.salary_recurring_id:
                    deduction = tt_days_count * salary_config.ticket_employee_share
                    proj_amount = salary_config.net_salary - deduction
                    proj_note = f"Salaire ({month_label})"
                elif rd.id == salary_config.ticket_recurring_id:
                    proj_amount = tt_days_count * salary_config.ticket_value
                    proj_note = f"Tickets Restaurant ({month_label})"
                    
            # Skip if already realized (we check month and recurring_id instead of exact date for salary to be safe)
            # Or just check exact date with the overriden proj_date
            if (rd.id, proj_date.date()) in realized_recurrences:
                continue
                
            projected_events.append({
                "id": f"proj_{rd.id}_{proj_date.isoformat()}",
                "date": proj_date.isoformat(),
                "name": proj_note,
                "amount": proj_amount,
                "type": rd.type,
                "category_id": rd.category_id,
                "is_projected": True,
                "recurring_id": rd.id,
                "currency": rd.currency,
                "account_id": rd.account_id
            })

    # 3. Format real transactions
    formatted_real = []
    for tx in real_txs:
        formatted_real.append({
            "id": f"tx_{tx.id}",
            "date": tx.date.isoformat(),
            "name": tx.merchant,
            "amount": tx.amount,
            "type": tx.type,
            "category_id": tx.category_id,
            "is_projected": False,
            "currency": tx.currency,
            "account_id": tx.account_id,
            "running_balance": getattr(tx, "running_balance", None)
        })
    
    for tx in real_inv_txs:
        formatted_real.append({
            "id": f"inv_{tx.id}",
            "date": tx.date.isoformat(),
            "name": f"[{tx.type.capitalize()}] {tx.note or 'Investissement'}",
            "amount": tx.amount,
            "type": tx.type,
            "category_id": None,
            "is_projected": False,
            "currency": tx.currency,
            "account_id": tx.account_id
        })
        
    # 4. Calculate daily balance projections
    daily_balances = []
    rates = await get_exchange_rates("EUR")
    
    # Initialize balances per account
    account_balances = {}
    active_accounts = db.query(Account).all()
    account_currencies = {acc.id: acc.currency for acc in active_accounts}
    
    if account_id:
        last_tx_before = db.query(Transaction).filter(
            Transaction.account_id == account_id,
            Transaction.date < sim_start
        ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
        account_balances[account_id] = last_tx_before.running_balance if last_tx_before else 0.0
    else:
        active_only = [a for a in active_accounts if a.active]
        for acc in active_only:
            last_tx_before = db.query(Transaction).filter(
                Transaction.account_id == acc.id,
                Transaction.date < sim_start
            ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
            account_balances[acc.id] = last_tx_before.running_balance if last_tx_before else 0.0

    # We simulate day by day
    all_events = sorted(formatted_real + projected_events, key=lambda x: x["date"])
    event_idx = 0
    
    temp_date = sim_start
    while temp_date < end_month:
        # Apply events for this day
        while event_idx < len(all_events) and datetime.fromisoformat(all_events[event_idx]["date"]).date() == temp_date.date():
            ev = all_events[event_idx]
            acc_id = ev.get("account_id")
            
            if acc_id is not None:
                if acc_id not in account_balances:
                    account_balances[acc_id] = 0.0

                positive_types = ["Entree", "Interets", "Solde Initial", "versement", "dividende"]
                negative_types = ["Sortie", "retrait"]
                
                # If it's a real transaction with a running_balance, we sync it exactly
                if not ev.get("is_projected") and ev.get("running_balance") is not None:
                    account_balances[acc_id] = ev["running_balance"]
                else:
                    amt = ev["amount"]
                    if ev["type"] == "Solde Initial":
                        account_balances[acc_id] = amt
                    elif ev["type"] in positive_types:
                        account_balances[acc_id] += amt
                    elif ev["type"] in negative_types:
                        account_balances[acc_id] -= amt

            event_idx += 1
            
        # Calculate daily total
        if account_id:
            current_bal = account_balances.get(account_id, 0.0)
        else:
            current_bal = 0.0
            for a_id, bal in account_balances.items():
                curr = account_currencies.get(a_id, "EUR")
                current_bal += bal / rates.get(curr, 1.0)

        if temp_date >= start_month:
            daily_balances.append({
                "date": temp_date.date().isoformat(),
                "balance": round(current_bal, 2)
            })
        temp_date += timedelta(days=1)

    return {
        "month": month,
        "year": year,
        "events": [ev for ev in sorted(formatted_real + projected_events, key=lambda x: x["date"]) if datetime.fromisoformat(ev["date"]) >= start_month],
        "daily_balances": daily_balances
    }


