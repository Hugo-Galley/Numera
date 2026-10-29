"""Résilience : mois d'autonomie couverts par l'épargne liquide."""
from datetime import date

from sqlalchemy.orm import Session

from app.services.analytics.budget.summary import compute_budget

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
        real = (await compute_budget(month=m + 1, year=y, account_id=None, db=db))["depenses_reelles"]
        if real > 0:
            expenses.append(real)

    liquid = (await compute_budget(month=month, year=year, account_id=None, db=db))["epargne_total"]
    average = sum(expenses) / len(expenses) if expenses else 0.0
    return {
        "months": round(liquid / average, 1) if average > 0 else None,
        "liquid_savings": round(liquid, 2),
        "avg_monthly_real_expenses": round(average, 2),
        "months_used": len(expenses),
    }
