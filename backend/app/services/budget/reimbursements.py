"""Remboursements : créances sur une Sortie et affectations d'Entree qui les soldent.

Seule porte d'entrée pour créer, modifier ou supprimer créances et affectations. Chaque mutation
recalcule `transactions.reimbursement_offset` des transactions touchées (`sync_offsets`), que les KPI
retranchent du montant (`repositories/analytics/common.py::NET_AMOUNT`). Aucun montant bancaire n'est modifié.
"""
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import InvalidOperationError, NotFoundError
from app.core.i18n import tr
from app.models.account import Account
from app.models.reimbursement import ReimbursementAllocation, ReimbursementClaim
from app.models.transaction import Transaction
from app.repositories.budget import reimbursements as repo
from app.schemas.reimbursement import AllocationCreate, ClaimCreate, ClaimUpdate

EPS = 0.005
CANDIDATE_DAYS_BEFORE = 7
CANDIDATE_DAYS_AFTER = 180
CANDIDATE_LIMIT = 30


def cents(value: float | None) -> float:
    return round(float(value or 0.0), 2)


def _refuse(detail: str) -> None:
    raise InvalidOperationError(detail)


def get_transaction(db: Session, tx_id: int) -> Transaction:
    tx = db.get(Transaction, tx_id)
    if tx is None:
        raise NotFoundError(tr("reimbursements.transaction_not_found"))
    return tx


def require_claim(db: Session, claim_id: int) -> ReimbursementClaim:
    claim = repo.get_claim(db, claim_id)
    if not claim:
        raise NotFoundError(tr("reimbursements.claim_not_found"))
    return claim


def require_allocation(db: Session, allocation_id: int) -> ReimbursementAllocation:
    allocation = repo.get_allocation(db, allocation_id)
    if not allocation:
        raise NotFoundError(tr("reimbursements.allocation_not_found"))
    return allocation


def account_currency(db: Session, tx: Transaction) -> str:
    account = db.get(Account, tx.account_id)
    return account.currency if account else "EUR"


def claim_received(db: Session, claim_id: int) -> float:
    return cents(repo.claim_received_total(db, claim_id))


def entree_allocated(db: Session, entree_id: int) -> float:
    return cents(repo.entree_allocated_total(db, entree_id))


def sortie_expected(db: Session, sortie_id: int, exclude_claim_id: int | None = None) -> float:
    return cents(repo.sortie_expected_total(db, sortie_id, exclude_claim_id))


def sortie_received(db: Session, sortie_id: int) -> float:
    return cents(repo.sortie_received_total(db, sortie_id))


def sync_offsets(db: Session, tx_ids: set[int]) -> None:
    """Recalcule `reimbursement_offset` des transactions données (sans commit)."""
    db.flush()
    for tx_id in tx_ids:
        tx = db.get(Transaction, tx_id)
        if tx is None:
            continue
        if tx.type == "Sortie":
            tx.reimbursement_offset = sortie_received(db, tx_id)
        elif tx.type == "Entree":
            tx.reimbursement_offset = entree_allocated(db, tx_id)
        else:
            tx.reimbursement_offset = 0.0


def has_reimbursement(db: Session, tx_id: int) -> bool:
    """La transaction porte une créance ou une affectation (elle ne peut plus être un virement)."""
    return repo.has_reimbursement(db, tx_id)


def check_transaction_change(db: Session, tx: Transaction, new_type: str, new_amount: float) -> None:
    """Refuse une modification qui casserait les créances ou affectations de `tx`."""
    expected = sortie_expected(db, tx.id)
    allocated = entree_allocated(db, tx.id)
    if expected <= 0 and allocated <= 0:
        return
    if new_type != tx.type:
        _refuse(tr("reimbursements.has_claims_type"))
    if expected > 0 and cents(new_amount) < expected - EPS:
        _refuse(tr("reimbursements.amount_below_claims"))
    if allocated > 0 and cents(new_amount) < allocated - EPS:
        _refuse(tr("reimbursements.amount_below_allocated"))


def detach_before_delete(db: Session, tx: Transaction) -> set[int]:
    """Supprime créances et affectations de `tx` ; renvoie les transactions de l'autre côté à resynchroniser."""
    touched: set[int] = set()
    for claim in repo.claims_of(db, tx.id):
        touched.update(a.entree_transaction_id for a in claim.allocations)
        db.delete(claim)
    for allocation in repo.allocations_of_entree(db, tx.id):
        touched.add(allocation.claim.transaction_id)
        db.delete(allocation)
    touched.discard(tx.id)
    return touched


