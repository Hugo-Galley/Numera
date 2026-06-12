from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.finance import apply_transaction_to_balance, month_label_from_date, normalize_transaction_type
from app.db.session import get_db
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate, TransactionBulkUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


def recalculate_running_balances(db: Session, account_id: int):
    """Recalculate running balances for all transactions of an account in chronological order."""
    transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
    
    current_balance = 0.0
    for tx in transactions:
        current_balance = apply_transaction_to_balance(current_balance, tx.type, tx.amount)
        tx.running_balance = current_balance
    
    db.commit()


@router.get("/merchants", response_model=list[str])
def list_merchants(db: Session = Depends(get_db)):
    merchants = (
        db.query(Transaction.merchant)
        .distinct()
        .order_by(Transaction.merchant.asc())
        .all()
    )
    return [m[0] for m in merchants if m[0]]


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
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Transaction)
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if type is not None:
        query = query.filter(Transaction.type == type)
    if merchant is not None:
        query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)
    if start_date is not None:
        query = query.filter(Transaction.date >= start_date)
    if end_date is not None:
        query = query.filter(Transaction.date <= end_date)
    if is_transfer is not None:
        query = query.filter(Transaction.is_transfer == is_transfer)
    if tag_ids:
        from app.models.tag import Tag
        query = query.join(Transaction.tags).filter(Tag.id.in_(tag_ids))
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.merchant.ilike(search_filter),
                Transaction.note.ilike(search_filter)
            )
        )
    if month is not None and year is not None:
        start = datetime(year, month, 1)
        end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
        query = query.filter(and_(
            Transaction.date >= start,
            Transaction.date < end,
        ))
    
    # Order by date desc for better UX in lists, unless searching for specific time range
    return query.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit).all()


