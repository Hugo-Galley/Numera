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


@router.get("/budget")
async def budget_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        start = None
        end = datetime.now()
        base_currency = "EUR"
        rates = await get_exchange_rates(base_currency)
        
        if month and year:
            start = datetime(year, month, 1)
            end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

        # Get ticket restaurant accounts to exclude from global views
        tr_accounts = _get_ticket_restaurant_account_ids(db)

        # Get income grouped by account currency
        revenus_query_filter = ["Entree", "Interets"]
        if not month or not year:
            # Only include Solde Initial when looking at "All time"
            revenus_query_filter.append("Solde Initial")

        revenus_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.type.in_(revenus_query_filter),
            Transaction.is_transfer == False
        )
        if not account_id:
            # Global view: include both checking and savings accounts
            revenus_by_curr = revenus_by_curr.filter(Account.type.in_(["courant", "epargne"]))
            if tr_accounts:
                revenus_by_curr = revenus_by_curr.filter(Transaction.account_id.notin_(tr_accounts))
        else:
            revenus_by_curr = revenus_by_curr.filter(Transaction.account_id == account_id)

        if start:
            revenus_by_curr = revenus_by_curr.filter(Transaction.date >= start)
        revenus_by_curr = revenus_by_curr.filter(Transaction.date < end)

        revenus_rows = revenus_by_curr.group_by(Account.currency).all()
        revenus = sum(row.total / rates.get(row.currency, 1.0) for row in revenus_rows)

        # ADD: Investment transactions as income when looking at a specific account OR if they are dividends
        itx_revenus_query = db.query(
            Account.currency,
            func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")
        ).join(Account, InvestmentTransaction.account_id == Account.id)

        if not account_id:
            itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.type == "dividende")
        else:
            itx_revenus_query = itx_revenus_query.filter(
                InvestmentTransaction.account_id == account_id,
                InvestmentTransaction.type.in_(["versement", "dividende"])
            )

        if start:
            itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.date >= start)
        itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.date < end)

        itx_revenus_rows = itx_revenus_query.group_by(Account.currency).all()
        revenus += sum(row.total / rates.get(row.currency, 1.0) for row in itx_revenus_rows)

        # Calculate "Interets" separately — restricted to courant/epargne accounts
        interets_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).outerjoin(Category, Transaction.category_id == Category.id).filter(
            ((Transaction.type == "Interets") |
             (Category.name.in_(["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"]))),
            Transaction.is_transfer == False
        )
        if not account_id:
            interets_by_curr = interets_by_curr.filter(Account.type.in_(["courant", "epargne"]))
            if tr_accounts:
                interets_by_curr = interets_by_curr.filter(Transaction.account_id.notin_(tr_accounts))
        else:
            interets_by_curr = interets_by_curr.filter(Transaction.account_id == account_id)

        if start:
            interets_by_curr = interets_by_curr.filter(Transaction.date >= start)
        interets_by_curr = interets_by_curr.filter(Transaction.date < end)

        interets_rows = interets_by_curr.group_by(Account.currency).all()
        interets = sum(row.total / rates.get(row.currency, 1.0) for row in interets_rows)
        # Add investment dividends to interests total as well (always dividends, even if not filtered specifically)
        itx_div_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.type == "dividende",
            InvestmentTransaction.date < end
        )
        if start:
            itx_div_query = itx_div_query.filter(InvestmentTransaction.date >= start)
        if account_id:
            itx_div_query = itx_div_query.filter(InvestmentTransaction.account_id == account_id)

        itx_div_rows = itx_div_query.group_by(Account.currency).all()
        interets += sum(row[1] / rates.get(row[0], 1.0) for row in itx_div_rows)

        # Expenses grouped by account currency
        depenses_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer == False
        )
        if not account_id:
            # Global view: include both checking and savings accounts
            depenses_by_curr = depenses_by_curr.filter(Account.type.in_(["courant", "epargne"]))
            if tr_accounts:
                depenses_by_curr = depenses_by_curr.filter(Transaction.account_id.notin_(tr_accounts))
        else:
            depenses_by_curr = depenses_by_curr.filter(Transaction.account_id == account_id)

        if start:
            depenses_by_curr = depenses_by_curr.filter(Transaction.date >= start)
        depenses_by_curr = depenses_by_curr.filter(Transaction.date < end)

        depenses_rows = depenses_by_curr.group_by(Account.currency).all()
        depenses = sum(row.total / rates.get(row.currency, 1.0) for row in depenses_rows)

        # ADD: Investment withdrawals as expenses for individual account view
        if account_id:
            itx_exp_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
                InvestmentTransaction.account_id == account_id,
                InvestmentTransaction.type == "retrait",
                InvestmentTransaction.date < end
            )
            if start:
                itx_exp_query = itx_exp_query.filter(InvestmentTransaction.date >= start)

            itx_exp_rows = itx_exp_query.group_by(Account.currency).all()
            depenses += sum(row[1] / rates.get(row[0], 1.0) for row in itx_exp_rows)

        # Calculate "Investissements" (Internal savings transfers) separately
        # We include both "Investissement" and "Epargne" categories here as they are not "consumption"
        investments_by_curr = (
            db.query(
                Account.currency,
                func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
            )
            .join(Account, Transaction.account_id == Account.id)
            .join(Category, Transaction.category_id == Category.id)
            .filter(Transaction.type == "Sortie", Category.name.in_(["Investissement", "Epargne"]), Transaction.is_transfer == False)
        )
        if start:
            investments_by_curr = investments_by_curr.filter(Transaction.date >= start)
        investments_by_curr = investments_by_curr.filter(Transaction.date < end)
        if account_id:
            investments_by_curr = investments_by_curr.filter(Transaction.account_id == account_id)
        else:
            if tr_accounts:
                investments_by_curr = investments_by_curr.filter(Transaction.account_id.notin_(tr_accounts))

        investments_rows = investments_by_curr.group_by(Account.currency).all()
        investments = sum(row.total / rates.get(row.currency, 1.0) for row in investments_rows)

        # ADD: Investment versements as investments
        itx_inv_query = db.query(
            Account.currency,
            func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")
        ).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.type == "versement"
        )
        if start:
            itx_inv_query = itx_inv_query.filter(InvestmentTransaction.date >= start)
        itx_inv_query = itx_inv_query.filter(InvestmentTransaction.date < end)
        if account_id:
            itx_inv_query = itx_inv_query.filter(InvestmentTransaction.account_id == account_id)

        itx_inv_rows = itx_inv_query.group_by(Account.currency).all()
        investments += sum(row.total / rates.get(row.currency, 1.0) for row in itx_inv_rows)

        real_depenses = depenses - investments
        remaining = revenus - depenses

        # Savings rate = (Revenus - Real Expenses) / Revenus
        if revenus <= 0:
            savings_rate = 0.0
        else:
            savings_rate = ((revenus - real_depenses) / revenus * 100.0)
            savings_rate = max(min(savings_rate, 100.0), -100.0)

        if month and year:
            now = datetime.now()
            if now.year == year and now.month == month:
                days = now.day
            else:
                days = calendar.monthrange(year, month)[1]
        else:
            # For all-time, use days between earliest tx and end
            earliest = db.query(func.min(Transaction.date)).scalar()
            if earliest:
                delta = end - earliest
                days = max(delta.days, 1)
            else:
                days = 1

        burn_rate = real_depenses / max(days, 1)

        latest_snapshots_subquery = (
            db.query(
                BalanceSnapshot.account_id.label("account_id"),
                func.max(BalanceSnapshot.date).label("max_date"),
            )
            .filter(BalanceSnapshot.date <= end)
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

        # Patrimoine / Solde Actuel logic
        # 1. Investments
        if account_id:
            # For a single investment account, use raw value from snapshots
            inv_acc = db.query(Account).filter(Account.id == account_id).first()
            if inv_acc and inv_acc.type == "investissement":
                latest_snap = db.query(BalanceSnapshot).filter(
                    BalanceSnapshot.account_id == account_id,
                    BalanceSnapshot.date <= end
                ).order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()).first()
                
                if latest_snap:
                    investment_value = float(latest_snap.current_value)
                else:
                    # Fallback to Transaction table
                    last_tx = db.query(Transaction).filter(
                        Transaction.account_id == account_id,
                        Transaction.date <= end
                    ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
                    investment_value = float(last_tx.running_balance) if last_tx else 0.0
            else:
                investment_value = 0.0
        else:
            # Global view: sum snapshots for all investment accounts
            investment_accounts = db.query(Account).filter(Account.type == "investissement", Account.active == True).all()
            investment_value = 0.0
            
            # Get latest values from snapshots
            latest_values_rows = (
                db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
                .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
                .all()
            )
            latest_values = {row.account_id: float(row.current_value or 0.0) for row in latest_values_rows}
            
            for acc in investment_accounts:
                val = 0.0
                if acc.id in latest_values:
                    val = latest_values[acc.id]
                else:
                    # Fallback to Transaction table
                    last_tx = db.query(Transaction).filter(
                        Transaction.account_id == acc.id,
                        Transaction.date <= end
                    ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
                    if last_tx:
                        val = float(last_tx.running_balance)
                
                investment_value += val / rates.get(acc.currency, 1.0)

        # 2. Checking / Savings balances
        # We use a subquery to get the latest transaction (max date, then max ID) for each account
        account_last_tx = (
            db.query(
                Transaction.account_id.label("account_id"),
                func.max(Transaction.date).label("max_date"),
            )
            .filter(Transaction.date <= end)
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

        current_accounts_query = (
            db.query(Account.id, Account.type, Account.currency, func.coalesce(func.sum(Transaction.running_balance), 0.0).label("total"))
            .join(Account, Transaction.account_id == Account.id)
            .join(latest_tx_ids, Transaction.id == latest_tx_ids.c.max_id)
        )
        if account_id:
            current_accounts_query = current_accounts_query.filter(Account.id == account_id)
        else:
            current_accounts_query = current_accounts_query.filter(Account.active == True)
            if tr_accounts:
                current_accounts_query = current_accounts_query.filter(Transaction.account_id.notin_(tr_accounts))

        current_accounts_rows = current_accounts_query.group_by(Account.id, Account.type, Account.currency).all()

        # Aggregate balances by type for the response
        checking_bal = 0.0
        savings_bal_from_tx = 0.0
        for row in current_accounts_rows:
            # For specific account, we might want the raw value
            if account_id and row.id == account_id:
                val = row.total
            else:
                val = row.total / rates.get(row.currency, 1.0)
            
            if row.type == "courant":
                checking_bal += val
            elif row.type == "epargne":
                savings_bal_from_tx += val

        # For savings accounts, we prefer the Snapshot-based calculation if available
        # because it might include value updates not present in transactions.
        savings_account_ids = _savings_account_ids(db)
        if account_id:
            savings_account_ids = [account_id] if account_id in savings_account_ids else []

        savings_account_map = {
            acc.id: acc
            for acc in db.query(Account).filter(Account.id.in_(savings_account_ids)).all()
        } if savings_account_ids else {}

        events = _savings_events_by_account(db, savings_account_ids, end)
        savings_total = 0.0
        for acc_id, items in events.items():
            if items:
                acc = savings_account_map.get(acc_id)
                val = items[-1][2]
                if account_id and acc_id == account_id:
                    savings_total += val
                else:
                    savings_total += val / rates.get(acc.currency, 1.0) if acc else val

        # If we have savings accounts, use savings_total (snapshot-aware) instead of savings_bal_from_tx
        if not account_id:
            solde_actuel = checking_bal + savings_total + investment_value
        else:
            acc_obj = db.query(Account).filter(Account.id == account_id).first()
            if acc_obj.type == "investissement":
                solde_actuel = investment_value
            elif acc_obj.type == "epargne":
                solde_actuel = savings_total
            else:
                solde_actuel = checking_bal

        # Re-calculate revenus and depenses in account currency if account_id is provided
        if account_id:
            acc_obj = db.query(Account).filter(Account.id == account_id).first()
            if not acc_obj:
                raise HTTPException(status_code=404, detail="Account not found")

            # We need to re-query without currency conversion
            revenus_query = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                .filter(Transaction.account_id == account_id, Transaction.type.in_(["Entree", "Solde Initial"]), Transaction.is_transfer == False)
            )
            if start:
                revenus_query = revenus_query.filter(Transaction.date >= start)
            revenus_query = revenus_query.filter(Transaction.date < end)
            revenus = float(revenus_query.scalar() or 0.0)
            
            # Add investment transactions (versement is positive flow into account)
            itx_revenus_query = (
                db.query(func.coalesce(func.sum(InvestmentTransaction.amount), 0.0))
                .filter(InvestmentTransaction.account_id == account_id, InvestmentTransaction.type == "versement")
            )
            if start:
                itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.date >= start)
            itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.date < end)
            revenus += float(itx_revenus_query.scalar() or 0.0)
            
            depenses_query = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                .filter(Transaction.account_id == account_id, Transaction.type == "Sortie", Transaction.is_transfer == False)
            )
            if start:
                depenses_query = depenses_query.filter(Transaction.date >= start)
            depenses_query = depenses_query.filter(Transaction.date < end)
            depenses = float(depenses_query.scalar() or 0.0)
            
            itx_retrait_query = (
                db.query(func.coalesce(func.sum(InvestmentTransaction.amount), 0.0))
                .filter(InvestmentTransaction.account_id == account_id, InvestmentTransaction.type == "retrait")
            )
            if start:
                itx_retrait_query = itx_retrait_query.filter(InvestmentTransaction.date >= start)
            itx_retrait_query = itx_retrait_query.filter(InvestmentTransaction.date < end)
            depenses += float(itx_retrait_query.scalar() or 0.0)
            
            # Calculate investments for specific account
            inv_q = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                .join(Category, Transaction.category_id == Category.id)
                .filter(
                    Transaction.account_id == account_id, 
                    Transaction.type == "Sortie", 
                    Category.name.in_(["Investissement", "Epargne"]),
                    Transaction.is_transfer == False
                )
            )
            if start:
                inv_q = inv_q.filter(Transaction.date >= start)
            inv_q = inv_q.filter(Transaction.date < end)
            investments = float(inv_q.scalar() or 0.0)
            
            # Add investment transactions (versement)
            itx_inv_q = (
                db.query(func.coalesce(func.sum(InvestmentTransaction.amount), 0.0))
                .filter(InvestmentTransaction.account_id == account_id, InvestmentTransaction.type == "versement")
            )
            if start:
                itx_inv_q = itx_inv_q.filter(InvestmentTransaction.date >= start)
            itx_inv_q = itx_inv_q.filter(InvestmentTransaction.date < end)
            investments += float(itx_inv_q.scalar() or 0.0)

            remaining = revenus - depenses
            savings_rate = (remaining / revenus * 100.0) if revenus > 0 else 0.0
            real_depenses = depenses - investments
            
            # Robust calculation of days for burn_rate
            if start:
                days_count = (end - start).days
            else:
                earliest = db.query(func.min(Transaction.date)).filter(Transaction.account_id == account_id).scalar()
                if earliest:
                    days_count = max((end - earliest).days, 1)
                else:
                    days_count = 1
            
            burn_rate = real_depenses / days_count if days_count > 0 else 0.0
            interets = 0.0 # Simplified for single account view




        return {
            "month": month,
            "year": year,
            "base_currency": base_currency,
            "revenus_totaux": round(float(revenus), 2),
            "interets_totaux": round(float(interets), 2),
            "depenses_totales": round(float(depenses), 2),
            "depenses_reelles": round(float(real_depenses), 2),
            "investissements_du_mois": round(float(investments), 2),
            "revenus_apres_depenses": round(float(remaining), 2),
            "taux_epargne": round(float(savings_rate), 2),
            "burn_rate": round(float(burn_rate), 2),
            "patrimoine_net_total": round(float(checking_bal + savings_total + investment_value), 2),
            "epargne_total": round(float(savings_total), 2),
            "solde_actuel": round(float(solde_actuel), 2),
        }
    except Exception as e:
        print(f"ERROR in budget_analytics: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budget-alerts", response_model=list[BudgetAlert])
