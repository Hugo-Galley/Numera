"""Remboursements : créances sur une Sortie et affectations d'Entree qui les soldent.

Seule porte d'entrée pour créer, modifier ou supprimer créances et affectations. Chaque mutation
recalcule `transactions.reimbursement_offset` des transactions touchées (`sync_offsets`), que les KPI
retranchent du montant (`api/analytics/utils.py::NET_AMOUNT`). Aucun montant bancaire n'est modifié.
"""
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.reimbursement import ReimbursementAllocation, ReimbursementClaim
from app.models.transaction import Transaction

EPS = 0.005
CANDIDATE_DAYS_BEFORE = 7
CANDIDATE_DAYS_AFTER = 180
CANDIDATE_LIMIT = 30


def cents(value: float | None) -> float:
    return round(float(value or 0.0), 2)


def _refuse(detail: str) -> None:
    raise HTTPException(status_code=400, detail=detail)


def _get_tx(db: Session, tx_id: int) -> Transaction:
    tx = db.get(Transaction, tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    return tx


def account_currency(db: Session, tx: Transaction) -> str:
    account = db.get(Account, tx.account_id)
    return account.currency if account else "EUR"


def claim_received(db: Session, claim_id: int) -> float:
    total = db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0)).filter(
        ReimbursementAllocation.claim_id == claim_id
    ).scalar()
    return cents(total)


def entree_allocated(db: Session, entree_id: int) -> float:
    total = db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0)).filter(
        ReimbursementAllocation.entree_transaction_id == entree_id
    ).scalar()
    return cents(total)


def sortie_expected(db: Session, sortie_id: int, exclude_claim_id: int | None = None) -> float:
    q = db.query(func.coalesce(func.sum(ReimbursementClaim.expected_amount), 0.0)).filter(
        ReimbursementClaim.transaction_id == sortie_id
    )
    if exclude_claim_id is not None:
        q = q.filter(ReimbursementClaim.id != exclude_claim_id)
    return cents(q.scalar())


def sortie_received(db: Session, sortie_id: int) -> float:
    total = (
        db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0))
        .join(ReimbursementClaim, ReimbursementAllocation.claim_id == ReimbursementClaim.id)
        .filter(ReimbursementClaim.transaction_id == sortie_id)
        .scalar()
    )
    return cents(total)


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
    if db.query(ReimbursementClaim.id).filter(ReimbursementClaim.transaction_id == tx_id).first():
        return True
    return db.query(ReimbursementAllocation.id).filter(ReimbursementAllocation.entree_transaction_id == tx_id).first() is not None


def create_claim(db: Session, transaction_id: int, debtor: str, expected_amount: float, note: str | None = None) -> ReimbursementClaim:
    sortie = _get_tx(db, transaction_id)
    if sortie.type != "Sortie":
        _refuse("Une créance ne peut porter que sur une dépense (Sortie)")
    if sortie.is_transfer:
        _refuse("Un virement interne ne peut pas porter de créance")
    expected = cents(expected_amount)
    if expected <= 0:
        _refuse("Le montant attendu doit être positif")
    if sortie_expected(db, sortie.id) + expected > cents(sortie.amount) + EPS:
        _refuse("Le total des créances dépasse le montant de la dépense")
    claim = ReimbursementClaim(transaction_id=sortie.id, debtor=debtor.strip(), expected_amount=expected, note=note)
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def update_claim(db: Session, claim: ReimbursementClaim, data: dict) -> ReimbursementClaim:
    if data.get("expected_amount") is not None:
        expected = cents(data["expected_amount"])
        if expected <= 0:
            _refuse("Le montant attendu doit être positif")
        if expected < claim_received(db, claim.id) - EPS:
            _refuse("Le montant attendu ne peut pas être inférieur au montant déjà reçu : retirez d'abord des remboursements")
        sortie = _get_tx(db, claim.transaction_id)
        if sortie_expected(db, sortie.id, exclude_claim_id=claim.id) + expected > cents(sortie.amount) + EPS:
            _refuse("Le total des créances dépasse le montant de la dépense")
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
    entree = _get_tx(db, entree_id)
    if entree.type != "Entree":
        _refuse("Seule une entrée (Entree) peut rembourser une créance")
    if entree.is_transfer:
        _refuse("Un virement interne ne peut pas servir de remboursement")
    sortie = _get_tx(db, claim.transaction_id)
    if account_currency(db, entree) != account_currency(db, sortie):
        _refuse("La dépense et le remboursement doivent être dans la même devise")

    existing = (
        db.query(ReimbursementAllocation)
        .filter(ReimbursementAllocation.claim_id == claim.id, ReimbursementAllocation.entree_transaction_id == entree.id)
        .first()
    )
    current = cents(existing.amount) if existing else 0.0
    claim_room = cents(claim.expected_amount - (claim_received(db, claim.id) - current))
    entree_room = cents(entree.amount - (entree_allocated(db, entree.id) - current))
    value = cents(min(claim_room, entree_room) if amount is None else amount)
    if value <= 0:
        _refuse("Rien à affecter : la créance est soldée ou l'entrée est déjà entièrement affectée")
    if value > claim_room + EPS:
        _refuse("Le montant dépasse le reste dû de la créance")
    if value > entree_room + EPS:
        _refuse("Le montant dépasse la part non affectée de l'entrée")

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
    claim = db.get(ReimbursementClaim, allocation.claim_id)
    touched = {allocation.entree_transaction_id, claim.transaction_id}
    db.delete(allocation)
    sync_offsets(db, touched)
    db.commit()


