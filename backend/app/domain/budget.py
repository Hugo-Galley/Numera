"""Formules du budget (sans base) : conversion EUR, taux d'épargne, jours écoulés, alertes de plafond."""
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from typing import Any

from app.schemas.category import BudgetAlert


def to_eur(rows_by_currency: Mapping[str, float] | Iterable[tuple[str, float]], rates: dict[str, float]) -> float:
    """Somme de montants par devise convertis en EUR (devise sans taux : comptée au pair)."""
    pairs = rows_by_currency.items() if isinstance(rows_by_currency, Mapping) else rows_by_currency
    return sum(total / rates.get(currency, 1.0) for currency, total in pairs)


def savings_rate(revenus: float, depenses_reelles: float) -> float:
    """Taux d'épargne en %, plafonné à ±100 ; 0 sans revenu."""
    if revenus <= 0:
        return 0.0
    return max(min((revenus - depenses_reelles) / revenus * 100.0, 100.0), -100.0)


def elapsed_days(start: datetime, end: datetime, now: datetime) -> int:
    """Jours écoulés d'une période, arrêtés à demain pour la période en cours (au moins 1)."""
    return max((min(end.date(), now.date() + timedelta(days=1)) - start.date()).days, 1)


def spending_by_category(rows: Iterable[tuple[Any, str, float]], rates: dict[str, float],
                         totals: dict | None = None) -> dict:
    """Cumule des lignes (catégorie, devise, montant) en EUR par catégorie."""
    totals = {} if totals is None else totals
    for cat_id, currency, amount in rows:
        if cat_id not in totals:
            totals[cat_id] = 0.0
        totals[cat_id] += amount / rates.get(currency, 1.0)
    return totals


def budget_alert(category: Any, monthly_spent: float, annual_spent: float) -> BudgetAlert:
    """Consommation d'une catégorie plafonnée (ratio None sans plafond)."""
    return BudgetAlert(
        category_id=category.id,
        category_name=category.name,
        category_icon=category.icon,
        category_color=category.color,
        monthly_limit=category.monthly_limit,
        annual_limit=category.annual_limit,
        monthly_spent=round(monthly_spent, 2),
        annual_spent=round(annual_spent, 2),
        monthly_ratio=(monthly_spent / category.monthly_limit) if category.monthly_limit else None,
        annual_ratio=(annual_spent / category.annual_limit) if category.annual_limit else None,
    )


def sort_alerts(alerts: list[BudgetAlert]) -> list[BudgetAlert]:
    """Alertes triées par ratio le plus élevé (mensuel ou annuel) d'abord, tri stable."""
    alerts.sort(key=lambda a: max(a.monthly_ratio or 0, a.annual_ratio or 0), reverse=True)
    return alerts
