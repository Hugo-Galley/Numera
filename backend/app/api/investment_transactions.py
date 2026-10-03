from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.holdings import apply_trade_to_holding, reverse_trade_from_holding
from app.db.session import get_db
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.investment_transaction import InvestmentTransaction
from app.schemas.investment import InvestmentTransactionCreate, InvestmentTransactionRead, InvestmentTransactionUpdate

router = APIRouter(prefix="/investment-transactions", tags=["investment-transactions"])


@router.get("", response_model=list[InvestmentTransactionRead])
def list_investment_transactions(
    account_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int | None = Query(default=None, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(InvestmentTransaction)
    if account_id is not None:
        query = query.filter(InvestmentTransaction.account_id == account_id)
    query = query.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


@router.post("", response_model=InvestmentTransactionRead, status_code=201)
async def create_investment_transaction(payload: InvestmentTransactionCreate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == payload.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.type not in {"investissement", "assurance_vie"}:
        raise HTTPException(status_code=422, detail="Account must be of type investissement or assurance_vie")

    tx_type = payload.type.strip().lower()
    if tx_type not in {"versement", "retrait", "dividende"}:
        raise HTTPException(status_code=422, detail="Investment transaction type must be versement, retrait or dividende")

    active_zero_point = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == payload.account_id, BalanceSnapshot.is_zero_point.is_(True))
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )
    if active_zero_point and payload.date < active_zero_point.date:
        raise HTTPException(
            status_code=422,
            detail="Transaction date cannot be before active zero point",
        )

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

    tx = InvestmentTransaction(
        account_id=payload.account_id,
        date=payload.date,
        type=tx_type,
        amount=converted_amount,
        currency=currency,
        original_amount=original_amount,
        note=payload.note,
        asset_class=payload.asset_class,
        sector=payload.sector,
        geographic_zone=payload.geographic_zone,
        ticker=payload.ticker.upper().strip() if payload.ticker else None,
        isin=payload.isin.upper().strip() if payload.isin else None,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        etf_profile_id=payload.etf_profile_id,
    )
    db.add(tx)

    apply_trade_to_holding(
        db,
        account_id=payload.account_id,
        ticker=payload.ticker,
        tx_type=tx_type,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        isin=payload.isin,
        asset_name=payload.note,
        currency=currency,
        etf_profile_id=payload.etf_profile_id,
    )

    from app.core.time import utcnow_naive
    account.last_verified_at = utcnow_naive()
    
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{transaction_id}", status_code=204)
def delete_investment_transaction(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(InvestmentTransaction).filter(InvestmentTransaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Investment transaction not found")
    reverse_trade_from_holding(
        db,
        account_id=tx.account_id,
        ticker=tx.ticker,
        tx_type=tx.type,
        quantity=tx.quantity,
        unit_price=tx.unit_price,
    )
    from app.models.transaction import Transaction
    for linked in db.query(Transaction).filter(Transaction.linked_investment_transaction_id == tx.id).all():
        linked.linked_investment_transaction_id = None
        linked.is_transfer = False
    db.delete(tx)
    db.commit()


@router.patch("/{transaction_id}", response_model=InvestmentTransactionRead)
async def update_investment_transaction(transaction_id: int, payload: InvestmentTransactionUpdate, db: Session = Depends(get_db)):
    tx = db.query(InvestmentTransaction).filter(InvestmentTransaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Investment transaction not found")

    account = db.query(Account).filter(Account.id == tx.account_id).first()

    data = payload.model_dump(exclude_unset=True)
    if "type" in data and data["type"] is not None:
        tx_type = data["type"].strip().lower()
        if tx_type not in {"versement", "retrait", "dividende"}:
            raise HTTPException(status_code=422, detail="Investment transaction type must be versement, retrait or dividende")
        data["type"] = tx_type

    active_zero_point = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == tx.account_id, BalanceSnapshot.is_zero_point.is_(True))
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )
    new_date = data.get("date", tx.date)
    if active_zero_point and new_date < active_zero_point.date:
        raise HTTPException(
            status_code=422,
            detail="Transaction date cannot be before active zero point",
        )

    # Handle currency conversion if amount or currency or date changed
    if "amount" in data or "currency" in data or "date" in data:
        from app.core.currency import convert_amount
        
        original_amount = data.get("amount", tx.original_amount)
        currency = data.get("currency", tx.currency)
        date = data.get("date", tx.date)
        
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
            
        data["amount"] = converted_amount
        data["original_amount"] = original_amount
        data["currency"] = currency

    # La position reflète le mouvement : on annule l'ancien, on applique le nouveau
    reverse_trade_from_holding(
        db,
        account_id=tx.account_id,
        ticker=tx.ticker,
        tx_type=tx.type,
        quantity=tx.quantity,
        unit_price=tx.unit_price,
    )

    for key, value in data.items():
        setattr(tx, key, value)
    if tx.ticker:
        tx.ticker = tx.ticker.upper().strip()

    apply_trade_to_holding(
        db,
        account_id=tx.account_id,
        ticker=tx.ticker,
        tx_type=tx.type,
        quantity=tx.quantity,
        unit_price=tx.unit_price,
        isin=tx.isin,
        asset_name=tx.note,
        currency=tx.currency,
        etf_profile_id=tx.etf_profile_id,
    )

    db.commit()
    db.refresh(tx)
    return tx
