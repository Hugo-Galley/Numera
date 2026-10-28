from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.services import reimbursements as remb
from app.services.splits import check_split_compatible, set_splits
from app.services.transfers import auto_link_transfers, create_counterpart, link_pair, release_partner, unlink_pair
from app.core.finance import month_label_from_date, normalize_transaction_type
from app.db.session import get_db
from app.repositories.transactions import TransactionFilters
from app.services import transactions as service
from app.services.balances import recalculate_running_balances
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transaction import TransferCandidate, TransferCounterpartCreate, TransferCounterpartRead, TransactionCreate, TransactionRead, TransactionUpdate, TransactionBulkDelete, TransactionBulkDeleteResult, TransactionBulkUpdate, TransactionSplitsUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


def validate_solde_initial(
    db: Session, account_id: int, date: datetime, exclude_id: int | None = None
) -> None:
    """Un compte n'a qu'un seul Solde Initial et il doit être la première transaction
    (il remet le solde à zéro à sa date, cf. apply_transaction_to_balance)."""
    existing_initial = db.query(Transaction).filter(
        Transaction.account_id == account_id,
        Transaction.type == "Solde Initial",
        Transaction.id != (exclude_id or -1),
    ).first()
    if existing_initial:
        raise HTTPException(status_code=422, detail="A Solde Initial already exists for this account")
    earliest = (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id, Transaction.id != (exclude_id or -1))
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .first()
    )
    if earliest and date >= earliest.date:
        raise HTTPException(status_code=422, detail="Solde Initial must be the chronologically first transaction")


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
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.type != "Sortie":
        raise HTTPException(status_code=422, detail="Only a Sortie can get a counterpart")
    if remb.has_reimbursement(db, tx.id):
        raise HTTPException(status_code=400, detail="Une transaction qui porte des remboursements ne peut pas être un virement interne")
    dest = db.query(Account).filter(Account.id == payload.account_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Account not found")
    if dest.id == tx.account_id:
        raise HTTPException(status_code=422, detail="Destination must be another account")

    leg, kind = await create_counterpart(db, tx, dest, date=payload.date, amount=payload.amount)
    db.commit()
    if kind == "regular":
        recalculate_running_balances(db, dest.id)
    return TransferCounterpartRead(id=leg.id, type=kind)


@router.post("/{transaction_id}/link/{other_id}")
def link_transactions(
    transaction_id: int,
    other_id: int,
    type: str = Query(default="regular"),
    db: Session = Depends(get_db)
):
    from app.models.investment_transaction import InvestmentTransaction

    tx1 = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx1:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if type not in ("regular", "investment"):
        raise HTTPException(status_code=422, detail="type must be 'regular' or 'investment'")
    if type == "regular" and other_id == transaction_id:
        raise HTTPException(status_code=422, detail="A transaction cannot be linked to itself")

    if type == "regular":
        other = db.query(Transaction).filter(Transaction.id == other_id).first()
        if not other:
            raise HTTPException(status_code=404, detail="Secondary transaction not found")
    else:
        other = db.query(InvestmentTransaction).filter(InvestmentTransaction.id == other_id).first()
        if not other:
            raise HTTPException(status_code=404, detail="Investment transaction not found")

    if remb.has_reimbursement(db, tx1.id) or (type == "regular" and remb.has_reimbursement(db, other.id)):
        raise HTTPException(status_code=400, detail="Une transaction qui porte des remboursements ne peut pas être un virement interne")
    link_pair(db, tx1, other, type, "manual")
    db.commit()
    return {"status": "ok"}


@router.post("/{transaction_id}/ignore", status_code=204)
def ignore_transfer(
    transaction_id: int,
    other_id: int | None = Query(default=None),
    type: str = Query(default="regular"),
    db: Session = Depends(get_db),
):
    """Écarte une suggestion de virement. Avec `other_id`, la ligne en face est écartée aussi."""
    from app.models.investment_transaction import InvestmentTransaction

    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.is_transfer_ignored = True
    if other_id is not None:
        model = InvestmentTransaction if type == "investment" else Transaction
        other = db.query(model).filter(model.id == other_id).first()
        if other:
            other.is_transfer_ignored = True
    db.commit()
    return


@router.post("/{transaction_id}/ignore-duplicate", status_code=204)
def ignore_duplicate(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.is_duplicate_ignored = True
    db.commit()
    return


@router.post("/{transaction_id}/unlink", response_model=TransactionRead)
def unlink_transaction(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    unlink_pair(db, tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.post("", response_model=TransactionRead, status_code=201)
async def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == payload.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        transaction_type = normalize_transaction_type(payload.type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if transaction_type == "Solde Initial":
        validate_solde_initial(db, payload.account_id, payload.date)

    # Handle currency conversion
    from app.core.currency import convert_amount
    
    original_amount = payload.amount
    currency = payload.currency or account.currency
    
    if currency != account.currency:
        converted_amount = await convert_amount(
            amount=original_amount,
            from_currency=currency,
            to_currency=account.currency,
            date=payload.date.date(),
            db=db
        )
    else:
        converted_amount = original_amount

    transaction = Transaction(
        account_id=payload.account_id,
        date=payload.date,
        month_label=month_label_from_date(payload.date),
        type=transaction_type,
        merchant=payload.merchant,
        category_id=payload.category_id,
        amount=converted_amount,
        currency=currency,
        original_amount=original_amount,
        running_balance=0.0, # Will be recalculated
        note=payload.note,
        is_exceptional=payload.is_exceptional and transaction_type == "Sortie",
        merchant_id=payload.merchant_id,
        is_recurring=payload.is_recurring,
        custom_icon=payload.custom_icon,
        custom_color=payload.custom_color,
    )

    if payload.tag_ids:
        from app.models.tag import Tag
        tags = db.query(Tag).filter(Tag.id.in_(payload.tag_ids)).all()
        transaction.tags = tags

    db.add(transaction)
    
    from app.core.time import utcnow_naive
    account.last_verified_at = utcnow_naive()
    
    db.commit()
    
    recalculate_running_balances(db, payload.account_id)
    await auto_link_transfers(db)
    db.refresh(transaction)
    return transaction


@router.patch("/bulk", status_code=204)
async def bulk_update_transactions(payload: TransactionBulkUpdate, db: Session = Depends(get_db)):
    if not payload.ids:
        return

    transactions = db.query(Transaction).filter(Transaction.id.in_(payload.ids)).all()
    if not transactions:
        return

    affected_account_ids = set()

    bulk_type = None
    if payload.type is not None:
        try:
            bulk_type = normalize_transaction_type(payload.type)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if bulk_type == "Solde Initial":
            raise HTTPException(status_code=422, detail="Solde Initial cannot be set through bulk update")
    if bulk_type is not None and any(tx.type == "Solde Initial" for tx in transactions):
        raise HTTPException(status_code=422, detail="A Solde Initial transaction cannot be bulk-retyped")
    if bulk_type is not None:
        for tx in transactions:
            remb.check_transaction_change(db, tx, bulk_type, tx.amount, False)
            check_split_compatible(tx, bulk_type, tx.amount, tx.is_transfer)

    tags = []
    if payload.tag_ids is not None:
        from app.models.tag import Tag
        tags = db.query(Tag).filter(Tag.id.in_(payload.tag_ids)).all()

    for tx in transactions:
        if payload.category_id is not None:
            tx.category_id = payload.category_id
            tx.splits = []  # recatégoriser en masse remplace le découpage
        if payload.is_recurring is not None:
            tx.is_recurring = payload.is_recurring
        if bulk_type is not None:
            tx.type = bulk_type
        if payload.merchant is not None:
            tx.merchant = payload.merchant
        if payload.merchant_id is not None:
            tx.merchant_id = payload.merchant_id
        if payload.tag_ids is not None:
            tx.tags = tags
        affected_account_ids.add(tx.account_id)

    db.commit()

    # Recalculate balances for all affected accounts
    for account_id in affected_account_ids:
        recalculate_running_balances(db, account_id)


@router.post("/bulk-delete", response_model=TransactionBulkDeleteResult)
def bulk_delete_transactions(payload: TransactionBulkDelete, db: Session = Depends(get_db)):
    """Supprime plusieurs transactions dans une seule transaction SQL, puis recalcule
    une fois les soldes de chaque compte (des DELETE parallèles se marchent dessus)."""
    transactions = db.query(Transaction).filter(Transaction.id.in_(payload.ids)).all()
    deleted_ids = {tx.id for tx in transactions}
    affected_account_ids = {tx.account_id for tx in transactions}
    others: set[int] = set()
    for tx in transactions:
        release_partner(db, tx)
        others |= remb.detach_before_delete(db, tx)
    # Les FK des bases migrées n'ont pas de ON DELETE SET NULL : les liens doivent être nuls en base avant les DELETE
    db.flush()
    for tx in transactions:
        db.delete(tx)
    remb.sync_offsets(db, others - deleted_ids)
    db.commit()

    for account_id in affected_account_ids:
        recalculate_running_balances(db, account_id)
    return TransactionBulkDeleteResult(deleted=len(transactions))


@router.put("/{transaction_id}/splits", response_model=TransactionRead)
def update_transaction_splits(transaction_id: int, payload: TransactionSplitsUpdate, db: Session = Depends(get_db)):
    """Découpe une dépense entre plusieurs catégories (liste vide = annuler le découpage)."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    set_splits(db, transaction, payload.items)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionRead)
async def update_transaction(transaction_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    account = db.query(Account).filter(Account.id == transaction.account_id).first()
    
    update_data = payload.model_dump(exclude_unset=True)
    
    if "type" in update_data:
        try:
            update_data["type"] = normalize_transaction_type(update_data["type"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    
    if "date" in update_data:
        update_data["month_label"] = month_label_from_date(update_data["date"])

    new_type = update_data.get("type", transaction.type)
    if new_type == "Solde Initial" and ("type" in update_data or "date" in update_data):
        validate_solde_initial(
            db, transaction.account_id, update_data.get("date", transaction.date), exclude_id=transaction.id
        )

    # Handle currency conversion if amount or currency or date changed
    if "amount" in update_data or "currency" in update_data or "date" in update_data:
        from app.core.currency import convert_amount
        
        original_amount = update_data.get("amount", transaction.original_amount)
        currency = update_data.get("currency", transaction.currency)
        date = update_data.get("date", transaction.date)
        
        if currency != account.currency:
            converted_amount = await convert_amount(
                amount=original_amount,
                from_currency=currency,
                to_currency=account.currency,
                date=date.date(),
                db=db
            )
        else:
            converted_amount = original_amount
            
        update_data["amount"] = converted_amount
        update_data["original_amount"] = original_amount
        update_data["currency"] = currency

    if "tag_ids" in update_data:
        from app.models.tag import Tag
        tag_ids = update_data.pop("tag_ids")
        if tag_ids is not None:
            tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
            transaction.tags = tags
        else:
            transaction.tags = []

    remb.check_transaction_change(
        db,
        transaction,
        update_data.get("type", transaction.type),
        update_data.get("amount", transaction.amount),
        bool(update_data.get("is_transfer")),
    )

    check_split_compatible(
        transaction,
        update_data.get("type", transaction.type),
        update_data.get("amount", transaction.amount),
        bool(update_data.get("is_transfer", transaction.is_transfer)),
    )
    if transaction.splits and "category_id" in update_data and update_data["category_id"] != transaction.category_id:
        transaction.splits = []  # choisir une seule catégorie annule le découpage

    # La colonne n'est pas nullable : un `null` explicite équivaut à « ne pas modifier »
    if update_data.get("is_exceptional", True) is None:
        update_data.pop("is_exceptional")

    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    recalculate_running_balances(db, transaction.account_id)
    await auto_link_transfers(db)
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    account_id = transaction.account_id
    # Le partenaire d'un virement ne doit pas rester marqué is_transfer sans lien
    release_partner(db, transaction)
    others = remb.detach_before_delete(db, transaction)
    db.flush()  # liens remis à NULL avant le DELETE (FK sans ON DELETE SET NULL en base migrée)
    db.delete(transaction)
    remb.sync_offsets(db, others)
    db.commit()
    
    recalculate_running_balances(db, account_id)
