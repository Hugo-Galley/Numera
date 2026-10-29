"""Flux net du mois (de paie) courant et du précédent d'un compte, et dépense moyenne."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.domain.metrics import net_flow, variation_pct
from app.repositories.analytics import metrics as repo
from app.services.budget_period import current_period, period_bounds


def compute_account_flow_summary(db: Session, account_id: int, start_date: datetime | None = None,
                                 end_date: datetime | None = None) -> dict:
    """Calculé sur tout l'historique du compte (pas sur la page chargée par le frontend),
    virements internes exclus, Solde Initial exclu. Montants dans la devise du compte.
    """
    account = repo.get_account(db, account_id)
    if not account:
        raise NotFoundError("Account not found")

    year, month = current_period(db)
    month_start, next_start = period_bounds(db, year, month)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_start, _ = period_bounds(db, prev_year, prev_month)

    monthly_net_flow = net_flow(repo.flow_by_type(db, account_id, month_start, next_start))
    prev_monthly_net_flow = net_flow(repo.flow_by_type(db, account_id, prev_start, month_start))
    monthly_variation = variation_pct(monthly_net_flow, prev_monthly_net_flow)
    avg_expense = repo.average_expense(db, account_id, start_date, end_date)

    return {
        "currency": account.currency,
        "monthly_net_flow": round(monthly_net_flow, 2),
        "prev_monthly_net_flow": round(prev_monthly_net_flow, 2),
        "monthly_variation": round(monthly_variation, 2) if monthly_variation is not None else None,
        "avg_expense": round(avg_expense, 2),
    }
