"""Répartition des dépenses par catégorie et top marchands du mois."""
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.integrations.currency import get_exchange_rates
from app.repositories.analytics import budget as budget_repo
from app.repositories.analytics import metrics as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.services.budget_period import period_bounds

UNCATEGORIZED = SimpleNamespace(
    id=None, name="Sans catégorie", icon=None, color="#94a3b8", monthly_limit=None, annual_limit=None
)


async def compute_expenses_by_category(db: Session, month: int, year: int, account_id: int | None = None) -> dict:
    start, end = period_bounds(db, year, month)
    rates = await get_exchange_rates("EUR")
    tr_accounts = set() if account_id else ticket_restaurant_account_ids(db)

    # Agrégat par catégorie après conversion ; les dépenses sans catégorie forment un bloc à part
    category_totals: dict = {}
    for row in repo.category_expense_rows(db, start, end, account_id, tr_accounts):
        category = row.Category or UNCATEGORIZED
        if category.id not in category_totals:
            category_totals[category.id] = {"category": category, "total_eur": 0.0}
        category_totals[category.id]["total_eur"] += row.total / rates.get(row.currency, 1.0)
    total_amount_eur = sum(item["total_eur"] for item in category_totals.values())

    # Versements : catégorie virtuelle « Investissement »
    itx_rows = budget_repo.budget_versements_by_currency(db, start, end, account_id)
    if itx_rows:
        inv_cat = budget_repo.investment_category(db)
        if inv_cat:
            if inv_cat.id not in category_totals:
                category_totals[inv_cat.id] = {"category": inv_cat, "total_eur": 0.0}
            for row in itx_rows:
                category_totals[inv_cat.id]["total_eur"] += row.total / rates.get(row.currency, 1.0)
            total_amount_eur = sum(item["total_eur"] for item in category_totals.values())

    return {
        "month": month,
        "year": year,
        "total": round(total_amount_eur, 2),
        "items": [_category_item(item, total_amount_eur)
                  for item in sorted(category_totals.values(), key=lambda x: x["total_eur"], reverse=True)],
    }


def _category_item(item: dict, total_amount_eur: float) -> dict:
    amount = item["total_eur"]
    pct = (amount / total_amount_eur * 100.0) if total_amount_eur > 0 else 0.0
    cat = item["category"]
    return {
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


async def compute_top_merchants(db: Session, month: int, year: int, limit: int = 5,
                                account_id: int | None = None) -> dict:
    start, end = period_bounds(db, year, month)
    rates = await get_exchange_rates("EUR")
    tr_accounts = set() if account_id else ticket_restaurant_account_ids(db)

    merchant_totals: dict = {}
    for row in repo.merchant_expense_rows(db, start, end, account_id, tr_accounts):
        if row.merchant not in merchant_totals:
            merchant_totals[row.merchant] = 0.0
        merchant_totals[row.merchant] += row.total / rates.get(row.currency, 1.0)

    sorted_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:limit]
    items = [{"merchant": name, "total": round(float(total), 2)} for name, total in sorted_merchants]
    return {"month": month, "year": year, "items": items}