def create_claim(db: Session, transaction_id: int, debtor: str, expected_amount: float, note: str | None = None) -> ReimbursementClaim:
    sortie = get_transaction(db, transaction_id)
    if sortie.type != "Sortie":
        _refuse(tr("reimbursements.claim_on_expense_only"))
    if sortie.is_transfer:
        _refuse(tr("reimbursements.claim_on_transfer"))
    expected = cents(expected_amount)
    if expected <= 0:
        _refuse(tr("reimbursements.expected_positive"))
    if sortie_expected(db, sortie.id) + expected > cents(sortie.amount) + EPS:
        _refuse(tr("reimbursements.claims_exceed_expense"))
    claim = ReimbursementClaim(transaction_id=sortie.id, debtor=debtor.strip(), expected_amount=expected, note=note)
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def update_claim(db: Session, claim: ReimbursementClaim, data: dict[str, Any]) -> ReimbursementClaim:
    if data.get("expected_amount") is not None:
        expected = cents(data["expected_amount"])
        if expected <= 0:
            _refuse(tr("reimbursements.expected_positive"))
        if expected < claim_received(db, claim.id) - EPS:
            _refuse(tr("reimbursements.expected_below_received"))
        sortie = get_transaction(db, claim.transaction_id)
        if sortie_expected(db, sortie.id, exclude_claim_id=claim.id) + expected > cents(sortie.amount) + EPS:
            _refuse(tr("reimbursements.claims_exceed_expense"))
        claim.expected_amount = expected
    if data.get("debtor"):
        claim.debtor = data["debtor"].strip()
    if "note" in data:
        claim.note = data["note"]
    db.commit()
    db.refresh(claim)
    return claim


def delete_claim(db: Session, claim: ReimbursementClaim) -> None:
    touched = {claim.transaction_id, *(a.entree_transaction_id for a in claim.allocations)}
    db.delete(claim)
    sync_offsets(db, touched)
    db.commit()


def allocate(db: Session, claim: ReimbursementClaim, entree_id: int, amount: float | None = None) -> ReimbursementAllocation:
    entree = get_transaction(db, entree_id)
    if entree.type != "Entree":
        _refuse(tr("reimbursements.only_entree_repays"))
    if entree.is_transfer:
        _refuse(tr("errors.transfer_not_reimbursement"))
    sortie = get_transaction(db, claim.transaction_id)
    if account_currency(db, entree) != account_currency(db, sortie):
        _refuse(tr("reimbursements.same_currency"))

    existing = repo.allocation_between(db, claim.id, entree.id)
    current = cents(existing.amount) if existing else 0.0
    claim_room = cents(claim.expected_amount - (claim_received(db, claim.id) - current))
    entree_room = cents(entree.amount - (entree_allocated(db, entree.id) - current))
    value = cents(min(claim_room, entree_room) if amount is None else amount)
    if value <= 0:
        _refuse(tr("reimbursements.nothing_to_allocate"))
    if value > claim_room + EPS:
        _refuse(tr("reimbursements.exceeds_claim_remaining"))
    if value > entree_room + EPS:
        _refuse(tr("reimbursements.exceeds_entree_unallocated"))

    if existing:
        existing.amount = value
        allocation = existing
    else:
        allocation = ReimbursementAllocation(claim_id=claim.id, entree_transaction_id=entree.id, amount=value)
        db.add(allocation)
    sync_offsets(db, {sortie.id, entree.id})
    db.commit()
    db.refresh(allocation)
    db.refresh(claim)
    return allocation


def remove_allocation(db: Session, allocation: ReimbursementAllocation) -> None:
    claim = require_claim(db, allocation.claim_id)
    touched = {allocation.entree_transaction_id, claim.transaction_id}
    db.delete(allocation)
    sync_offsets(db, touched)
    db.commit()


def _label(tx: Transaction) -> str:
    return tx.merchant or tx.note or ""


def claim_views(db: Session, claims: list[ReimbursementClaim]) -> list[dict[str, Any]]:
    """Vue de chaque créance : totaux, dépense et affectations lus par lot (3 requêtes quel que soit le nombre de créances)."""
    received_by_id = repo.received_by_claim(db, [c.id for c in claims])
    tx_ids = {c.transaction_id for c in claims} | {a.entree_transaction_id for c in claims for a in c.allocations}
    txs = repo.transactions_with_currency(db, tx_ids)
    views = []
    for claim in claims:
        sortie, currency = txs[claim.transaction_id]
        received = cents(received_by_id.get(claim.id, 0.0))
        allocations = []
        for a in claim.allocations:
            entree = txs.get(a.entree_transaction_id, (None, ""))[0]
            allocations.append({
                "id": a.id, "entree_id": a.entree_transaction_id, "amount": cents(a.amount),
                "date": entree.date if entree else None, "label": _label(entree) if entree else None,
                "account_id": entree.account_id if entree else None,
            })
        views.append({
            "id": claim.id,
            "debtor": claim.debtor,
            "expected_amount": cents(claim.expected_amount),
            "received": received,
            "remaining": cents(claim.expected_amount - received),
            "note": claim.note,
            "created_at": claim.created_at,
            "currency": currency,
            "expense": {
                "id": sortie.id, "account_id": sortie.account_id, "date": sortie.date,
                "label": _label(sortie), "amount": cents(sortie.amount),
            },
            "allocations": allocations,
        })
    return views


