"""Calendrier du mois : transactions réelles, récurrences projetées et solde jour par jour."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.time import end_of_today
from app.domain.finance import get_recurring_occurrences, month_label_from_date
from app.domain.metrics import daily_balances
from app.domain.recurring import transfer_credit_date
from app.integrations.currency import get_exchange_rates
from app.models.recurring_transaction import RecurringTransaction
from app.repositories.analytics import metrics as repo
from app.repositories.analytics.common import active_recurrings, ticket_restaurant_account_ids
from app.repositories.comptes import balances


async def compute_calendar(db: Session, month: int, year: int, account_id: int | None = None) -> dict:
    start_month = datetime(year, month, 1)
    end_month = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    sim_start = min(start_month, today)

    tr_accounts = ticket_restaurant_account_ids(db)
    real_txs = repo.transactions_between(db, sim_start, end_month, account_id, tr_accounts)
    real_inv_txs = repo.investment_transactions_between(db, sim_start, end_month, account_id)
    rates = await get_exchange_rates("EUR")
    accounts = repo.all_accounts(db)
    projected = _projected_events(db, sim_start, end_month, account_id, tr_accounts, real_txs, real_inv_txs, accounts, rates)
    formatted_real = _real_events(real_txs, real_inv_txs)

    balances = _opening_balances(db, accounts, account_id, sim_start)
    currencies = {acc.id: acc.currency for acc in accounts}
    events = formatted_real + projected
    return {
        "month": month,
        "year": year,
        "events": [ev for ev in sorted(events, key=lambda x: x["date"]) if datetime.fromisoformat(ev["date"]) >= start_month],
        "daily_balances": daily_balances(events, balances, currencies, rates, sim_start, start_month, end_month, account_id),
    }


def _opening_balances(db: Session, accounts: list, account_id: int | None, sim_start: datetime) -> dict[int, float]:
    """Dernier solde courant avant le début de la simulation (du compte, ou de chaque compte actif)."""
    ids = [account_id] if account_id else [a.id for a in accounts if a.active]
    last = balances.latest_balances_by_account(db, ids, sim_start)
    return {acc_id: (last[acc_id].running_balance or 0.0) if acc_id in last else 0.0 for acc_id in ids}


def _projected_events(db: Session, start: datetime, end: datetime, account_id: int | None, tr_accounts: set[int],
                      real_txs: list, real_inv_txs: list, accounts: list, rates: dict) -> list[dict]:
    """Occurrences des récurrences actives non encore réalisées (même récurrence, même jour)."""
    realized = {(tx.recurring_transaction_id, tx.date.date()) for tx in real_txs if tx.recurring_transaction_id is not None}
    for tx in real_inv_txs:
        if getattr(tx, "recurring_transaction_id", None) is not None:
            realized.add((tx.recurring_transaction_id, tx.date.date()))
    events = []
    by_id = {a.id: a for a in accounts}
    counted = {a.id for a in accounts if a.active and a.id not in tr_accounts}
    for rd in active_recurrings(db, account_id, tr_accounts):
        incoming = account_id is not None and rd.account_id != account_id  # virement qui arrive sur ce compte
        # Vue globale : un virement entre deux comptes comptés est neutre pour le total
        if account_id is None and rd.transfer_to_account_id in counted:
            continue
        for occ in get_recurring_occurrences(rd, start, end):
            proj_date, proj_amount, proj_note = _salary_projection(db, rd, occ)
            if incoming:
                proj_date = transfer_credit_date(occ, rd.transfer_credit_day)
                if proj_date >= end:
                    continue
            if (rd.id, proj_date.date()) in realized:
                continue
            if incoming:
                dest = by_id[account_id]
                events.append(_incoming_transfer_event(rd, proj_date, proj_amount, proj_note, dest, rates))
                continue
            events.append({
                "id": f"proj_{rd.id}_{proj_date.isoformat()}",
                "date": proj_date.isoformat(),
                "name": proj_note,
                "amount": proj_amount,
                "type": rd.type,
                "category_id": rd.category_id,
                "is_projected": True,
                "is_upcoming": True,
                "recurring_id": rd.id,
                "currency": rd.currency,
                "account_id": rd.account_id,
                "ticker": rd.ticker,
                "quantity": rd.quantity,
                "unit_price": rd.unit_price,
                "logo": rd.logo,
            })
    return events


def _incoming_transfer_event(rd: RecurringTransaction, when: datetime, amount: float, name: str, dest, rates: dict) -> dict:
    """Entrée projetée d'un virement récurrent sur le compte de destination, dans sa devise."""
    converted = amount / rates.get(rd.currency, 1.0) * rates.get(dest.currency, 1.0)
    return {
        "id": f"proj_{rd.id}_{when.isoformat()}",
        "date": when.isoformat(),
        "name": name,
        "amount": converted,
        "type": "versement" if dest.type == "investissement" else "Entree",
        "category_id": None,
        "is_projected": True,
        "is_upcoming": True,
        "recurring_id": rd.id,
        "currency": dest.currency,
        "account_id": dest.id,
        "logo": rd.logo,
    }


