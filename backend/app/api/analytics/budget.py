import calendar
from datetime import date, datetime, timedelta

from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.core import budget_period
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
from app.core.portfolio import positions_values_eur

INVESTMENT_ACCOUNT_TYPES = ("investissement", "assurance_vie")
from app.schemas.transaction import TransactionRead


logger = get_logger(__name__)

router = APIRouter()

from app.core.wealth import account_values, active_accounts
from .utils import (
    income_criterion,
    NET_AMOUNT,
    budget_versement_ids,
    _tx_sample,
    _tx_read,
    _savings_account_ids,
    _savings_events_by_account,
    _savings_total_at,
    _get_ticket_restaurant_account_ids,
)


@router.get("/budget")
async def budget_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if account_id is not None and db.get(Account, account_id) is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if bool(month) != bool(year):
        raise HTTPException(status_code=422, detail="month et year doivent être fournis ensemble")
    try:
        start = None
        end = datetime.now()
        base_currency = "EUR"
        rates = await get_exchange_rates(base_currency)
        
        if month and year:
            start, end = period_bounds(db, year, month)

        # Get ticket restaurant accounts to exclude from global views
        tr_accounts = _get_ticket_restaurant_account_ids(db)

        # Get income grouped by account currency
        # Solde Initial n'est jamais un revenu (base du solde), y compris sur « tout le temps »
        revenus_query_filter = ["Entree", "Interets"]

        revenus_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.type.in_(revenus_query_filter),
            Transaction.is_transfer == False
        )
        if not account_id:
            # Vue globale : revenu au sens de income_criterion (courant, ou catégorie « revenu » ailleurs)
            revenus_by_curr = revenus_by_curr.filter(
                Account.type.in_(["courant", "epargne"]), income_criterion(db)
            )
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
            func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
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
            func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
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
                func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total")
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
        else:
            itx_inv_query = itx_inv_query.filter(InvestmentTransaction.id.in_(budget_versement_ids(db)))

        # Les dépenses ne contiennent que les sorties catégorisées : on ne retranche
        # que celles-ci, jamais les versements (absents de `depenses`).
        categorized_investments = investments

        itx_inv_rows = itx_inv_query.group_by(Account.currency).all()
        investments += sum(row.total / rates.get(row.currency, 1.0) for row in itx_inv_rows)

        real_depenses = depenses - (investments if account_id else categorized_investments)
        remaining = revenus - depenses

        # Savings rate = (Revenus - Real Expenses) / Revenus
        if revenus <= 0:
            savings_rate = 0.0
        else:
            savings_rate = ((revenus - real_depenses) / revenus * 100.0)
            savings_rate = max(min(savings_rate, 100.0), -100.0)

        if month and year:
            now = datetime.now()
            days = max((min(end.date(), now.date() + timedelta(days=1)) - start.date()).days, 1)
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
        # 1. Investments (comptes titres et assurances-vie)
        # Période en cours : un compte valorisé par ses positions prend la même valeur que la page
        # Investissements ; un mois passé garde le dernier relevé à sa date.
        is_current_period = end.date() >= date.today()
        if account_id:
            # For a single investment account, use raw value from snapshots
            inv_acc = db.query(Account).filter(Account.id == account_id).first()
            positions_values = (
                await positions_values_eur(db, [inv_acc]) if inv_acc and is_current_period else {}
            )
            if inv_acc and inv_acc.type in INVESTMENT_ACCOUNT_TYPES:
                latest_snap = db.query(BalanceSnapshot).filter(
                    BalanceSnapshot.account_id == account_id,
                    BalanceSnapshot.date <= end
                ).order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()).first()

                if account_id in positions_values:
                    investment_value = positions_values[account_id] * rates.get(inv_acc.currency, 1.0)
                elif latest_snap:
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
            investment_accounts = db.query(Account).filter(Account.type.in_(INVESTMENT_ACCOUNT_TYPES), Account.active == True).all()
            positions_values = await positions_values_eur(db, investment_accounts) if is_current_period else {}
            investment_value = 0.0
            
            # Get latest values from snapshots
            latest_values_rows = (
                db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
                .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
                .all()
            )
            latest_values = {row.account_id: float(row.current_value or 0.0) for row in latest_values_rows}
            
            for acc in investment_accounts:
                if acc.id in positions_values:
                    investment_value += positions_values[acc.id]
                    continue
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

        # Vue globale : le patrimoine vient du calculateur unique (tous les comptes actifs, tous types)
        other_bal = 0.0
        global_values = None
        if not account_id:
            wealth_accounts = active_accounts(db)
            global_values = await account_values(db, wealth_accounts, end if not is_current_period else None)
            account_by_id = {a.id: a for a in wealth_accounts}
            investment_value = sum(
                v.value_eur for i, v in global_values.items() if account_by_id[i].type in INVESTMENT_ACCOUNT_TYPES
            )

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
            checking_bal = sum(v.value_eur for i, v in global_values.items() if account_by_id[i].type == "courant")
            savings_total = sum(v.value_eur for i, v in global_values.items() if account_by_id[i].type == "epargne")
            other_bal = sum(
                v.value_eur
                for i, v in global_values.items()
                if account_by_id[i].type not in ("courant", "epargne", *INVESTMENT_ACCOUNT_TYPES)
            )
            solde_actuel = checking_bal + savings_total + investment_value + other_bal
        else:
            acc_obj = db.query(Account).filter(Account.id == account_id).first()
            if acc_obj.type in INVESTMENT_ACCOUNT_TYPES:
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
                db.query(func.coalesce(func.sum(NET_AMOUNT), 0.0))
                .filter(Transaction.account_id == account_id, Transaction.type.in_(["Entree", "Interets"]), Transaction.is_transfer == False)
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
                db.query(func.coalesce(func.sum(NET_AMOUNT), 0.0))
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
                db.query(func.coalesce(func.sum(NET_AMOUNT), 0.0))
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
            # Compte titres : un versement est une entrée du compte, pas une dépense à retrancher
            real_depenses = depenses if acc_obj.type in INVESTMENT_ACCOUNT_TYPES else depenses - investments
            # Mêmes formules que la vue globale : taux plafonné, burn rate sur les jours écoulés
            savings_rate = max(min((revenus - real_depenses) / revenus * 100.0, 100.0), -100.0) if revenus > 0 else 0.0
            burn_rate = max(real_depenses, 0.0) / max(days, 1)

            interets_query = (
                db.query(func.coalesce(func.sum(NET_AMOUNT), 0.0))
                .filter(Transaction.account_id == account_id, Transaction.type == "Interets", Transaction.is_transfer == False)
            )
            if start:
                interets_query = interets_query.filter(Transaction.date >= start)
            interets = float(interets_query.filter(Transaction.date < end).scalar() or 0.0)




        saved = remaining if account_id else revenus - real_depenses
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
            # Vue globale : épargné = revenus − dépenses réelles (numérateur du taux d'épargne), dont
            # `reste_tresorerie` = ce qui reste une fois tous les investissements du mois sortis
            "epargne_realisee": round(float(saved), 2),
            "reste_tresorerie": round(float(saved - (0.0 if account_id else investments)), 2),
            "taux_epargne": round(float(savings_rate), 2),
            "burn_rate": round(float(burn_rate), 2),
            "patrimoine_net_total": round(float(checking_bal + savings_total + investment_value + other_bal), 2),
            "epargne_total": round(float(savings_total), 2),
            "solde_actuel": round(float(solde_actuel), 2),
        }
    except HTTPException:
        raise
    except Exception:
        # Détail volontairement absent de la réponse : il reste dans les logs
        logger.exception("Erreur dans budget_analytics")
        raise HTTPException(status_code=500, detail="Erreur interne lors du calcul du budget")


