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
from .insights import get_intelligent_insights
from .metrics import expenses_by_category, top_merchants
logger = get_logger(__name__)

router = APIRouter()


def calc_diff(curr: float, prev: float) -> tuple[float, float]:
    diff = curr - prev
    pct = (diff / abs(prev) * 100.0) if prev != 0 else 0.0
    return round(diff, 2), round(pct, 2)

from .utils import (
    _tx_sample,
    _tx_read,
    _savings_account_ids,
    _savings_events_by_account,
    _savings_total_at,
    _get_ticket_restaurant_account_ids,
)


@router.get("/cashflow-projection", response_model=CashflowProjection)
async def get_cashflow_projection(
    days: int = Query(default=30, ge=7, le=365),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Projects balance for the next X days based on current balance and recurring transactions.
    """
    now = datetime.now()
    end_date = now + timedelta(days=days)
    rates = await get_exchange_rates("EUR")

    # 1. Current balance
    current_bal = 0.0
    if account_id:
        acc = db.query(Account).filter(Account.id == account_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail="Account not found")
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
        tr_accounts = _get_ticket_restaurant_account_ids(db)
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

    # 2. Collect future occurrences
    projected_events_list: List[ProjectionEvent] = []
    
    recur_query = db.query(RecurringTransaction).filter(RecurringTransaction.is_active == True)
    if account_id:
        recur_query = recur_query.filter(RecurringTransaction.account_id == account_id)
    else:
        tr_accounts = _get_ticket_restaurant_account_ids(db)
        if tr_accounts:
            recur_query = recur_query.filter(RecurringTransaction.account_id.notin_(tr_accounts))
    
    recurring_defs = recur_query.all()
    
    for rd in recurring_defs:
        occurrences = get_recurring_occurrences(rd, now, end_date)
        for occ in occurrences:
            is_income = rd.type in ["Entree", "Interets", "versement", "dividende"]
            
            proj_amount = rd.amount
            
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


@router.get("/monthly-report", response_model=MonthlyReport)
async def get_monthly_report(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Consolidates data for a comprehensive monthly smart report.
    Compares with previous month and provides insights.
    """
    # 1. Current month data
    current_budget = await budget_analytics(month=month, year=year, account_id=account_id, db=db)
    
    # 2. Previous month data for comparison
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_budget = await budget_analytics(month=prev_month, year=prev_year, account_id=account_id, db=db)
    
    # 3. Insights (Anomalies, Score, etc.)
    insights_data = await get_intelligent_insights(month=month, year=year, account_id=account_id, db=db)
    
    # 4. Top categories
    cat_data = await expenses_by_category(month=month, year=year, account_id=account_id, db=db)
    top_categories = []
    # Sort items by total descending
    sorted_items = sorted(cat_data["items"], key=lambda x: x["total"], reverse=True)
    for item in sorted_items[:5]:
        top_categories.append({
            "name": item["category"]["name"],
            "total": item["total"],
            "icon": item["category"]["icon"],
            "color": item["category"]["color"]
        })
    
    # 5. Top merchants
    merch_data = await top_merchants(month=month, year=year, limit=5, account_id=account_id, db=db)
    
    # 6. Comparison logic
    inc_diff, inc_pct = calc_diff(current_budget["revenus_totaux"], prev_budget["revenus_totaux"])
    exp_diff, exp_pct = calc_diff(current_budget["depenses_reelles"], prev_budget["depenses_reelles"])
    sav_diff, sav_pct = calc_diff(current_budget["revenus_apres_depenses"], prev_budget["revenus_apres_depenses"])
    
    # Net worth change
    nw_change = current_budget["patrimoine_net_total"] - prev_budget["patrimoine_net_total"]

    # 7. Money Flow (Integrated)
    flow_data = await get_money_flow(month=month, year=year, account_id=account_id, db=db)
    
    return MonthlyReport(
        month=month,
        year=year,
        income=current_budget["revenus_totaux"],
        expenses=current_budget["depenses_totales"],
        real_expenses=current_budget["depenses_reelles"],
        savings=current_budget["revenus_apres_depenses"],
        savings_rate=current_budget["taux_epargne"],
        burn_rate=current_budget["burn_rate"],
        net_worth=current_budget["patrimoine_net_total"],
        net_worth_change=round(nw_change, 2),
        top_categories=top_categories,
        top_merchants=merch_data["items"],
        comparison=MonthlyComparison(
            income_diff=round(inc_diff, 2),
            income_diff_pct=round(inc_pct, 1),
            expenses_diff=round(exp_diff, 2),
            expenses_diff_pct=round(exp_pct, 1),
            savings_diff=round(sav_diff, 2),
            savings_diff_pct=round(sav_pct, 1)
        ),
        insights=insights_data.insights,
        health_score=insights_data.health_score,
        money_flow=flow_data
    )


async def _calculate_money_flow_data(month: int, year: int, db: Session, account_id: int | None = None):
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")
    
    # 1. Income (Filtered to checking accounts by default if account_id is None)
    # We re-implement a lean version here or call budget_analytics with type filter if supported.
    # To be precise and follow user instruction: we only want cash flowing INTO checking accounts.
    
    income_query = (
        db.query(Account.currency, func.sum(Transaction.amount).label("total"))
        .join(Account, Transaction.account_id == Account.id)
        .filter(Transaction.date >= start, Transaction.date < end)
        .filter(Transaction.type.in_(["Entree", "Interets", "Solde Initial"]))
        .filter(Transaction.is_transfer == False)
    )
    
    if account_id:
        income_query = income_query.filter(Transaction.account_id == account_id)
    else:
        # Focus on CHECKING accounts only
        income_query = income_query.filter(Account.type == "courant")
        tr_accounts = _get_ticket_restaurant_account_ids(db)
        if tr_accounts:
            income_query = income_query.filter(Transaction.account_id.notin_(tr_accounts))
        
    income_rows = income_query.group_by(Account.currency).all()
    income = sum(row.total / rates.get(row.currency, 1.0) for row in income_rows)
    
    # 2. Expenses (Sortie, is_transfer=False) from CHECKING accounts
    tx_query = (
        db.query(Transaction, Category.name.label("cat_name"))
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.date >= start, Transaction.date < end)
        .filter(Transaction.is_transfer == False)
    )
    
    if account_id:
        tx_query = tx_query.filter(Transaction.account_id == account_id)
    else:
        tx_query = tx_query.filter(Account.type == "courant")
        tr_accounts = _get_ticket_restaurant_account_ids(db)
        if tr_accounts:
            tx_query = tx_query.filter(Transaction.account_id.notin_(tr_accounts))
        
    transactions = tx_query.all()
    
    fixed_charges = 0.0
    variable_expenses = 0.0
    savings = 0.0
    investments = 0.0
    
    top_fixed_map = {}
    top_variable_map = {}
    top_savings_map = {}
    top_investments_map = {}
    
    for row in transactions:
        tx = row.Transaction
        cat_name = row.cat_name or "Sans catégorie"
        
        amount_eur = tx.amount / rates.get(tx.currency, 1.0)
        
        if tx.type == "Sortie":
            if cat_name in ["Epargne", "Épargne"]:
                savings += amount_eur
                top_savings_map[tx.merchant] = top_savings_map.get(tx.merchant, 0) + amount_eur
            elif cat_name in ["Investissement"]:
                investments += amount_eur
                top_investments_map[tx.merchant] = top_investments_map.get(tx.merchant, 0) + amount_eur
            elif tx.is_recurring:
                fixed_charges += amount_eur
                key = f"{tx.merchant} ({cat_name})"
                top_fixed_map[key] = top_fixed_map.get(key, 0) + amount_eur
            else:
                variable_expenses += amount_eur
                key = cat_name
                top_variable_map[key] = top_variable_map.get(key, 0) + amount_eur
                
    # 3. Investment Transactions
    # We REMOVE the direct query to InvestmentTransaction because for the "Checking Account" perspective,
    # these flows are already captured as 'Sortie' (Transferts) in the Transactions table of the checking account.
    # Including them again would double count the outflows.
    
    remainder = income - (fixed_charges + variable_expenses + savings + investments)
    
    return {
        "income": income,
        "fixed_charges": fixed_charges,
        "variable_expenses": variable_expenses,
        "savings": savings,
        "investments": investments,
        "remainder": remainder,
        "top_fixed": sorted([{"name": k, "amount": v} for k, v in top_fixed_map.items()], key=lambda x: x["amount"], reverse=True)[:5],
        "top_variable": sorted([{"name": k, "amount": v} for k, v in top_variable_map.items()], key=lambda x: x["amount"], reverse=True)[:5],
        "top_savings": sorted([{"name": k, "amount": v} for k, v in top_savings_map.items()], key=lambda x: x["amount"], reverse=True)[:5],
        "top_investments": sorted([{"name": k, "amount": v} for k, v in top_investments_map.items()], key=lambda x: x["amount"], reverse=True)[:5]
    }


