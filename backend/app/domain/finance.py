import calendar
from datetime import datetime, timedelta
from typing import Any, List

FRENCH_MONTHS = {
    1: "Janvier",
    2: "Fevrier",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Aout",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Decembre",
}


def month_label_from_date(value: datetime) -> str:
    return FRENCH_MONTHS[value.month]


def normalize_transaction_type(raw_type: str) -> str:
    normalized = raw_type.strip().lower()
    if normalized in {"entree", "entré", "entrée", "entre", "in", "credit"}:
        return "Entree"
    if normalized in {"sortie", "out", "debit", "débit"}:
        return "Sortie"
    if normalized in {"type", "solde initial", "solde_initial"}:
        return "Solde Initial"
    if normalized in {"interets", "intérêts", "interet", "intérêt", "interests"}:
        return "Interets"
    raise ValueError(f"Unsupported transaction type: {raw_type}")


def apply_transaction_to_balance(current_balance: float, transaction_type: str, amount: float) -> float:
    if transaction_type in {"Entree", "Solde Initial", "Interets"}:
        return amount if transaction_type == "Solde Initial" else current_balance + amount
    if transaction_type == "Sortie":
        return current_balance - amount
    raise ValueError(f"Unsupported transaction type: {transaction_type}")


def _first_occurrence(recurring_tx: Any) -> datetime:
    """Premier passage : la date de début (à minuit), ou pour une règle mensuelle/trimestrielle à jour
    fixe, ce jour-là à partir de la date de début (une règle créée le 8 pour le 16 démarre le 16)."""
    current_date = recurring_tx.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if recurring_tx.frequency in ("monthly", "quarterly") and recurring_tx.day_of_month:
        day = recurring_tx.day_of_month
        year, month = current_date.year, current_date.month
        if current_date.day > min(day, calendar.monthrange(year, month)[1]):
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        current_date = datetime(year, month, min(day, calendar.monthrange(year, month)[1]))
    return current_date


def _excluded_months(recurring_tx: Any) -> set[int]:
    """Mois exclus, stockés en CSV (« 5,10 » → {5, 10}) ou en liste."""
    excluded = getattr(recurring_tx, "excluded_months", None)
    if isinstance(excluded, str) and excluded:
        return {int(m) for m in excluded.split(",") if m.strip()}
    if isinstance(excluded, list):
        return set(excluded)
    return set()


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _next_occurrence(recurring_tx: Any, current_date: datetime) -> datetime | None:
    """Passage suivant selon la fréquence ; None pour une fréquence inconnue."""
    frequency = recurring_tx.frequency
    if frequency == "daily":
        return current_date + timedelta(days=1)
    if frequency == "weekly":
        return current_date + timedelta(weeks=1)
    if frequency in ("monthly", "quarterly"):
        year, month = current_date.year, current_date.month
        for _ in range(1 if frequency == "monthly" else 3):
            year, month = _next_month(year, month)
        day = recurring_tx.day_of_month or recurring_tx.start_date.day
        return datetime(year, month, min(day, calendar.monthrange(year, month)[1]))
    if frequency == "yearly":
        year, month, day = current_date.year + 1, recurring_tx.start_date.month, recurring_tx.start_date.day
        return datetime(year, month, min(day, calendar.monthrange(year, month)[1]))
    return None


def get_recurring_occurrences(recurring_tx: Any, start_period: datetime, end_period: datetime) -> List[datetime]:
    """
    Returns a list of dates when a recurring transaction occurs within a period.
    Respects excluded_months (CSV string or list of month numbers 1-12).
    """
    excluded_months = _excluded_months(recurring_tx)
    # If end_date is set on the recurring tx, use the earliest of tx end_date or period end
    actual_end_period = end_period
    if recurring_tx.end_date and recurring_tx.end_date < end_period:
        actual_end_period = recurring_tx.end_date

    occurrences = []
    current_date = _first_occurrence(recurring_tx)
    while current_date is not None and current_date < actual_end_period:
        if current_date >= start_period and current_date.month not in excluded_months:
            occurrences.append(current_date)
        current_date = _next_occurrence(recurring_tx, current_date)
    return occurrences


# Durée d'une période par fréquence, en jours (borne haute)
PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 31, "quarterly": 92, "yearly": 366, "annual": 366}


def is_lapsed(frequency: str, last_occurrence, today) -> bool:
    """Récurrence active mais plus prélevée : aucune occurrence depuis plus de deux périodes (+ 7 jours de marge).

    Sans aucune occurrence rattachée, on ne conclut rien (récurrence jamais liée, ou toute nouvelle).
    """
    if last_occurrence is None:
        return False
    days = PERIOD_DAYS.get(frequency, 31)
    last_day = last_occurrence.date() if hasattr(last_occurrence, "date") else last_occurrence
    today_day = today.date() if hasattr(today, "date") else today
    return (today_day - last_day).days > 2 * days + 7
