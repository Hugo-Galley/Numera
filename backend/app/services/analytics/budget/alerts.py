"""Alertes de plafonds : consommation mensuelle et annuelle des catégories plafonnées."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.budget import budget_alert, sort_alerts, spending_by_category
from app.integrations.currency import get_exchange_rates
from app.repositories.analytics import budget as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.schemas.category import BudgetAlert
from app.services.budget_period import period_bounds


async def compute_budget_alerts(db: Session, year: int, month: int, account_id: int | None = None) -> list[BudgetAlert]:
    categories = repo.capped_categories(db)
    if not categories:
        return []

    rates = await get_exchange_rates("EUR")
    tr_accounts = ticket_restaurant_account_ids(db)
    start_month, end_month = period_bounds(db, year, month)
    start_year, end_year = datetime(year, 1, 1), datetime(year + 1, 1, 1)

    # Dépenses par catégorie en EUR (dépenses découpées : une ligne par part)
    monthly = spending_by_category(repo.category_spending_rows(db, start_month, end_month, account_id, tr_accounts), rates)
    annual = spending_by_category(repo.category_spending_rows(db, start_year, end_year, account_id, tr_accounts), rates)

    # Les versements comptent dans la catégorie « Investissement »
    inv_cat = repo.investment_category(db)
    if inv_cat:
        for (start, end), totals in (((start_month, end_month), monthly), ((start_year, end_year), annual)):
            rows = repo.budget_versements_by_currency(db, start, end, account_id)
            spending_by_category(((inv_cat.id, currency, amount) for currency, amount in rows), rates, totals)

    return sort_alerts([
        budget_alert(cat, monthly.get(cat.id, 0.0), annual.get(cat.id, 0.0)) for cat in categories
    ])