def _salary_projection(db: Session, rd: RecurringTransaction, occ: datetime) -> tuple[datetime, float, str]:
    """Date, montant et libellé d'une occurrence ; salaire et tickets restaurant suivent le mois renseigné."""
    proj_date, proj_amount, proj_note = occ, rd.amount, rd.name
    config = repo.salary_config_for_recurring(db, rd.id)
    if not config:
        return proj_date, proj_amount, proj_note
    month_label = month_label_from_date(occ)
    if rd.id == config.ticket_recurring_id and occ.day < 15:
        work_month = occ - timedelta(days=20)
        salary_month_label = f"{work_month.year}-{work_month.month:02d}"
    else:
        salary_month_label = f"{occ.year}-{occ.month:02d}"
    salary_month = repo.salary_month(db, config.id, salary_month_label)
    tt_days_count = 0
    if salary_month:
        tt_days_count = repo.telecommuting_count(db, config.id, salary_month_label)
        if rd.id == config.salary_recurring_id and salary_month.salary_date:
            proj_date = datetime.combine(salary_month.salary_date, datetime.min.time())
        if rd.id == config.ticket_recurring_id and salary_month.ticket_date:
            proj_date = datetime.combine(salary_month.ticket_date, datetime.min.time())
    if rd.id == config.salary_recurring_id:
        proj_amount = config.net_salary - tt_days_count * config.ticket_employee_share
        proj_note = f"Salaire ({month_label})"
    elif rd.id == config.ticket_recurring_id:
        proj_amount = tt_days_count * config.ticket_value
        proj_note = f"Tickets Restaurant ({month_label})"
    return proj_date, proj_amount, proj_note


def _real_events(real_txs: list, real_inv_txs: list) -> list[dict]:
    events = [{
        "id": f"tx_{tx.id}",
        "date": tx.date.isoformat(),
        "name": tx.merchant,
        "amount": tx.amount,
        "type": tx.type,
        "category_id": tx.category_id,
        "is_projected": False,
        "is_upcoming": tx.date >= end_of_today(),
        "currency": tx.currency,
        "account_id": tx.account_id,
        "running_balance": getattr(tx, "running_balance", None),
        "logo": tx.recurring_logo,
    } for tx in real_txs]
    events += [{
        "id": f"inv_{tx.id}",
        "date": tx.date.isoformat(),
        "name": f"[{tx.type.capitalize()}] {tx.note or 'Investissement'}",
        "amount": tx.amount,
        "type": tx.type,
        "category_id": None,
        "is_projected": False,
        "is_upcoming": tx.date >= end_of_today(),
        "currency": tx.currency,
        "account_id": tx.account_id,
        "ticker": getattr(tx, "ticker", None),
        "quantity": getattr(tx, "quantity", None),
        "unit_price": getattr(tx, "unit_price", None),
    } for tx in real_inv_txs]
    return events
