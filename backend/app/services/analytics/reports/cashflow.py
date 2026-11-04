"""Projection de trésorerie (échéances récurrentes à venir)."""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.time import end_of_today
from app.domain.finance import get_recurring_occurrences, is_lapsed
from app.domain.recurring import transfer_credit_date
from app.domain.reports import flag_possible_duplicates, simulate_cashflow
from app.integrations.currency import get_exchange_rates
from app.models.recurring_transaction import RecurringTransaction
from app.repositories.analytics import metrics as salary_repo
from app.repositories.analytics import reports as repo
from app.repositories.analytics.common import active_recurrings, ticket_restaurant_account_ids
from app.repositories.comptes.balances import active_accounts
from app.schemas.insight import CashflowProjection, ProjectionEvent
from app.services.comptes.wealth import account_values

INCOME_TYPES = ["Entree", "Interets", "versement", "dividende"]


async def compute_cashflow_projection(db: Session, days: int = 30, account_id: int | None = None) -> CashflowProjection:
    """Solde projeté sur `days` jours à partir du solde actuel et des transactions récurrentes."""
    now = datetime.now()
    end_date = now + timedelta(days=days)
    rates = await get_exchange_rates("EUR")
    current_bal, counted_ids = await _current_balance(db, account_id, rates)
    scheduled, entered = _scheduled_events(db, account_id, rates, end_date)
    events = scheduled + _projected_events(db, account_id, counted_ids, rates, now, end_date, entered)
    events.sort(key=lambda x: x.date)
    flag_possible_duplicates(events)
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


async def _current_balance(db: Session, account_id: int | None, rates: dict) -> tuple[float, set[int]]:
    """Valeur actuelle du compte, ou somme EUR des comptes actifs hors tickets restaurant (et leurs ids).

    Valeurs par `account_values` (source unique) ; les opérations à venir ne comptent qu'à leur date."""
    counted_ids: set[int] = set()  # comptes dont le solde est dans `current_bal`
    if account_id:
        account = repo.get_account(db, account_id)
        if not account:
            raise NotFoundError("Account not found")
        return (await account_values(db, [account]))[account_id].value, counted_ids
    tr_accounts = ticket_restaurant_account_ids(db)
    accounts = [acc for acc in active_accounts(db) if acc.id not in tr_accounts]
    values = await account_values(db, accounts)
    current_bal = 0.0
    for acc in accounts:
        if values[acc.id].source != "none":
            current_bal += values[acc.id].value_eur
            counted_ids.add(acc.id)
    return current_bal, counted_ids


def _scheduled_events(db: Session, account_id: int | None, rates: dict,
                      end_date: datetime) -> tuple[list[ProjectionEvent], set[tuple[int, date]]]:
    """Transactions saisies à l'avance (après aujourd'hui) et les échéances récurrentes qu'elles réalisent déjà."""
    tr_accounts = set() if account_id else ticket_restaurant_account_ids(db)
    currencies = {acc.id: acc.currency for acc in active_accounts(db)}
    events: list[ProjectionEvent] = []
    entered: set[tuple[int, date]] = set()
    for tx in repo.upcoming_transactions(db, account_id, tr_accounts, end_of_today(), end_date):
        # Vue globale : montant converti en EUR (le montant stocké est dans la devise du compte)
        amount = float(tx.amount) if account_id else float(tx.amount) / rates.get(currencies.get(tx.account_id, "EUR"), 1.0)
        events.append(ProjectionEvent(date=tx.date.isoformat(), name=tx.merchant, amount=amount, type="scheduled",
                                      is_income=tx.type in INCOME_TYPES, transaction_id=tx.id))
        if tx.recurring_transaction_id is not None:
            entered.add((tx.recurring_transaction_id, tx.date.date()))
    return events, entered


def _projected_events(db: Session, account_id: int | None, counted_ids: set[int], rates: dict,
                      now: datetime, end_date: datetime, entered: set[tuple[int, date]]) -> list[ProjectionEvent]:
    tr_accounts = set() if account_id else ticket_restaurant_account_ids(db)
    events: list[ProjectionEvent] = []
    dest = repo.get_account(db, account_id) if account_id else None
    for rd in active_recurrings(db, account_id, tr_accounts):
        incoming = dest is not None and rd.account_id != account_id  # virement récurrent qui arrive sur ce compte
        # Vue globale : un virement vers un compte déjà compté dans le solde ne change pas le total
        if not account_id and rd.transfer_to_account_id in counted_ids:
            continue
        # Récurrence plus prélevée depuis deux périodes (abonnement arrêté sans être désactivé)
        if is_lapsed(rd.frequency, repo.last_occurrence(db, rd.id), now):
            continue
        for occ in get_recurring_occurrences(rd, now, end_date):
            when = transfer_credit_date(occ, rd.transfer_credit_day) if incoming else occ
            if when >= end_date or (rd.id, when.date()) in entered:  # déjà saisie à la main : ne pas la compter deux fois
                continue
            amount_target = float(_projected_amount(db, rd, occ))
            if incoming and dest is not None:  # entrée dans la devise du compte de destination
                amount_target = amount_target / rates.get(rd.currency, 1.0) * rates.get(dest.currency, 1.0)
            elif not account_id and rd.currency != "EUR":  # vue globale : montant converti en EUR
                amount_target = amount_target / rates.get(rd.currency, 1.0)
            events.append(ProjectionEvent(
                date=when.isoformat(),
                name=rd.name,
                amount=amount_target,
                type="recurring",
                is_income=True if incoming else rd.type in INCOME_TYPES,
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