@router.get("/money-flow", response_model=MoneyFlowReport)
async def get_money_flow(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Returns a detailed flow of where the money went during a month.
    """
    # 1. Current month
    curr = await _calculate_money_flow_data(month, year, db, account_id)
    
    # 2. Previous month
    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    prev = await _calculate_money_flow_data(prev_m, prev_y, db, account_id)
    
    def make_block(val_curr, val_prev, income):
        diff = val_curr - val_prev
        diff_pct = (diff / abs(val_prev) * 100) if val_prev != 0 else 0
        pct_inc = (val_curr / income * 100) if income != 0 else 0
        return MoneyFlowBlock(
            amount=round(val_curr, 2),
            percentage=round(pct_inc, 1),
            diff_prev_month=round(diff, 2),
            diff_prev_month_pct=round(diff_pct, 1)
        )

    return MoneyFlowReport(
        month=month,
        year=year,
        income=curr["income"],
        fixed_charges=make_block(curr["fixed_charges"], prev["fixed_charges"], curr["income"]),
        variable_expenses=make_block(curr["variable_expenses"], prev["variable_expenses"], curr["income"]),
        savings=make_block(curr["savings"], prev["savings"], curr["income"]),
        investments=make_block(curr["investments"], prev["investments"], curr["income"]),
        remainder=make_block(curr["remainder"], prev["remainder"], curr["income"]),
        top_fixed=[MoneyFlowItem(**x, is_recurring=True) for x in curr["top_fixed"]],
        top_variable=[MoneyFlowItem(**x) for x in curr["top_variable"]],
        top_savings=[MoneyFlowItem(**x) for x in curr["top_savings"]],
        top_investments=[MoneyFlowItem(**x) for x in curr["top_investments"]]
    )


@router.get("/sankey")
async def sankey_analytics(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # 1. Prepare time and rates
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")
    budget_data = await budget_analytics(month=month, year=year, account_id=account_id, db=db)
    
    # 2. Fetch all expenses by category (excluding internal transfers/savings/investments)
    exp_query = (
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
            # We filter out Investment/Savings categories because they have their own logic below
            ~Category.name.in_(["Investissement", "Epargne"])
        )
    )
    if account_id:
        exp_query = exp_query.filter(Transaction.account_id == account_id)

    exp_rows = exp_query.group_by(Category.id, Account.currency).all()

    # Aggregate expenses by category
    cat_expenses = {} # cat_id -> {obj, total}
    for row in exp_rows:
        cid = row.Category.id
        if cid not in cat_expenses:
            cat_expenses[cid] = {"obj": row.Category, "total": 0.0}
        cat_expenses[cid]["total"] += row.total / rates.get(row.currency, 1.0)

    # 3. Fetch Income sources
    inc_query = (
        db.query(
            Category,
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type.in_(["Entree", "Interets", "Solde Initial"]), # Include Solde Initial for better flow visualization
            Transaction.is_transfer == False
        )
    )
    if account_id:
        inc_query = inc_query.filter(Transaction.account_id == account_id)

    inc_rows = inc_query.group_by(Category.id, Account.currency).all()

    income_sources = [] # list of {name, total, color}
    total_income = 0.0
    for row in inc_rows:
        name = row.Category.name if row.Category else "Autres Revenus"
        color = row.Category.color if row.Category else "#10b981"
        val = row.total / rates.get(row.currency, 1.0)
        if val > 0:
            income_sources.append({"name": name, "total": val, "color": color})
            total_income += val

    # Add investment dividends to income
    itx_div_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
        InvestmentTransaction.type == "dividende",
        InvestmentTransaction.date >= start,
        InvestmentTransaction.date < end
    )
    if account_id:
        itx_div_query = itx_div_query.filter(InvestmentTransaction.account_id == account_id)

    div_total = 0.0
    for curr, amt in itx_div_query.group_by(Account.currency).all():
        div_total += amt / rates.get(curr, 1.0)

    if div_total > 0:
        income_sources.append({"name": "Dividendes", "total": div_total, "color": "#10b981"})
        total_income += div_total

    # 4. Build Nodes and Links
    nodes = []
    links = []

    def add_node(name, color=None):
        idx = len(nodes)
        nodes.append({"name": name, "color": color})
        return idx

    # Aggregator Node
    total_revenus_idx = add_node("Budget", "#94a3b8")

    # STAGE 1: Income -> Budget
    for src in income_sources:
        src_idx = add_node(src["name"], src["color"])
        links.append({"source": src_idx, "target": total_revenus_idx, "value": round(src["total"], 2), "color": src["color"]})

    # STAGE 2 & 3: Budget -> Groups -> Categories
    groups = {} # group_name -> {idx, total, color}

    # Investment "Group"
    invest_total = budget_data["investissements_du_mois"]
    if invest_total > 0:
        inv_idx = add_node("Investissements", "#6366f1")
        links.append({"source": total_revenus_idx, "target": inv_idx, "value": round(invest_total, 2), "color": "#6366f1"})

    # Savings "Group"
    savings_total = budget_data["revenus_apres_depenses"]
    if savings_total > 0:
        sav_idx = add_node("Épargne", "#10b981")
        links.append({"source": total_revenus_idx, "target": sav_idx, "value": round(savings_total, 2), "color": "#10b981"})
    elif savings_total < 0:
        # Spending more than income: add a 'Deficit' node as an incoming flow to Budget
        def_idx = add_node("Déficit / Trésorerie", "#f43f5e")
        links.append({"source": def_idx, "target": total_revenus_idx, "value": round(abs(savings_total), 2), "color": "#fecdd3"})
        total_income += abs(savings_total)

    # Expense Groups and Categories
    # Group categories by parent group to prevent link crossings in the Sankey diagram
    grouped_expenses = {} # group_name -> list of {"name": name, "color": color, "total": total}
    ungrouped_expenses = [] # list of {"name": name, "color": color, "total": total}

    for cid, data in cat_expenses.items():
        cat = data["obj"]
        total = data["total"]
        if total <= 0: continue

        item = {"name": cat.name, "color": cat.color, "total": total}
        if cat.group:
            if cat.group not in grouped_expenses:
                grouped_expenses[cat.group] = []
            grouped_expenses[cat.group].append(item)
        else:
            ungrouped_expenses.append(item)

    # Calculate group totals and sort groups by total value descending
    group_totals = {}
    for g_name, items in grouped_expenses.items():
        group_totals[g_name] = sum(item["total"] for item in items)
    
    sorted_groups = sorted(grouped_expenses.keys(), key=lambda g: group_totals[g], reverse=True)

    # Sort categories within each group by total value descending
    for g_name in grouped_expenses:
        grouped_expenses[g_name] = sorted(grouped_expenses[g_name], key=lambda x: x["total"], reverse=True)
    
    # Sort ungrouped categories by total value descending
    ungrouped_expenses = sorted(ungrouped_expenses, key=lambda x: x["total"], reverse=True)

    # STAGE 2: Add Group Nodes
    group_node_indices = {}
    for g_name in sorted_groups:
        g_idx = add_node(g_name, "#64748b")
        group_node_indices[g_name] = g_idx
        # Link Budget -> Group
        links.append({
            "source": total_revenus_idx,
            "target": g_idx,
            "value": round(group_totals[g_name], 2),
            "color": "#cbd5e1"
        })

    # STAGE 3: Add Category Nodes grouped by parent group
    for g_name in sorted_groups:
        g_idx = group_node_indices[g_name]
        for item in grouped_expenses[g_name]:
            cat_idx = add_node(item["name"], item["color"])
            links.append({
                "source": g_idx,
                "target": cat_idx,
                "value": round(item["total"], 2),
                "color": item["color"]
            })

    # Add ungrouped categories (connected directly to Budget)
    for item in ungrouped_expenses:
        cat_idx = add_node(item["name"], item["color"])
        links.append({
            "source": total_revenus_idx,
            "target": cat_idx,
            "value": round(item["total"], 2),
            "color": item["color"]
        })

    # Final check: if the Budget node is still unbalanced (more income than total links out),
    # it might be due to rounding or untracked flows. We balance it with a small "Ajustement" if needed.
    total_out = sum(l["value"] for l in links if l["source"] == total_revenus_idx)
    diff = total_income - total_out
    if diff > 1.0: # Only if significant (> 1 EUR)
        adj_idx = add_node("Reliquat / Ajustement", "#94a3b8")
        links.append({"source": total_revenus_idx, "target": adj_idx, "value": round(diff, 2), "color": "#cbd5e1"})

    return {"nodes": nodes, "links": links}


