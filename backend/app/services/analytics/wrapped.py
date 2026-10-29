"""Bilan annuel « Wrapped » : agrège les chiffres officiels du budget sur une année civile.

Les totaux reprennent mois par mois `compute_budget`, `compute_expenses_by_category` et `compute_top_merchants`,
pour rester identiques à ce qu'affichent le Dashboard et le rapport mensuel. L'année en cours est
arrêtée au mois courant, et la comparaison avec N-1 se fait sur la même période.
"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.errors import InvalidOperationError
from app.domain.budget import to_eur
from app.domain.finance import is_lapsed
from app.domain.wrapped import MONTHLY_FACTOR, NON_EXPENSE_CATEGORIES, hours, pct_change, period
from app.integrations.currency import get_exchange_rates
from app.repositories.analytics import wrapped as repo
from app.repositories.analytics.common import opening_balances_eur, ticket_restaurant_account_ids
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
from app.services.analytics.budget import compute_budget
from app.services.analytics.metrics import compute_expenses_by_category, compute_top_merchants
from app.services.budget.budget_period import civil_months
from app.services.budget.work_time import load_work_time


async def compute_wrapped(db: Session, year: int) -> WrappedReport:
    # Le bilan annuel reste en année civile, même si le dashboard suit le mois de paie.
    with civil_months():
        return await _build_wrapped(year, db)


async def _build_wrapped(year: int, db: Session) -> WrappedReport:
    today = date.today()
    if year > today.year:
        raise InvalidOperationError("Le bilan d'une année future n'est pas disponible")
    is_partial = year == today.year
    last_month = today.month if is_partial else 12
    rates = await get_exchange_rates("EUR")
    hourly_rate = load_work_time(db).hourly_rate
    available_years = repo.available_years(db)

    totals, months = await _totals(db, year, last_month, rates)
    active_months = [m for m in months if m.income > 0 or m.real_expenses > 0]
    previous = await _previous_year(db, year, last_month, rates, totals, active_months, available_years)
    new_subs, stopped_subs = _subscription_changes(db, year, last_month, today)
    return WrappedReport(
        year=year,
        available_years=available_years,
        has_data=year in available_years and bool(active_months),
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
        real_expenses_work_hours=hours(totals.real_expenses, hourly_rate),
        net_worth_change_pct=(
            round(totals.net_worth_change / totals.net_worth_start * 100.0, 1) if totals.net_worth_start > 0 else None
        ),
        new_subscriptions=new_subs,
        stopped_subscriptions=stopped_subs,
        stopped_subscriptions_yearly_saving=round(sum(s.monthly_cost for s in stopped_subs) * 12, 2),
        previous=previous,
    )


async def _previous_year(db: Session, year: int, last_month: int, rates: dict, totals: WrappedTotals,
                         active_months: list[WrappedMonth], available_years: list[int]) -> WrappedComparison | None:
    """Comparaison avec N-1 sur la même période, si N-1 a des dépenses sur au moins la moitié des mois comparés
    (une année presque vide, suivi commencé en cours d'année, donnerait des « +124 000 % »)."""
    if year - 1 not in available_years:
        return None
    prev_totals, prev_months = await _totals(db, year - 1, last_month, rates)
    prev_active = [m for m in prev_months if m.real_expenses > 0]
    if not (prev_active and len(prev_active) * 2 >= max(len(active_months), 1)):
        return None
    return WrappedComparison(
        year=year - 1,
        totals=prev_totals,
        income_change_pct=pct_change(totals.income, prev_totals.income),
        real_expenses_change_pct=pct_change(totals.real_expenses, prev_totals.real_expenses),
        savings_rate_change_pts=round(totals.savings_rate - prev_totals.savings_rate, 1),
        net_worth_change_diff=round(totals.net_worth_change - prev_totals.net_worth_change, 2),
        invested_change_pct=pct_change(totals.invested, prev_totals.invested),
    )


async def _totals(db: Session, year: int, last_month: int, rates: dict[str, float]) -> tuple[WrappedTotals, list[WrappedMonth]]:
    start, end = period(year, last_month)
    months: list[WrappedMonth] = []
    invested = 0.0
    net_worth_end = 0.0
    for month in range(1, last_month + 1):
        budget = await compute_budget(month=month, year=year, account_id=None, db=db)
        income, real = budget["revenus_totaux"], budget["depenses_reelles"]
        months.append(WrappedMonth(month=month, income=income, real_expenses=real, saved=round(income - real, 2)))
        invested += budget["investissements_du_mois"]
        net_worth_end = budget["patrimoine_net_total"]
    net_worth_start = (await compute_budget(month=12, year=year - 1, account_id=None, db=db))["patrimoine_net_total"]

    income = sum(m.income for m in months)
    real_expenses = sum(m.real_expenses for m in months)
    saved = income - real_expenses
    savings_rate = max(min(saved / income * 100.0, 100.0), -100.0) if income > 0 else 0.0
    dividends = to_eur(repo.dividend_rows(db, start, end), rates)

    tr_accounts = ticket_restaurant_account_ids(db)
    subscription_ids = [rd.id for rd in repo.subscription_recurrings(db)]
    subscriptions_cost = 0.0
    if subscription_ids:
        subscriptions_cost = to_eur(repo.subscription_expense_rows(db, start, end, tr_accounts, subscription_ids), rates)

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
        expense_count=repo.expense_count(db, start, end, tr_accounts),
    )
    return totals, months


async def _top_categories(db: Session, year: int, last_month: int, hourly_rate: float | None) -> list[WrappedCategory]:
    totals: dict[int, dict] = {}
    for month in range(1, last_month + 1):
        data = await compute_expenses_by_category(month=month, year=year, account_id=None, db=db)
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
            work_hours=hours(e["total"], hourly_rate),
        )
        for e in ranked
    ]


async def _top_merchants(db: Session, year: int, last_month: int, hourly_rate: float | None) -> list[WrappedMerchant]:
    totals: dict[str, float] = {}
    for month in range(1, last_month + 1):
        data = await compute_top_merchants(month=month, year=year, limit=50, account_id=None, db=db)
        for item in data["items"]:
            totals[item["merchant"]] = totals.get(item["merchant"], 0.0) + item["total"]
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return [WrappedMerchant(merchant=name, total=round(total, 2), work_hours=hours(total, hourly_rate)) for name, total in ranked]


def _biggest_expense(
    db: Session, year: int, last_month: int, rates: dict[str, float], hourly_rate: float | None
) -> WrappedExpense | None:
    start, end = period(year, last_month)
    best = None
    for row in repo.biggest_expense_candidates(db, start, end, ticket_restaurant_account_ids(db)):
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
        work_hours=hours(amount, hourly_rate),
    )


def _subscription_changes(
    db: Session, year: int, last_month: int, today: date
) -> tuple[list[WrappedSubscription], list[WrappedSubscription]]:
    """Nouveaux : première échéance réelle dans l'année. Arrêtés : dernière échéance dans l'année, récurrence close."""
    start, end = period(year, last_month)
    recurrings = {rd.id: rd for rd in repo.subscription_recurrings(db)}
    if not recurrings:
        return [], []
    new: list[WrappedSubscription] = []
    stopped: list[WrappedSubscription] = []
    now = datetime.combine(today, datetime.min.time())
    for row in repo.recurring_bounds(db, list(recurrings)):
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
