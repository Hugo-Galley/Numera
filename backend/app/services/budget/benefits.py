"""Aides perçues (prime d'activité, APL…) : versements reçus, statut du mois, déclaration périodique.

Aucune transaction n'est créée : les versements sont les entrées dont le libellé (ou la note) contient
le motif de l'aide. Une entrée qui correspond à plusieurs aides (deux aides CAF) est rattachée à celle
dont le montant attendu est le plus proche. Les aides restent des revenus ordinaires dans les KPI.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.domain import benefits as calc
from app.models.benefit import Benefit
from app.models.transaction import Transaction
from app.repositories.budget import benefits as repo
from app.schemas.benefit import BenefitCreate, BenefitDeclared, BenefitUpdate

# Historique scanné : l'année civile en cours et les 12 derniers mois
HISTORY_DAYS = 400
PAYMENTS_SHOWN = 12


@dataclass
class BenefitState:
    benefit: Benefit
    payments: list[Transaction] = field(default_factory=list)  # du plus récent au plus ancien
    status: str = "pending"
    expected_date: date | None = None
    next_payment_date: date | None = None
    declaration_days_left: int | None = None


def _payments_by_benefit(db: Session, benefits: list[Benefit], today: date) -> dict[int, list[Transaction]]:
    since = datetime.combine(today - timedelta(days=HISTORY_DAYS), time.min)
    txs: dict[int, Transaction] = {}
    candidates: dict[int, list[int]] = defaultdict(list)
    for b in benefits:
        for t in repo.matching_entries(db, b, since):
            txs[t.id] = t
            candidates[t.id].append(b.id)
    owners = calc.assign(candidates, {i: t.amount for i, t in txs.items()}, {b.id: b.amount for b in benefits})
    result: dict[int, list[Transaction]] = {b.id: [] for b in benefits}
    for tx_id, benefit_id in owners.items():
        result[benefit_id].append(txs[tx_id])
    for rows in result.values():
        rows.sort(key=lambda t: (t.date, t.id), reverse=True)
    return result


def compute_states(db: Session, today: date | None = None) -> list[BenefitState]:
    """État de toutes les aides (le rattachement des versements se fait entre toutes les aides)."""
    today = today or date.today()
    benefits = repo.list_ordered(db)
    payments = _payments_by_benefit(db, benefits, today)
    states = []
    for b in benefits:
        st = BenefitState(benefit=b, payments=payments[b.id])
        status, st.expected_date = calc.month_status(today, b.payment_day, (t.date.date() for t in st.payments), b.start_date)
        st.status = status if b.active else "inactive"
        st.next_payment_date = calc.next_payment_date(today, b.payment_day, status)
        if b.next_declaration_date is not None:
            st.declaration_days_left = (b.next_declaration_date - today).days
        states.append(st)
    return states


def _payment(t: Transaction) -> dict:
    return {"transaction_id": t.id, "date": t.date.date(), "amount": round(t.amount, 2), "merchant": t.merchant}


def to_read(st: BenefitState, today: date | None = None) -> dict:
    today = today or date.today()
    b = st.benefit
    last = st.payments[0] if st.payments else None
    return {
        "id": b.id,
        "name": b.name,
        "organization": b.organization,
        "amount": b.amount,
        "payment_day": b.payment_day,
        "match_pattern": b.match_pattern,
        "account_id": b.account_id,
        "start_date": b.start_date,
        "declaration_interval_months": b.declaration_interval_months,
        "next_declaration_date": b.next_declaration_date,
        "note": b.note,
        "active": b.active,
        "account_name": b.account.name if b.account else None,
        "status": st.status,
        "expected_date": st.expected_date,
        "next_payment_date": st.next_payment_date,
        "last_payment": _payment(last) if last else None,
        "amount_changed": bool(last) and calc.amount_changed(b.amount, last.amount),
        "received_this_year": round(sum(t.amount for t in st.payments if t.date.year == today.year), 2),
        "payments": [_payment(t) for t in st.payments[:PAYMENTS_SHOWN]],
        "declaration_days_left": st.declaration_days_left,
    }


def _require(db: Session, benefit_id: int) -> Benefit:
    benefit = repo.get(db, benefit_id)
    if benefit is None:
        raise NotFoundError("Aide introuvable")
    return benefit


def _read(db: Session, benefit_id: int) -> dict:
    return next(to_read(st) for st in compute_states(db) if st.benefit.id == benefit_id)


def list_benefits(db: Session) -> list[dict]:
    return [to_read(st) for st in compute_states(db)]


def benefits_summary(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    states = [st for st in compute_states(db, today) if st.benefit.active]
    year_ago = datetime.combine(today - timedelta(days=365), time.min)
    declarations = sorted((st for st in states if st.declaration_days_left is not None), key=lambda st: st.declaration_days_left)
    return {
        "monthly_expected_total": round(sum(st.benefit.amount for st in states), 2),
        "received_this_year": round(sum(t.amount for st in states for t in st.payments if t.date.year == today.year), 2),
        "received_last_12_months": round(sum(t.amount for st in states for t in st.payments if t.date >= year_ago), 2),
        "late_count": sum(1 for st in states if st.status == "late"),
        "next_declaration": to_read(declarations[0], today) if declarations else None,
    }


def _check_declaration(interval: int | None, next_date: date | None) -> None:
    if (interval is None) != (next_date is None):
        raise BusinessRuleError("Indiquez à la fois la périodicité et la date de la prochaine déclaration")


def create_benefit(db: Session, payload: BenefitCreate) -> dict:
    if payload.account_id is not None and not repo.account_exists(db, payload.account_id):
        raise NotFoundError("Compte introuvable")
    _check_declaration(payload.declaration_interval_months, payload.next_declaration_date)
    benefit = Benefit(**payload.model_dump())
    repo.add(db, benefit)
    db.commit()
    return _read(db, benefit.id)


def update_benefit(db: Session, benefit_id: int, payload: BenefitUpdate) -> dict:
    benefit = _require(db, benefit_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("account_id") is not None and not repo.account_exists(db, data["account_id"]):
        raise NotFoundError("Compte introuvable")
    for name in ("name", "organization", "amount", "payment_day", "match_pattern", "active"):
        if name in data and data[name] is None:
            data.pop(name)  # colonnes non nullables : `null` = ne pas modifier
    _check_declaration(
        data.get("declaration_interval_months", benefit.declaration_interval_months),
        data.get("next_declaration_date", benefit.next_declaration_date),
    )
    for name, value in data.items():
        setattr(benefit, name, value)
    db.commit()
    return _read(db, benefit.id)


def mark_declared(db: Session, benefit_id: int, payload: BenefitDeclared, today: date | None = None) -> dict:
    """Déclaration faite : la prochaine échéance avance d'un intervalle (et le montant notifié est repris)."""
    today = today or date.today()
    benefit = _require(db, benefit_id)
    if benefit.declaration_interval_months is None or benefit.next_declaration_date is None:
        raise BusinessRuleError("Cette aide n'a pas de déclaration périodique")
    benefit.next_declaration_date = calc.advance_declaration(benefit.next_declaration_date, benefit.declaration_interval_months, today)
    if payload.amount is not None:
        benefit.amount = payload.amount
    db.commit()
    return _read(db, benefit.id)


def delete_benefit(db: Session, benefit_id: int) -> None:
    repo.delete(db, _require(db, benefit_id))
    db.commit()
