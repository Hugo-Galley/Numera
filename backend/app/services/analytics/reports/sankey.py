"""Sankey du mois : revenus → budget → investissements, épargne et dépenses par catégorie."""
from sqlalchemy.orm import Session

from app.domain.reports import sankey_graph
from app.integrations.currency import get_exchange_rates
from app.repositories.analytics import reports as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.services.analytics.budget import compute_budget
from app.services.budget.budget_period import period_bounds


async def compute_sankey(db: Session, month: int, year: int, account_id: int | None = None) -> dict:
    start, end = period_bounds(db, year, month)
    rates = await get_exchange_rates("EUR")
    budget_data = await compute_budget(month=month, year=year, account_id=account_id, db=db)
    tr_accounts = set() if account_id else ticket_restaurant_account_ids(db)

    # Dépenses par catégorie (Investissement/Epargne à part : nœud des investissements)
    cat_expenses: dict = {}
    for row in repo.sankey_expense_rows(db, start, end, account_id, tr_accounts):
        cid = row.Category.id
        if cid not in cat_expenses:
            cat_expenses[cid] = {"obj": row.Category, "total": 0.0}
        cat_expenses[cid]["total"] += row.total / rates.get(row.currency, 1.0)

    income_sources, total_income = _income_sources(db, start, end, account_id, tr_accounts, rates)
    return sankey_graph(income_sources, total_income, budget_data["investissements_du_mois"], cat_expenses)


def _income_sources(db: Session, start, end, account_id: int | None, tr_accounts: set[int],
                    rates: dict) -> tuple[list[dict], float]:
    income_sources = []
    total_income = 0.0
    for row in repo.sankey_income_rows(db, start, end, account_id, tr_accounts):
        name = row.Category.name if row.Category else "Autres Revenus"
        color = row.Category.color if row.Category else "#10b981"
        val = row.total / rates.get(row.currency, 1.0)
        if val > 0:
            income_sources.append({"name": name, "total": val, "color": color})
            total_income += val
    div_total = 0.0
    for curr, amt in repo.dividend_rows(db, start, end, account_id):
        div_total += amt / rates.get(curr, 1.0)
    if div_total > 0:
        income_sources.append({"name": "Dividendes", "total": div_total, "color": "#10b981"})
        total_income += div_total
    return income_sources, total_income
