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
    """
    occurrences = []
    current_date = recurring_tx.start_date
    
    # Ensure current_date is at the beginning of the day
    current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # If end_date is set on the recurring tx, use the earliest of tx end_date or period end
    actual_end_period = end_period
    if recurring_tx.end_date and recurring_tx.end_date < end_period:
        actual_end_period = recurring_tx.end_date

    while current_date < actual_end_period:
        if current_date >= start_period:
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