def _label(tx: Transaction) -> str:
    return tx.merchant or tx.note or ""


def claim_view(db: Session, claim: ReimbursementClaim) -> dict:
    sortie = db.get(Transaction, claim.transaction_id)
    received = claim_received(db, claim.id)
    allocations = []
    for a in claim.allocations:
        entree = db.get(Transaction, a.entree_transaction_id)
        allocations.append({
            "id": a.id, "entree_id": a.entree_transaction_id, "amount": cents(a.amount),
            "date": entree.date if entree else None, "label": _label(entree) if entree else None,
            "account_id": entree.account_id if entree else None,
        })
    return {
        "id": claim.id,
        "debtor": claim.debtor,
        "expected_amount": cents(claim.expected_amount),
        "received": received,
        "remaining": cents(claim.expected_amount - received),
        "note": claim.note,
        "created_at": claim.created_at,
        "currency": account_currency(db, sortie),
        "expense": {
            "id": sortie.id, "account_id": sortie.account_id, "date": sortie.date,
            "label": _label(sortie), "amount": cents(sortie.amount),
        },
        "allocations": allocations,
    }


def list_claims(db: Session, status: str = "open", debtor: str | None = None) -> list[dict]:
    q = db.query(ReimbursementClaim).join(Transaction, ReimbursementClaim.transaction_id == Transaction.id)
    if debtor:
        q = q.filter(func.lower(ReimbursementClaim.debtor) == debtor.strip().lower())
    views = [claim_view(db, c) for c in q.order_by(Transaction.date.desc(), ReimbursementClaim.id).all()]
    if status == "open":
        return [v for v in views if v["remaining"] > EPS]
    if status == "settled":
        return [v for v in views if v["remaining"] <= EPS]
    return views


def summary(db: Session) -> dict:
    by_debtor: dict[str, dict] = {}
    for view in list_claims(db, "open"):
        key = view["debtor"].strip().lower()
        row = by_debtor.setdefault(key, {"debtor": view["debtor"], "claims": 0, "due": 0.0})
        row["claims"] += 1
        row["due"] = cents(row["due"] + view["remaining"])
    debtors = sorted(by_debtor.values(), key=lambda r: (-r["due"], r["debtor"]))
    return {"total_due": cents(sum(r["due"] for r in debtors)), "debtors": debtors}


def candidates(db: Session, claim: ReimbursementClaim) -> list[dict]:
    """Entrées qui peuvent solder la créance : débiteur dans le libellé, puis montant exact, puis date."""
    sortie = db.get(Transaction, claim.transaction_id)
    currency = account_currency(db, sortie)
    remaining = cents(claim.expected_amount - claim_received(db, claim.id))
    debtor = claim.debtor.strip().lower()
    already = {a.entree_transaction_id for a in claim.allocations}
    rows = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type == "Entree",
            Transaction.is_transfer.is_(False),
            Account.currency == currency,
            Transaction.date >= sortie.date - timedelta(days=CANDIDATE_DAYS_BEFORE),
            Transaction.date <= sortie.date + timedelta(days=CANDIDATE_DAYS_AFTER),
        )
        .all()
    )
    out = []
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


def claims_for_entree(db: Session, entree: Transaction) -> dict:
    """Créances ouvertes auxquelles affecter `entree` (débiteur reconnu dans le libellé d'abord)."""
    if entree.type != "Entree":
        _refuse("Seule une entrée (Entree) peut rembourser une créance")
    currency = account_currency(db, entree)
    label = _label(entree).lower()
    open_claims = [v for v in list_claims(db, "open") if v["currency"] == currency]
    open_claims.sort(key=lambda v: (v["debtor"].strip().lower() not in label, v["expense"]["date"]))
    allocations = (
        db.query(ReimbursementAllocation).filter(ReimbursementAllocation.entree_transaction_id == entree.id).all()
    )
    return {
        "entree_id": entree.id,
        "amount": cents(entree.amount),
        "available": cents(entree.amount - entree_allocated(db, entree.id)),
        "open_claims": open_claims,
        "allocations": [
            {"id": a.id, "claim_id": a.claim_id, "amount": cents(a.amount), "debtor": a.claim.debtor} for a in allocations
        ],
    }
