"""Rapport mensuel : budget du mois comparé au précédent, top catégories et marchands, money-flow, insights."""
from sqlalchemy.orm import Session

from app.domain.reports import calc_diff
from app.integrations.currency import get_exchange_rates
from app.repositories.analytics.common import opening_balances_eur
from app.schemas.insight import MonthlyComparison, MonthlyReport
from app.services.analytics.budget import compute_budget
from app.services.analytics.insights import compute_insights
from app.services.analytics.metrics import compute_expenses_by_category, compute_top_merchants
from app.services.analytics.reports.money_flow import compute_money_flow
from app.services.budget.budget_period import period_bounds
from app.services.budget.month_review import exceptional_expenses, month_bounds, savings_basis, without_exceptional


async def compute_monthly_report(db: Session, month: int, year: int, account_id: int | None = None) -> MonthlyReport:
    current_budget = await compute_budget(month=month, year=year, account_id=account_id, db=db)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_budget = await compute_budget(month=prev_month, year=prev_year, account_id=account_id, db=db)
    insights_data = await compute_insights(db, month, year, account_id)

    top_categories = await _top_categories(db, month, year, prev_month, prev_year, account_id)
    merch_data = await compute_top_merchants(month=month, year=year, limit=5, account_id=account_id, db=db)

    account_scope = account_id is not None
    current_savings = savings_basis(current_budget, account_scope)
    comparison = _comparison(current_budget, prev_budget, current_savings, savings_basis(prev_budget, account_scope))
    nw_change = await _net_worth_change(db, month, year, account_id, current_budget, prev_budget)
    flow_data = await compute_money_flow(month=month, year=year, account_id=account_id, db=db)

    start, end = month_bounds(db, year, month)
    rates = await get_exchange_rates("EUR")
    excl = without_exceptional(
        current_budget,
        exceptional_expenses(db, start, end, rates, account_id),
        account_scope=account_scope,
    )
    return MonthlyReport(
        month=month,
        year=year,
        income=current_budget["revenus_totaux"],
        expenses=current_budget["depenses_totales"],
        real_expenses=current_budget["depenses_reelles"],
        savings=round(current_savings, 2),
        savings_rate=current_budget["taux_epargne"],
        burn_rate=current_budget["burn_rate"],
        net_worth=current_budget["patrimoine_net_total"],
        net_worth_change=round(nw_change, 2),
        top_categories=top_categories,
        top_merchants=merch_data["items"],
        comparison=comparison,
        insights=insights_data.insights,
        health_score=insights_data.health_score,
        money_flow=flow_data,
        **excl,
    )


async def _top_categories(db: Session, month: int, year: int, prev_month: int, prev_year: int,
                          account_id: int | None) -> list[dict]:
    """Huit premiers postes de consommation (hors Investissement / Epargne, comme dans le bilan annuel)."""
    cat_data = await compute_expenses_by_category(month=month, year=year, account_id=account_id, db=db)
    prev_cat_data = await compute_expenses_by_category(month=prev_month, year=prev_year, account_id=account_id, db=db)
    prev_cat_totals = {item["category"]["id"]: item["total"] for item in prev_cat_data["items"]}
    sorted_items = sorted(
        (i for i in cat_data["items"] if i["category"]["name"] not in ("Investissement", "Epargne")),
        key=lambda x: x["total"],
        reverse=True,
    )
    return [{
        "id": item["category"]["id"],
        "name": item["category"]["name"],
        "total": item["total"],
        "icon": item["category"]["icon"],
        "color": item["category"]["color"],
        "prev_total": round(prev_cat_totals.get(item["category"]["id"], 0.0), 2),
    } for item in sorted_items[:8]]


def _comparison(current: dict, prev: dict, current_savings: float, prev_savings: float) -> MonthlyComparison:
    inc_diff, inc_pct = calc_diff(current["revenus_totaux"], prev["revenus_totaux"])
    exp_diff, exp_pct = calc_diff(current["depenses_reelles"], prev["depenses_reelles"])
    sav_diff, sav_pct = calc_diff(current_savings, prev_savings)
    return MonthlyComparison(
        income_diff=round(inc_diff, 2),
        income_diff_pct=round(inc_pct, 1),
        expenses_diff=round(exp_diff, 2),
        expenses_diff_pct=round(exp_pct, 1),
        savings_diff=round(sav_diff, 2),
        savings_diff_pct=round(sav_pct, 1)
    )


async def _net_worth_change(db: Session, month: int, year: int, account_id: int | None, current: dict,
                            prev: dict) -> float:
    nw_change = current["patrimoine_net_total"] - prev["patrimoine_net_total"]
    if account_id is None:
        # Un compte ouvert dans le mois n'est pas un gain : son solde initial est retranché
        period_start, period_end = period_bounds(db, year, month)
        nw_change -= opening_balances_eur(db, period_start, period_end, await get_exchange_rates("EUR"))
    return nw_change
