"""Calculs purs du bilan annuel."""
from datetime import datetime

# Épargne et investissement ne sont pas des « postes de dépense » : déjà hors dépenses réelles
NON_EXPENSE_CATEGORIES = ("Investissement", "Epargne", "Épargne")
MONTHLY_FACTOR = {"monthly": 1.0, "weekly": 52 / 12, "quarterly": 1 / 3, "yearly": 1 / 12, "annual": 1 / 12}


def period(year: int, last_month: int) -> tuple[datetime, datetime]:
    """Du 1er janvier à la fin du mois `last_month` (exclue)."""
    end = datetime(year + 1, 1, 1) if last_month == 12 else datetime(year, last_month + 1, 1)
    return datetime(year, 1, 1), end


def pct_change(current: float, previous: float) -> float | None:
    """Variation en % (None si la référence est nulle)."""
    if abs(previous) < 0.005:
        return None
    return round((current - previous) / abs(previous) * 100.0, 1)


def hours(amount: float, hourly_rate: float | None) -> float | None:
    """Montant en heures de travail (None sans taux horaire)."""
    return round(amount / hourly_rate, 1) if hourly_rate else None
