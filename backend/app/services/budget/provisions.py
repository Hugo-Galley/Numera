"""Provisions pour grosses dépenses périodiques.

Pour chaque provision : prochaine échéance, ce qui devrait déjà être mis de côté (au prorata du
temps écoulé depuis l'échéance précédente), effort mensuel pour être prêt à temps et, si un
compte est rattaché, constitution réelle. Le solde d'un compte est réparti entre ses provisions
au prorata de leur cible : un compte qui couvre la somme des cibles est « à jour ».
Rien n'est écrit en base : le prévisionnel reste séparé du réel.
"""

import calendar
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.integrations.currency import get_exchange_rates
from app.models.provision import Provision
from app.repositories.budget import provisions as repo
from app.schemas.provision import ProvisionCreate, ProvisionUpdate
from app.services.comptes.wealth import account_values

# Fenêtre autour de l'échéance précédente pour retrouver le paiement réel
PAYMENT_WINDOW_DAYS = 60
# Tolérance avant de déclarer une provision en retard (arrondis, intérêts, petits écarts)
BEHIND_TOLERANCE_EUR = 1.0
UPCOMING_DAYS = 90


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def due_window(anchor: date, interval_months: int, today: date) -> tuple[date, date]:
    """(échéance précédente, prochaine échéance ≥ today), déduites de l'échéance de référence."""
    # Saut direct au bon nombre d'intervalles, puis ajustement (jours en fin de mois)
    months_apart = (today.year - anchor.year) * 12 + today.month - anchor.month
    k = math.floor(months_apart / interval_months)
    nxt = add_months(anchor, k * interval_months)
    while nxt < today:
        k += 1
        nxt = add_months(anchor, k * interval_months)
    while add_months(anchor, (k - 1) * interval_months) >= today:
        k -= 1
        nxt = add_months(anchor, k * interval_months)
    return add_months(anchor, (k - 1) * interval_months), nxt


def _months_between(start: date, end: date) -> int:
    """Mois pleins entre deux dates, au moins 1 (dernier versement possible le mois de l'échéance)."""
    months = (end.year - start.year) * 12 + end.month - start.month - (1 if end.day < start.day else 0)
    return max(1, months)


@dataclass
class ProvisionState:
    provision: Provision
    previous_due: date
    next_due: date
    months_left: int
    monthly_amount: float
    target_now: float
    monthly_needed: float = 0.0
    funded: float | None = None
    status: str = "untracked"
    last_payment: dict | None = None


def _base_state(p: Provision, today: date) -> ProvisionState:
    previous_due, next_due = due_window(p.due_date, p.interval_months, today)
    span = max((next_due - previous_due).days, 1)
    elapsed = min(max((today - previous_due).days, 0), span)
    return ProvisionState(
        provision=p,
        previous_due=previous_due,
        next_due=next_due,
        months_left=_months_between(today, next_due),
        monthly_amount=p.amount / p.interval_months,
        target_now=p.amount * elapsed / span,
    )


async def _last_payment(db: Session, p: Provision, around: date, rates: dict[str, float]) -> dict | None:
    """Plus grosse dépense de la catégorie près de l'échéance précédente (parts de découpage comprises)."""
    if p.category_id is None:
        return None
    start = datetime.combine(around - timedelta(days=PAYMENT_WINDOW_DAYS), datetime.min.time())
    end = datetime.combine(around + timedelta(days=PAYMENT_WINDOW_DAYS + 1), datetime.min.time())
    rows = repo.category_expenses_between(db, p.category_id, start, end)
    if not rows:
        return None
    best = max(rows, key=lambda r: r.net_amount / rates.get(r.currency, 1.0))
    return {"date": best.date.date(), "amount": round(best.net_amount / rates.get(best.currency, 1.0), 2)}


async def compute_states(db: Session, provisions: list[Provision], today: date | None = None) -> list[ProvisionState]:
    today = today or date.today()
    rates = await get_exchange_rates("EUR")
    states = [_base_state(p, today) for p in provisions]

    # Constitution par compte rattaché (provisions actives seulement)
    tracked: dict[int, list[ProvisionState]] = {}
    for st in states:
        if st.provision.active and st.provision.account_id is not None:
            tracked.setdefault(st.provision.account_id, []).append(st)
    accounts = repo.accounts_in(db, tracked.keys()) if tracked else []
    values = await account_values(db, accounts) if accounts else {}
    for account_id, group in tracked.items():
        balance = values[account_id].value_eur if account_id in values else 0.0
        total_target = sum(st.target_now for st in group)
        ratio = 1.0 if total_target <= 0 else min(1.0, max(balance, 0.0) / total_target)
        for st in group:
            st.funded = st.target_now * ratio

    for st in states:
        p = st.provision
        st.last_payment = await _last_payment(db, p, st.previous_due, rates)
        if not p.active:
            st.status = "inactive"
            st.monthly_needed = 0.0
            continue
        constituted = st.funded if st.funded is not None else st.target_now
        st.monthly_needed = max(p.amount - constituted, 0.0) / st.months_left
        if st.funded is None:
            st.status = "untracked"
        elif st.funded < st.target_now - BEHIND_TOLERANCE_EUR:
            st.status = "behind"
        else:
            st.status = "on_track"
    return states