async def budget_alerts(
    year: int = Query(...),
    month: int = Query(...),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    categories = db.query(Category).filter(
        (Category.monthly_limit.isnot(None)) | (Category.annual_limit.isnot(None))
    ).all()

    if not categories:
        return []

    rates = await get_exchange_rates("EUR")
    tr_accounts = _get_ticket_restaurant_account_ids(db)
    start_month = datetime(year, month, 1)
    end_month = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    start_year = datetime(year, 1, 1)
    end_year = datetime(year + 1, 1, 1)

    # Monthly spending per category in EUR
    monthly_query = (
        db.query(Transaction.category_id, Account.currency, func.sum(Transaction.amount))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            Transaction.date >= start_month,
            Transaction.date < end_month,
        )
    )
    if account_id:
        monthly_query = monthly_query.filter(Transaction.account_id == account_id)
    else:
        if tr_accounts:
            monthly_query = monthly_query.filter(Transaction.account_id.notin_(tr_accounts))

    monthly_rows = monthly_query.group_by(Transaction.category_id, Account.currency).all()

    monthly_spent_map = {}
    for cat_id, curr, amount in monthly_rows:
        if cat_id not in monthly_spent_map:
            monthly_spent_map[cat_id] = 0.0
        monthly_spent_map[cat_id] += amount / rates.get(curr, 1.0)

    # Annual spending per category in EUR
    annual_query = (
        db.query(Transaction.category_id, Account.currency, func.sum(Transaction.amount))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            Transaction.date >= start_year,
            Transaction.date < end_year,
        )
    )
    if account_id:
        annual_query = annual_query.filter(Transaction.account_id == account_id)
    else:
        if tr_accounts:
            annual_query = annual_query.filter(Transaction.account_id.notin_(tr_accounts))

    annual_rows = annual_query.group_by(Transaction.category_id, Account.currency).all()    
    annual_spent_map = {}
    for cat_id, curr, amount in annual_rows:
        if cat_id not in annual_spent_map:
            annual_spent_map[cat_id] = 0.0
        annual_spent_map[cat_id] += amount / rates.get(curr, 1.0)

    # ADD: Investment versements into "Investissement" category for alerts
    inv_cat = db.query(Category).filter(Category.name == "Investissement").first()
    if inv_cat:
        # Monthly Investment Transactions
        itx_monthly_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.type == "versement",
            InvestmentTransaction.date >= start_month,
            InvestmentTransaction.date < end_month,
        )
        if account_id:
            itx_monthly_query = itx_monthly_query.filter(InvestmentTransaction.account_id == account_id)

        itx_monthly_rows = itx_monthly_query.group_by(Account.currency).all()
        for curr, amount in itx_monthly_rows:
            if inv_cat.id not in monthly_spent_map:
                monthly_spent_map[inv_cat.id] = 0.0
            monthly_spent_map[inv_cat.id] += amount / rates.get(curr, 1.0)

        # Annual Investment Transactions
        itx_annual_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.type == "versement",
            InvestmentTransaction.date >= start_year,
            InvestmentTransaction.date < end_year,
        )
        if account_id:
            itx_annual_query = itx_annual_query.filter(InvestmentTransaction.account_id == account_id)

        itx_annual_rows = itx_annual_query.group_by(Account.currency).all()
        for curr, amount in itx_annual_rows:
            if inv_cat.id not in annual_spent_map:
                annual_spent_map[inv_cat.id] = 0.0
            annual_spent_map[inv_cat.id] += amount / rates.get(curr, 1.0)

    results = []
    for cat in categories:
        monthly_spent = monthly_spent_map.get(cat.id, 0.0)
        annual_spent = annual_spent_map.get(cat.id, 0.0)

        monthly_ratio = (monthly_spent / cat.monthly_limit) if cat.monthly_limit else None
        annual_ratio = (annual_spent / cat.annual_limit) if cat.annual_limit else None

        results.append(BudgetAlert(
            category_id=cat.id,
            category_name=cat.name,
            category_icon=cat.icon,
            category_color=cat.color,
            monthly_limit=cat.monthly_limit,
            annual_limit=cat.annual_limit,
            monthly_spent=round(monthly_spent, 2),
            annual_spent=round(annual_spent, 2),
            monthly_ratio=monthly_ratio,
            annual_ratio=annual_ratio,
        ))

    # Sort by ratio (highest first)
    results.sort(key=lambda a: max(
        a.monthly_ratio or 0,
        a.annual_ratio or 0,
    ), reverse=True)

    return results


