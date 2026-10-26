import calendar
from datetime import datetime, timedelta
from typing import List

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


def get_recurring_occurrences(
    recurring_tx: any, 
    start_period: datetime, 
    end_period: datetime
) -> List[datetime]:
    """
    Returns a list of dates when a recurring transaction occurs within a period.
    Respects excluded_months (CSV string or list of month numbers 1-12).
    """
    occurrences = []
    current_date = recurring_tx.start_date
    
    # Ensure current_date is at the beginning of the day
    current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Monthly / quarterly: the first occurrence falls on day_of_month on or after start_date,
    # not on start_date itself (a rule created on the 8th for the 16th starts on the 16th).
    if recurring_tx.frequency in ("monthly", "quarterly") and recurring_tx.day_of_month:
        day = recurring_tx.day_of_month
        year, month = current_date.year, current_date.month
        if current_date.day > min(day, calendar.monthrange(year, month)[1]):
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        current_date = datetime(year, month, min(day, calendar.monthrange(year, month)[1]))

    # Parse excluded months (stored as CSV string "5,10" → {5, 10})
    excluded_months: set[int] = set()
    if hasattr(recurring_tx, 'excluded_months') and recurring_tx.excluded_months:
        if isinstance(recurring_tx.excluded_months, str):
            excluded_months = {int(m) for m in recurring_tx.excluded_months.split(",") if m.strip()}
        elif isinstance(recurring_tx.excluded_months, list):
            excluded_months = set(recurring_tx.excluded_months)

    # If end_date is set on the recurring tx, use the earliest of tx end_date or period end
    actual_end_period = end_period
    if recurring_tx.end_date and recurring_tx.end_date < end_period:
        actual_end_period = recurring_tx.end_date

    while current_date < actual_end_period:
        if current_date >= start_period and current_date.month not in excluded_months:
            occurrences.append(current_date)
        
        if recurring_tx.frequency == "daily":
            current_date += timedelta(days=1)
        elif recurring_tx.frequency == "weekly":
            current_date += timedelta(weeks=1)
        elif recurring_tx.frequency == "monthly":
            # Move to next month
            month = current_date.month
            year = current_date.year
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
            
            # Handle day of month
            day = recurring_tx.day_of_month or recurring_tx.start_date.day
            last_day_of_next_month = calendar.monthrange(year, month)[1]
            actual_day = min(day, last_day_of_next_month)
            current_date = datetime(year, month, actual_day)
        elif recurring_tx.frequency == "quarterly":
            for _ in range(3):
                month = current_date.month
                year = current_date.year
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
                current_date = datetime(year, month, 1) # Temporary
            
            day = recurring_tx.day_of_month or recurring_tx.start_date.day
            last_day_of_next_month = calendar.monthrange(current_date.year, current_date.month)[1]
            actual_day = min(day, last_day_of_next_month)
            current_date = datetime(current_date.year, current_date.month, actual_day)
        elif recurring_tx.frequency == "yearly":
            year = current_date.year + 1
            month = recurring_tx.start_date.month
            day = recurring_tx.start_date.day
            last_day_of_month = calendar.monthrange(year, month)[1]
            actual_day = min(day, last_day_of_month)
            current_date = datetime(year, month, actual_day)
        else:
            break # Unknown frequency
            
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
