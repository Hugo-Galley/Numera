"""Bilan annuel « Wrapped » : agrège les chiffres officiels du budget sur une année civile.

Les totaux reprennent mois par mois `budget_analytics`, `expenses_by_category` et `top_merchants`,
pour rester identiques à ce qu'affichent le Dashboard et le rapport mensuel. L'année en cours est
arrêtée au mois courant, et la comparaison avec N-1 se fait sur la même période.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.currency import get_exchange_rates
from app.core.finance import is_lapsed
from app.core.work_time import load_work_time
from app.db.session import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.schemas.wrapped import (
    WrappedCategory,
    WrappedComparison,
    WrappedExpense,
    WrappedMerchant,
    WrappedMonth,
    WrappedReport,
    WrappedSubscription,
    WrappedTotals,
)

from app.core.budget_period import civil_months
from .budget import budget_analytics
from .metrics import expenses_by_category, top_merchants
from .utils import NET_AMOUNT, _get_ticket_restaurant_account_ids, opening_balances_eur

router = APIRouter()

# Épargne et investissement ne sont pas des « postes de dépense » : déjà hors dépenses réelles
NON_EXPENSE_CATEGORIES = ("Investissement", "Epargne", "Épargne")
MONTHLY_FACTOR = {"monthly": 1.0, "weekly": 52 / 12, "quarterly": 1 / 3, "yearly": 1 / 12, "annual": 1 / 12}


def _period(year: int, last_month: int) -> tuple[datetime, datetime]:
    end = datetime(year + 1, 1, 1) if last_month == 12 else datetime(year, last_month + 1, 1)
    return datetime(year, 1, 1), end


def _pct_change(current: float, previous: float) -> float | None:
    if abs(previous) < 0.005:
        return None
    return round((current - previous) / abs(previous) * 100.0, 1)


def _hours(amount: float, hourly_rate: float | None) -> float | None:
    return round(amount / hourly_rate, 1) if hourly_rate else None


def _expense_query(db: Session, start: datetime, end: datetime):
    """Sorties réelles du budget : hors virements internes et comptes tickets restaurant."""
    query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,  # noqa: E712
            Account.type.in_(["courant", "epargne"]),
        )
    )
    tr_accounts = _get_ticket_restaurant_account_ids(db)
    if tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    return query


def _subscription_query(db: Session):
    """Récurrences de dépense « abonnement » : ni virement, ni épargne/investissement."""
    return (
        db.query(RecurringTransaction)
        .outerjoin(Category, RecurringTransaction.category_id == Category.id)
        .filter(
            RecurringTransaction.type == "Sortie",
            RecurringTransaction.transfer_to_account_id.is_(None),
            func.coalesce(Category.name, "").notin_(NON_EXPENSE_CATEGORIES),
        )
    )


async def _totals(db: Session, year: int, last_month: int, rates: dict[str, float]) -> tuple[WrappedTotals, list[WrappedMonth]]:
    start, end = _period(year, last_month)
    months: list[WrappedMonth] = []
    invested = 0.0
    net_worth_end = 0.0
    for month in range(1, last_month + 1):
        budget = await budget_analytics(month=month, year=year, account_id=None, db=db)
        income, real = budget["revenus_totaux"], budget["depenses_reelles"]
        months.append(WrappedMonth(month=month, income=income, real_expenses=real, saved=round(income - real, 2)))
        invested += budget["investissements_du_mois"]
        net_worth_end = budget["patrimoine_net_total"]
    start_budget = await budget_analytics(month=12, year=year - 1, account_id=None, db=db)
    net_worth_start = start_budget["patrimoine_net_total"]

    income = sum(m.income for m in months)
    real_expenses = sum(m.real_expenses for m in months)
    saved = income - real_expenses
    savings_rate = max(min(saved / income * 100.0, 100.0), -100.0) if income > 0 else 0.0

    dividend_rows = (
        db.query(Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total"))
        .join(Account, InvestmentTransaction.account_id == Account.id)
        .filter(
            InvestmentTransaction.type == "dividende",
            InvestmentTransaction.date >= start,
            InvestmentTransaction.date < end,
        )
        .group_by(Account.currency)
        .all()
    )
    dividends = sum(row.total / rates.get(row.currency, 1.0) for row in dividend_rows)

    subscription_ids = [rd.id for rd in _subscription_query(db).all()]
    subscriptions_cost = 0.0
    if subscription_ids:
        sub_rows = (
            _expense_query(db, start, end)
            .filter(Transaction.recurring_transaction_id.in_(subscription_ids))
            .with_entities(Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0).label("total"))
            .group_by(Account.currency)
            .all()
        )
        subscriptions_cost = sum(row.total / rates.get(row.currency, 1.0) for row in sub_rows)

    expense_count = _expense_query(db, start, end).count()

    totals = WrappedTotals(
        income=round(income, 2),
        real_expenses=round(real_expenses, 2),
        saved=round(saved, 2),
        savings_rate=round(savings_rate, 1),
        invested=round(invested, 2),
        dividends=round(dividends, 2),
        net_worth_start=round(net_worth_start, 2),
        net_worth_end=round(net_worth_end, 2),
        # Les soldes initiaux des comptes ouverts dans l'année ne sont pas un gain
        net_worth_change=round(net_worth_end - net_worth_start - opening_balances_eur(db, start, end, rates), 2),
        subscriptions_cost=round(subscriptions_cost, 2),
        expense_count=expense_count,
    )
    return totals, months


async def _top_categories(db: Session, year: int, last_month: int, hourly_rate: float | None) -> list[WrappedCategory]:
    totals: dict[int, dict] = {}
    for month in range(1, last_month + 1):
        data = await expenses_by_category(month=month, year=year, account_id=None, db=db)
        for item in data["items"]:
            cat = item["category"]
            if cat["name"] in NON_EXPENSE_CATEGORIES:
                continue
            entry = totals.setdefault(cat["id"], {"cat": cat, "total": 0.0})
            entry["total"] += item["total"]
    grand_total = sum(e["total"] for e in totals.values())
    ranked = sorted(totals.values(), key=lambda e: e["total"], reverse=True)[:5]
    return [
        WrappedCategory(
            name=e["cat"]["name"],
            icon=e["cat"]["icon"],
            color=e["cat"]["color"],
            total=round(e["total"], 2),
            percentage=round(e["total"] / grand_total * 100.0, 1) if grand_total > 0 else 0.0,
            work_hours=_hours(e["total"], hourly_rate),
        )
        for e in ranked
    ]


async def _top_merchants(db: Session, year: int, last_month: int, hourly_rate: float | None) -> list[WrappedMerchant]:
    totals: dict[str, float] = {}
    for month in range(1, last_month + 1):
        data = await top_merchants(month=month, year=year, limit=50, account_id=None, db=db)
        for item in data["items"]:
            totals[item["merchant"]] = totals.get(item["merchant"], 0.0) + item["total"]
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return [WrappedMerchant(merchant=name, total=round(total, 2), work_hours=_hours(total, hourly_rate)) for name, total in ranked]


def _biggest_expense(
    db: Session, year: int, last_month: int, rates: dict[str, float], hourly_rate: float | None
) -> WrappedExpense | None:
    start, end = _period(year, last_month)
    candidates = (
        _expense_query(db, start, end)
        .filter(func.coalesce(Category.name, "").notin_(NON_EXPENSE_CATEGORIES))
        .with_entities(Transaction, Account.currency, Category.name.label("category_name"))
        .order_by(NET_AMOUNT.desc())
        .limit(20)
        .all()
    )
    best = None
    for row in candidates:
        tx = row.Transaction
        amount_eur = (tx.amount - (tx.reimbursement_offset or 0.0)) / rates.get(row.currency, 1.0)
        if best is None or amount_eur > best[0]:
            best = (amount_eur, tx, row.category_name)
    if best is None or best[0] <= 0:
        return None
    amount, tx, category = best
    return WrappedExpense(
        merchant=tx.merchant,
        amount=round(amount, 2),
        date=tx.date.date().isoformat(),
        category=category,
        work_hours=_hours(amount, hourly_rate),
    )


def _subscription_changes(
    db: Session, year: int, last_month: int, today: date
) -> tuple[list[WrappedSubscription], list[WrappedSubscription]]:
    """Nouveaux : première échéance réelle dans l'année. Arrêtés : dernière échéance dans l'année, récurrence close."""
    start, end = _period(year, last_month)
    recurrings = {rd.id: rd for rd in _subscription_query(db).all()}
    if not recurrings:
        return [], []
    bounds = (
        db.query(
            Transaction.recurring_transaction_id,
            func.min(Transaction.date).label("first"),
            func.max(Transaction.date).label("last"),
        )
        .filter(Transaction.recurring_transaction_id.in_(list(recurrings)))
        .group_by(Transaction.recurring_transaction_id)
        .all()
    )
    new: list[WrappedSubscription] = []
    stopped: list[WrappedSubscription] = []
    now = datetime.combine(today, datetime.min.time())
    for row in bounds:
        rd = recurrings[row.recurring_transaction_id]
        item = WrappedSubscription(
            name=rd.name, monthly_cost=round(float(rd.amount) * MONTHLY_FACTOR.get(rd.frequency, 1.0), 2)
        )
        if start <= row.first < end:
            new.append(item)
        closed = (
            not rd.is_active
            or (rd.end_date is not None and rd.end_date < now)
            # plus prélevé depuis deux périodes, jugé à la fin de la période analysée
            or is_lapsed(rd.frequency, row.last, min(end, now))
        )
        if closed and start <= row.last < end:
            stopped.append(item)
    new.sort(key=lambda s: s.monthly_cost, reverse=True)
    stopped.sort(key=lambda s: s.monthly_cost, reverse=True)
    return new, stopped


def _available_years(db: Session) -> list[int]:
    rows = (
        db.query(func.strftime("%Y", Transaction.date))
        .filter(Transaction.type != "Solde Initial")
        .distinct()
        .all()
    )
    return sorted((int(r[0]) for r in rows if r[0]), reverse=True)


@router.get("/wrapped", response_model=WrappedReport)
async def get_wrapped(
    year: int = Query(ge=2000, le=2200),
    db: Session = Depends(get_db),
) -> WrappedReport:
    # Le bilan annuel reste en année civile, même si le dashboard suit le mois de paie.
    with civil_months():
        return await _build_wrapped(year, db)


async def _build_wrapped(year: int, db: Session) -> WrappedReport:
    today = date.today()
    if year > today.year:
        raise HTTPException(status_code=400, detail="Le bilan d'une année future n'est pas disponible")
    is_partial = year == today.year
    last_month = today.month if is_partial else 12
    rates = await get_exchange_rates("EUR")
    hourly_rate = load_work_time(db).hourly_rate
    available_years = _available_years(db)

    totals, months = await _totals(db, year, last_month, rates)
    active_months = [m for m in months if m.income > 0 or m.real_expenses > 0]
    has_data = year in available_years and bool(active_months)

    previous = None
    if year - 1 in available_years:
        prev_totals, prev_months = await _totals(db, year - 1, last_month, rates)
    # Comparer à une année presque vide (suivi commencé en cours d'année) donne des « +124 000 % » :
    # il faut des dépenses sur au moins la moitié des mois comparés
    prev_active = [m for m in prev_months if m.real_expenses > 0] if year - 1 in available_years else []
    if prev_active and len(prev_active) * 2 >= max(len(active_months), 1):
        previous = WrappedComparison(
            year=year - 1,
            totals=prev_totals,
            income_change_pct=_pct_change(totals.income, prev_totals.income),
            real_expenses_change_pct=_pct_change(totals.real_expenses, prev_totals.real_expenses),
            savings_rate_change_pts=round(totals.savings_rate - prev_totals.savings_rate, 1),
            net_worth_change_diff=round(totals.net_worth_change - prev_totals.net_worth_change, 2),
            invested_change_pct=_pct_change(totals.invested, prev_totals.invested),
        )

    new_subs, stopped_subs = _subscription_changes(db, year, last_month, today)
    return WrappedReport(
        year=year,
        available_years=available_years,
        has_data=has_data,
        is_partial=is_partial,
        months_covered=last_month,
        totals=totals,
        months=months,
        most_expensive_month=max(active_months, key=lambda m: m.real_expenses) if active_months else None,
        thriftiest_month=min(active_months, key=lambda m: m.real_expenses) if len(active_months) > 1 else None,
        top_categories=await _top_categories(db, year, last_month, hourly_rate),
        top_merchants=await _top_merchants(db, year, last_month, hourly_rate),
        biggest_expense=_biggest_expense(db, year, last_month, rates, hourly_rate),
        hourly_rate=hourly_rate,
        real_expenses_work_hours=_hours(totals.real_expenses, hourly_rate),
        net_worth_change_pct=(
            round(totals.net_worth_change / totals.net_worth_start * 100.0, 1) if totals.net_worth_start > 0 else None
        ),
        new_subscriptions=new_subs,
        stopped_subscriptions=stopped_subs,
        stopped_subscriptions_yearly_saving=round(sum(s.monthly_cost for s in stopped_subs) * 12, 2),
        previous=previous,
    )
