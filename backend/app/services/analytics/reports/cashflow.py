"""Projection de trésorerie (échéances récurrentes à venir)."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.domain.finance import get_recurring_occurrences, is_lapsed
from app.domain.reports import simulate_cashflow
from app.integrations.currency import get_exchange_rates
from app.models.recurring_transaction import RecurringTransaction
from app.repositories.analytics import metrics as salary_repo
from app.repositories.analytics import reports as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.schemas.insight import CashflowProjection, ProjectionEvent

INCOME_TYPES = ["Entree", "Interets", "versement", "dividende"]


async def compute_cashflow_projection(db: Session, days: int = 30, account_id: int | None = None) -> CashflowProjection:
    """Solde projeté sur `days` jours à partir du solde actuel et des transactions récurrentes."""
    now = datetime.now()
    end_date = now + timedelta(days=days)
    rates = await get_exchange_rates("EUR")
    current_bal, counted_ids = _current_balance(db, account_id, rates)
    events = _projected_events(db, account_id, counted_ids, rates, now, end_date)
    events.sort(key=lambda x: x.date)
    points, simulated_bal, low_point, low_point_date = simulate_cashflow(events, current_bal, now, end_date)
    return CashflowProjection(
        points=points,
        events=events,
        current_balance=round(current_bal, 2),
        projected_balance=round(simulated_bal, 2),
        low_point=round(low_point, 2),
        low_point_date=low_point_date,
        days=days
    )


def _current_balance(db: Session, account_id: int | None, rates: dict) -> tuple[float, set[int]]:
    """Dernier solde du compte, ou somme EUR des comptes actifs hors tickets restaurant (et leurs ids)."""
    current_bal = 0.0
    counted_ids: set[int] = set()  # comptes dont le solde est dans `current_bal`
    if account_id:
        if not repo.get_account(db, account_id):
            raise NotFoundError("Account not found")
        last_tx = repo.last_transaction(db, account_id)
        if last_tx:
            current_bal = float(last_tx.running_balance)
        return current_bal, counted_ids
    tr_accounts = ticket_restaurant_account_ids(db)
    for acc in repo.active_accounts(db):
        if tr_accounts and acc.id in tr_accounts:
            continue
        last_tx = repo.last_transaction(db, acc.id)
        if last_tx:
            current_bal += float(last_tx.running_balance) / rates.get(acc.currency, 1.0)
            counted_ids.add(acc.id)
    return current_bal, counted_ids


def _projected_events(db: Session, account_id: int | None, counted_ids: set[int], rates: dict,
                      now: datetime, end_date: datetime) -> list[ProjectionEvent]:
    tr_accounts = set() if account_id else ticket_restaurant_account_ids(db)
    events: list[ProjectionEvent] = []
    for rd in repo.active_recurrings(db, account_id, tr_accounts):
        # Vue globale : un virement vers un compte déjà compté dans le solde ne change pas le total
        if not account_id and rd.transfer_to_account_id in counted_ids:
            continue
        # Récurrence plus prélevée depuis deux périodes (abonnement arrêté sans être désactivé)
        if is_lapsed(rd.frequency, repo.last_occurrence(db, rd.id), now):
            continue
        for occ in get_recurring_occurrences(rd, now, end_date):
            amount_target = float(_projected_amount(db, rd, occ))
            # Vue globale : montant converti en EUR
            if not account_id and rd.currency != "EUR":
                amount_target = amount_target / rates.get(rd.currency, 1.0)
            events.append(ProjectionEvent(
                date=occ.isoformat(),
                name=rd.name,
                amount=amount_target,
                type="recurring",
                is_income=rd.type in INCOME_TYPES,
            ))
    return events


def _projected_amount(db: Session, rd: RecurringTransaction, occ: datetime) -> float:
    """Montant d'une occurrence ; salaire et tickets restaurant dépendent des jours de télétravail du mois."""
    config = salary_repo.salary_config_for_recurring(db, rd.id)
    if not config:
        return rd.amount
    if rd.id == config.ticket_recurring_id and occ.day < 15:
        work_month = occ - timedelta(days=20)
        salary_month_label = f"{work_month.year}-{work_month.month:02d}"
    else:
        salary_month_label = f"{occ.year}-{occ.month:02d}"
    tt_days_count = 0
    if salary_repo.salary_month(db, config.id, salary_month_label):
        tt_days_count = salary_repo.telecommuting_count(db, config.id, salary_month_label)
    if rd.id == config.salary_recurring_id:
        return config.net_salary - tt_days_count * config.ticket_employee_share
    if rd.id == config.ticket_recurring_id:
        return tt_days_count * config.ticket_value
    return rd.amount
