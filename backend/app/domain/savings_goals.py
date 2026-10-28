"""Progression d'un objectif d'épargne : calculs purs."""
from datetime import date

DAYS_PER_MONTH = 30.44
CREDIT_TYPES = ("Entree", "Interets", "Solde Initial")


def signed_total_eur(rows: list[tuple[str, float, str]], rates: dict[str, float]) -> float:
    """Somme en EUR de (type, montant, devise) : les entrées ajoutent, le reste retranche."""
    total = 0.0
    for type_, amount, currency in rows:
        value = amount / rates.get(currency, 1.0)
        total += value if type_ in CREDIT_TYPES else -value
    return total


def percentage(current_amount: float, target_amount: float) -> float:
    return (current_amount / target_amount * 100.0) if target_amount > 0 else 0.0


def goal_status(current_amount: float, target_amount: float, deadline: date | None,
                today: date) -> tuple[int | None, float | None, str]:
    """(jours restants, effort mensuel requis, statut) d'un objectif."""
    days_remaining = None
    monthly_required = None
    status = "on_track"
    if deadline:
        days_remaining = (deadline - today).days
        if days_remaining > 0:
            months_rem = days_remaining / DAYS_PER_MONTH
            remaining_amount = max(0, target_amount - current_amount)
            monthly_required = remaining_amount / months_rem if months_rem > 0 else remaining_amount
        elif current_amount < target_amount:
            status = "behind"
    if current_amount >= target_amount:
        status = "completed"
    elif percentage(current_amount, target_amount) > 80:
        status = "ahead"
    return days_remaining, monthly_required, status