RESILIENCE_WINDOW_MONTHS = 6


async def compute_resilience(db: Session, year: int, month: int, window: int = RESILIENCE_WINDOW_MONTHS) -> dict:
    """Mois d'autonomie = épargne liquide ÷ dépenses réelles mensuelles moyennes.

    La moyenne porte sur les `window` derniers mois **complets** ayant des dépenses : le mois en
    cours (incomplet, parfois sans salaire) faussait l'indice quand il servait de référence.
    """
    today = date.today()
    index = year * 12 + (month - 1)
    if index >= today.year * 12 + (today.month - 1):
        index = today.year * 12 + (today.month - 1) - 1  # dernier mois complet

    expenses: list[float] = []
    for offset in range(window):
        y, m = divmod(index - offset, 12)
        real = (await budget_analytics(month=m + 1, year=y, account_id=None, db=db))["depenses_reelles"]
        if real > 0:
            expenses.append(real)

    liquid = (await budget_analytics(month=month, year=year, account_id=None, db=db))["epargne_total"]
    average = sum(expenses) / len(expenses) if expenses else 0.0
    return {
        "months": round(liquid / average, 1) if average > 0 else None,
        "liquid_savings": round(liquid, 2),
        "avg_monthly_real_expenses": round(average, 2),
        "months_used": len(expenses),
    }


@router.get("/resilience")
async def resilience(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    db: Session = Depends(get_db),
):
    return await compute_resilience(db, year, month)


@router.get("/budget-alerts", response_model=list[BudgetAlert])
async def budget_alerts(
    year: int = Query(..., ge=2000, le=2200),
    month: int = Query(..., ge=1, le=12),
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
    start_month, end_month = period_bounds(db, year, month)
    start_year = datetime(year, 1, 1)
    end_year = datetime(year + 1, 1, 1)

    # Monthly spending per category in EUR
    monthly_query = (
        db.query(Transaction.category_id, Account.currency, func.sum(NET_AMOUNT))
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
        db.query(Transaction.category_id, Account.currency, func.sum(NET_AMOUNT))
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
        else:
            itx_monthly_query = itx_monthly_query.filter(InvestmentTransaction.id.in_(budget_versement_ids(db)))

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
        else:
            itx_annual_query = itx_annual_query.filter(InvestmentTransaction.id.in_(budget_versement_ids(db)))

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




class BudgetPeriodModeUpdate(BaseModel):
    mode: Literal["civil", "salary"]


@router.get("/budget-period")
def get_budget_period(
    year: int | None = Query(default=None, ge=2000, le=2200),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Mois budgétaire en cours et fenêtre (début / fin incluse) du mois demandé."""
    current_year, current_month = budget_period.current_period(db)
    info = budget_period.describe(db, year or current_year, month or current_month)
    return {**info, "current": {"year": current_year, "month": current_month}}


@router.put("/budget-period")
def set_budget_period_mode(payload: BudgetPeriodModeUpdate, db: Session = Depends(get_db)):
    budget_period.set_mode(db, payload.mode)
    return get_budget_period(year=None, month=None, db=db)
