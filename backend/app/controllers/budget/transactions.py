from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.budget.transactions import TransactionFilters
from app.services.budget import transaction_links as links
from app.services.budget import transaction_writes as writes
from app.services.budget import transactions as service
from app.schemas.transaction import TransferCandidate, TransferCounterpartCreate, TransferCounterpartRead, TransactionCreate, TransactionRead, TransactionUpdate, TransactionBulkDelete, TransactionBulkDeleteResult, TransactionBulkUpdate, TransactionSplitsUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/merchants", response_model=list[str])
def list_merchants(db: Session = Depends(get_db)):
    return service.list_merchants(db)


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    account_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    type: str | None = Query(default=None),
    merchant: str | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    min_amount: float | None = Query(default=None),
    max_amount: float | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    is_transfer: bool | None = Query(default=None),
    tag_ids: list[int] | None = Query(default=None),
    search: str | None = Query(default=None),
    uncategorized: bool = Query(default=False),
    merchant_name: str | None = Query(default=None, description="Nom canonique exact (marchand normalisé, sinon libellé)"),
    period: bool = Query(default=False, description="month/year = mois de paie (comme les analytics) au lieu du mois civil"),
    budget_scope: bool = Query(default=False, description="Périmètre des flux du budget : courant/épargne hors tickets restaurant"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    filters = TransactionFilters(
        account_id=account_id, category_id=category_id, type=type, merchant=merchant, month=month, year=year,
        min_amount=min_amount, max_amount=max_amount, start_date=start_date, end_date=end_date,
        is_transfer=is_transfer, tag_ids=tag_ids, search=search, uncategorized=uncategorized,
        merchant_name=merchant_name, period=period, budget_scope=budget_scope,
    )
    return service.list_transactions(db, filters, skip, limit)


@router.get("/potential-transfers")
async def find_potential_transfers(
    days_tolerance: int = Query(default=5, ge=0, le=30),
    amount_tolerance_pct: float = Query(default=1.0, ge=0, le=50),
    months: int = Query(default=0, ge=0, le=240, description="0 = tout l'historique"),
    db: Session = Depends(get_db)
):
    """Suggestions de virements internes (appariement 1 pour 1, égalités marquées `ambiguous`)."""
    return await service.find_potential_transfers(db, days_tolerance, amount_tolerance_pct, months)


@router.get("/{transaction_id}/transfer-candidates", response_model=list[TransferCandidate])
async def transfer_candidates(
    transaction_id: int,
    days: int = Query(default=15, ge=0, le=60),
    amount_tolerance_pct: float = Query(default=5.0, ge=0, le=100),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Candidates classées pour relier cette ligne à un virement interne (liaison manuelle)."""
    return await service.transfer_candidates(db, transaction_id, days, amount_tolerance_pct, account_id)


@router.post("/{transaction_id}/transfer-counterpart", response_model=TransferCounterpartRead, status_code=201)
async def create_transfer_counterpart(
    transaction_id: int, payload: TransferCounterpartCreate, db: Session = Depends(get_db)
):
    """Crée la contrepartie manquante d'une sortie sur un autre compte et la relie."""
    return await links.create_transfer_counterpart(db, transaction_id, payload)


@router.post("/{transaction_id}/link/{other_id}")
def link_transactions(
    transaction_id: int,
    other_id: int,
    type: str = Query(default="regular"),
    db: Session = Depends(get_db)
):
    return links.link_transactions(db, transaction_id, other_id, type)


@router.post("/{transaction_id}/ignore", status_code=204)
def ignore_transfer(
    transaction_id: int,
    other_id: int | None = Query(default=None),
    type: str = Query(default="regular"),
    db: Session = Depends(get_db),
):
    """Écarte une suggestion de virement. Avec `other_id`, la ligne en face est écartée aussi."""
    links.ignore_transfer(db, transaction_id, other_id, type)


@router.post("/{transaction_id}/ignore-duplicate", status_code=204)
def ignore_duplicate(transaction_id: int, db: Session = Depends(get_db)):
    links.ignore_duplicate(db, transaction_id)


@router.post("/{transaction_id}/unlink", response_model=TransactionRead)
def unlink_transaction(transaction_id: int, db: Session = Depends(get_db)):
    return links.unlink_transaction(db, transaction_id)


@router.post("", response_model=TransactionRead, status_code=201)
async def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    return await writes.create_transaction(db, payload)


@router.patch("/bulk", status_code=204)
async def bulk_update_transactions(payload: TransactionBulkUpdate, db: Session = Depends(get_db)):
    await writes.bulk_update_transactions(db, payload)


@router.post("/bulk-delete", response_model=TransactionBulkDeleteResult)
def bulk_delete_transactions(payload: TransactionBulkDelete, db: Session = Depends(get_db)):
    """Supprime plusieurs transactions dans une seule transaction SQL, puis recalcule les soldes."""
    return writes.bulk_delete_transactions(db, payload)


@router.put("/{transaction_id}/splits", response_model=TransactionRead)
def update_transaction_splits(transaction_id: int, payload: TransactionSplitsUpdate, db: Session = Depends(get_db)):
    """Découpe une dépense entre plusieurs catégories (liste vide = annuler le découpage)."""
    return writes.update_transaction_splits(db, transaction_id, payload)


@router.patch("/{transaction_id}", response_model=TransactionRead)
async def update_transaction(transaction_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)):
    return await writes.update_transaction(db, transaction_id, payload)


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    writes.delete_transaction(db, transaction_id)