@router.get("/potential-transfers")
async def find_potential_transfers(
    days_tolerance: int = Query(default=3, ge=0, le=14),
    amount_tolerance_pct: float = Query(default=0.01, ge=0, le=10),
    db: Session = Depends(get_db)
):
    """
    Find pairs of transactions that could be internal transfers.
    A potential transfer is a Sortie from one account and an Entree (or versement) to another account
    with similar amounts and close dates.
    """
    from app.core.currency import get_exchange_rates
    from app.models.investment_transaction import InvestmentTransaction

    # Get all unlinked Sortie transactions from the last 6 months
    six_months_ago = datetime.now() - timedelta(days=180)
    sorties = (
        db.query(Transaction)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            Transaction.is_transfer_ignored == False,
            Transaction.linked_transaction_id == None,
            Transaction.linked_investment_transaction_id == None,
            Transaction.date >= six_months_ago
        )
        .all()
    )

    potential_pairs = []
    rates = await get_exchange_rates("EUR")

    for sortie in sorties:
        start_date = sortie.date - timedelta(days=days_tolerance)
        end_date = sortie.date + timedelta(days=days_tolerance)
        
        amount_eur = sortie.amount / rates.get(sortie.currency, 1.0)
        min_amount_eur = amount_eur * (1 - amount_tolerance_pct / 100.0)
        max_amount_eur = amount_eur * (1 + amount_tolerance_pct / 100.0)

        # 1. Look for regular Entrees
        candidates = (
            db.query(Transaction)
            .filter(
                Transaction.type == "Entree",
                Transaction.account_id != sortie.account_id,
                Transaction.is_transfer == False,
                Transaction.is_transfer_ignored == False,
                Transaction.linked_transaction_id == None,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
            .all()
        )

        for entree in candidates:
            entree_eur = entree.amount / rates.get(entree.currency, 1.0)
            diff_pct = abs(entree_eur - amount_eur) / max(amount_eur, 1.0) * 100.0
            if diff_pct <= amount_tolerance_pct:
                potential_pairs.append({
                    "sortie": sortie,
                    "entree": entree,
                    "type": "regular",
                    "confidence": "high" if diff_pct < 0.001 else "medium"
                })

        # 2. Look for Investment Versements
        itx_candidates = (
            db.query(InvestmentTransaction)
            .filter(
                InvestmentTransaction.type == "versement",
                InvestmentTransaction.account_id != sortie.account_id,
                InvestmentTransaction.is_transfer == False,
                InvestmentTransaction.is_transfer_ignored == False,
                InvestmentTransaction.linked_transaction_id == None,
                InvestmentTransaction.date >= start_date,
                InvestmentTransaction.date <= end_date
            )
            .all()
        )

        for itx in itx_candidates:
            itx_eur = itx.amount / rates.get(itx.currency, 1.0)
            diff_pct = abs(itx_eur - amount_eur) / max(amount_eur, 1.0) * 100.0
            if diff_pct <= amount_tolerance_pct:
                potential_pairs.append({
                    "sortie": sortie,
                    "entree": itx,
                    "type": "investment",
                    "confidence": "high" if diff_pct < 0.001 else "medium"
                })

    return potential_pairs


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
        
    if type == "regular":
        tx2 = db.query(Transaction).filter(Transaction.id == other_id).first()
        if not tx2:
            raise HTTPException(status_code=404, detail="Secondary transaction not found")
        
        tx1.linked_transaction_id = tx2.id
        tx2.linked_transaction_id = tx1.id
        tx2.is_transfer = True
    else:
        tx2 = db.query(InvestmentTransaction).filter(InvestmentTransaction.id == other_id).first()
        if not tx2:
            raise HTTPException(status_code=404, detail="Investment transaction not found")
            
        tx1.linked_investment_transaction_id = tx2.id
        tx2.linked_transaction_id = tx1.id
        tx2.is_transfer = True
    
    tx1.is_transfer = True
    db.commit()
    return {"status": "ok"}


@router.post("/{transaction_id}/ignore", status_code=204)
def ignore_transfer(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tx.is_transfer_ignored = True
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
    from app.models.investment_transaction import InvestmentTransaction

    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    if tx.linked_transaction_id:
        other = db.query(Transaction).filter(Transaction.id == tx.linked_transaction_id).first()
        if other:
            other.linked_transaction_id = None
            other.is_transfer = False
            
    if tx.linked_investment_transaction_id:
        other_inv = db.query(InvestmentTransaction).filter(InvestmentTransaction.id == tx.linked_investment_transaction_id).first()
        if other_inv:
            other_inv.linked_transaction_id = None
            other_inv.is_transfer = False

    tx.linked_transaction_id = None
    tx.linked_investment_transaction_id = None
    tx.is_transfer = False
    
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
        existing_initial = db.query(Transaction).filter(
            Transaction.account_id == payload.account_id,
            Transaction.type == "Solde Initial",
        ).first()
        if existing_initial:
            raise HTTPException(status_code=422, detail="A Solde Initial already exists for this account")
        earliest = (
            db.query(Transaction)
            .filter(Transaction.account_id == payload.account_id)
            .order_by(Transaction.date.asc(), Transaction.id.asc())
            .first()
        )
        if earliest and payload.date >= earliest.date:
            raise HTTPException(status_code=422, detail="Solde Initial must be the chronologically first transaction")

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
    )

    if payload.tag_ids:
        from app.models.tag import Tag
        tags = db.query(Tag).filter(Tag.id.in_(payload.tag_ids)).all()
        transaction.tags = tags

    db.add(transaction)
    db.commit()
    
    recalculate_running_balances(db, payload.account_id)
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
    
    tags = []
    if payload.tag_ids is not None:
        from app.models.tag import Tag
        tags = db.query(Tag).filter(Tag.id.in_(payload.tag_ids)).all()

    for tx in transactions:
        if payload.category_id is not None:
            tx.category_id = payload.category_id
        if payload.is_recurring is not None:
            tx.is_recurring = payload.is_recurring
        if payload.type is not None:
            try:
                tx.type = normalize_transaction_type(payload.type)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        if payload.merchant is not None:
            tx.merchant = payload.merchant
        if payload.tag_ids is not None:
            tx.tags = tags
        affected_account_ids.add(tx.account_id)

    db.commit()

    # Recalculate balances for all affected accounts
    for account_id in affected_account_ids:
        recalculate_running_balances(db, account_id)


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

    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    recalculate_running_balances(db, transaction.account_id)
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    account_id = transaction.account_id
    db.delete(transaction)
    db.commit()
    
    recalculate_running_balances(db, account_id)