def to_read(st: ProvisionState) -> dict:
    p = st.provision
    return {
        "id": p.id,
        "name": p.name,
        "amount": p.amount,
        "interval_months": p.interval_months,
        "due_date": p.due_date,
        "category_id": p.category_id,
        "account_id": p.account_id,
        "note": p.note,
        "active": p.active,
        "category_name": p.category.name if p.category else None,
        "account_name": p.account.name if p.account else None,
        "next_due": st.next_due,
        "previous_due": st.previous_due,
        "months_left": st.months_left,
        "monthly_amount": round(st.monthly_amount, 2),
        "target_now": round(st.target_now, 2),
        "monthly_needed": round(st.monthly_needed, 2),
        "funded": round(st.funded, 2) if st.funded is not None else None,
        "status": st.status,
        "last_payment": st.last_payment,
    }


async def summary(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    provisions = repo.list_active(db)
    states = await compute_states(db, provisions, today)

    accounts: dict[int, dict] = {}
    for st in states:
        if st.provision.account_id is None or st.funded is None:
            continue
        acc = accounts.setdefault(
            st.provision.account_id,
            {"account_id": st.provision.account_id, "account_name": st.provision.account.name, "target_now": 0.0, "funded": 0.0},
        )
        acc["target_now"] += st.target_now
        acc["funded"] += st.funded
    if accounts:
        acc_rows = repo.accounts_in(db, accounts.keys())
        values = await account_values(db, acc_rows)
        for account_id, acc in accounts.items():
            acc["balance"] = round(values[account_id].value_eur if account_id in values else 0.0, 2)
            acc["gap"] = round(max(acc["target_now"] - acc["balance"], 0.0), 2)
            acc["target_now"] = round(acc["target_now"], 2)
            del acc["funded"]

    horizon = today + timedelta(days=UPCOMING_DAYS)
    upcoming = sorted((st for st in states if st.next_due <= horizon), key=lambda st: st.next_due)
    return {
        "monthly_total": round(sum(st.monthly_amount for st in states), 2),
        "target_now_total": round(sum(st.target_now for st in states), 2),
        "upcoming": [to_read(st) for st in upcoming],
        "accounts": list(accounts.values()),
        "behind_count": sum(1 for st in states if st.status == "behind"),
    }


def _check_refs(db: Session, category_id: int | None, account_id: int | None) -> None:
    if category_id is not None and not repo.category_exists(db, category_id):
        raise NotFoundError("Catégorie introuvable")
    if account_id is not None and not repo.account_exists(db, account_id):
        raise NotFoundError("Compte introuvable")


def _require(db: Session, provision_id: int) -> Provision:
    provision = repo.get(db, provision_id)
    if provision is None:
        raise NotFoundError("Provision introuvable")
    return provision


async def _read(db: Session, provision: Provision) -> dict:
    return to_read((await compute_states(db, [provision]))[0])


async def list_provisions(db: Session) -> list[dict]:
    states = await compute_states(db, repo.list_ordered(db))
    return [to_read(st) for st in sorted(states, key=lambda st: (not st.provision.active, st.next_due))]


async def provisions_summary(db: Session) -> dict:
    return await summary(db)


async def create_provision(db: Session, payload: ProvisionCreate) -> dict:
    _check_refs(db, payload.category_id, payload.account_id)
    provision = Provision(**payload.model_dump())
    repo.add(db, provision)
    db.commit()
    db.refresh(provision)
    return await _read(db, provision)


async def update_provision(db: Session, provision_id: int, payload: ProvisionUpdate) -> dict:
    provision = _require(db, provision_id)
    data = payload.model_dump(exclude_unset=True)
    _check_refs(db, data.get("category_id"), data.get("account_id"))
    for field in ("name", "amount", "interval_months", "due_date", "active"):
        if field in data and data[field] is None:
            data.pop(field)  # colonnes non nullables : `null` = ne pas modifier
    for field, value in data.items():
        setattr(provision, field, value)
    db.commit()
    db.refresh(provision)
    return await _read(db, provision)


def delete_provision(db: Session, provision_id: int) -> None:
    repo.delete(db, _require(db, provision_id))
    db.commit()