def claim_view(db: Session, claim: ReimbursementClaim) -> dict[str, Any]:
    return claim_views(db, [claim])[0]


def list_claims(db: Session, status: str = "open", debtor: str | None = None) -> list[dict[str, Any]]:
    views = claim_views(db, repo.claims_by_date(db, debtor.strip().lower() if debtor else None))
    if status == "open":
        return [v for v in views if v["remaining"] > EPS]
    if status == "settled":
        return [v for v in views if v["remaining"] <= EPS]
    return views


def summary(db: Session) -> dict[str, Any]:
    by_debtor: dict[str, dict[str, Any]] = {}
    for view in list_claims(db, "open"):
        key = view["debtor"].strip().lower()
        row = by_debtor.setdefault(key, {"debtor": view["debtor"], "claims": 0, "due": 0.0})
        row["claims"] += 1
        row["due"] = cents(row["due"] + view["remaining"])
    debtors = sorted(by_debtor.values(), key=lambda r: (-r["due"], r["debtor"]))
    return {"total_due": cents(sum(r["due"] for r in debtors)), "debtors": debtors}


def candidates(db: Session, claim: ReimbursementClaim) -> list[dict[str, Any]]:
    """Entrées qui peuvent solder la créance : débiteur dans le libellé, puis montant exact, puis date."""
    sortie = db.get(Transaction, claim.transaction_id)
    if sortie is None:
        raise NotFoundError(tr("errors.transaction_not_found"))
    currency = account_currency(db, sortie)
    remaining = cents(claim.expected_amount - claim_received(db, claim.id))
    debtor = claim.debtor.strip().lower()
    already = {a.entree_transaction_id for a in claim.allocations}
    rows = repo.entree_candidates(
        db, currency, sortie.date - timedelta(days=CANDIDATE_DAYS_BEFORE), sortie.date + timedelta(days=CANDIDATE_DAYS_AFTER)
    )
    out: list[dict[str, Any]] = []
    for e in rows:
        if e.id in already:
            continue
        available = cents(e.amount - entree_allocated(db, e.id))
        if available <= EPS:
            continue
        label = _label(e)
        out.append({
            "id": e.id, "account_id": e.account_id, "date": e.date, "label": label,
            "amount": cents(e.amount), "available": available,
            "day_gap": abs((e.date.date() - sortie.date.date()).days),
            "debtor_match": bool(debtor) and debtor in label.lower(),
        })
    out.sort(key=lambda c: (not c["debtor_match"], abs(c["available"] - remaining) > EPS, c["day_gap"], c["id"]))
    return out[:CANDIDATE_LIMIT]


def claims_for_entree(db: Session, entree: Transaction) -> dict[str, Any]:
    """Créances ouvertes auxquelles affecter `entree` (débiteur reconnu dans le libellé d'abord)."""
    if entree.type != "Entree":
        _refuse(tr("reimbursements.only_entree_repays"))
    currency = account_currency(db, entree)
    label = _label(entree).lower()
    open_claims = [v for v in list_claims(db, "open") if v["currency"] == currency]
    open_claims.sort(key=lambda v: (v["debtor"].strip().lower() not in label, v["expense"]["date"]))
    allocations = repo.allocations_of_entree(db, entree.id)
    return {
        "entree_id": entree.id,
        "amount": cents(entree.amount),
        "available": cents(entree.amount - entree_allocated(db, entree.id)),
        "open_claims": open_claims,
        "allocations": [
            {"id": a.id, "claim_id": a.claim_id, "amount": cents(a.amount), "debtor": a.claim.debtor} for a in allocations
        ],
    }


def create_claim_view(db: Session, payload: ClaimCreate) -> dict[str, Any]:
    claim = create_claim(db, payload.transaction_id, payload.debtor, payload.expected_amount, payload.note)
    return claim_view(db, claim)


def update_claim_view(db: Session, claim_id: int, payload: ClaimUpdate) -> dict[str, Any]:
    claim = update_claim(db, require_claim(db, claim_id), payload.model_dump(exclude_unset=True))
    return claim_view(db, claim)


def allocate_view(db: Session, claim_id: int, payload: AllocationCreate) -> dict[str, Any]:
    claim = require_claim(db, claim_id)
    allocate(db, claim, payload.entree_id, payload.amount)
    return claim_view(db, claim)
