from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.holdings import SELL_TYPES, is_trade, rebuild_holdings, trade_cutoff
from app.db.session import get_db
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.investment_transaction import InvestmentTransaction
from app.schemas.investment import InvestmentTransactionCreate, InvestmentTransactionRead, InvestmentTransactionUpdate

router = APIRouter(prefix="/investment-transactions", tags=["investment-transactions"])

VALID_TYPES = {"versement", "retrait", "dividende", "achat", "vente", "frais"}
TRADE_FIELDS = {"type", "date", "ticker", "quantity", "unit_price", "price_currency", "fees"}
TYPE_ERROR = "Investment transaction type must be one of: " + ", ".join(sorted(VALID_TYPES))


def _check_trade(db: Session, account_id: int, tx_type: str, date: datetime, ticker: str | None, quantity: float | None) -> None:
    """Un achat/une vente exige un titre et une quantité, et ne peut précéder l'inventaire Point Zéro."""
    if tx_type in {"achat", "vente"} and (not ticker or not quantity or quantity <= 0):
        raise HTTPException(status_code=422, detail="Un achat ou une vente exige un titre (ticker) et une quantité > 0")
    if not is_trade(tx_type, ticker, quantity):
        return
    cutoff = trade_cutoff(db, account_id, ticker)
    if cutoff and date <= cutoff:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Opération sur {ticker.upper()} antérieure au Point Zéro des positions ({cutoff:%d/%m/%Y %H:%M}) : "
                "elle est déjà couverte par l'inventaire, modifie plutôt l'inventaire du Point Zéro"
            ),
        )


def _derive_unit_price(tx: InvestmentTransaction) -> None:
    """Sans prix unitaire, on le déduit du montant (frais exclus) dans la devise de saisie."""
    if tx.unit_price or not is_trade(tx.type, tx.ticker, tx.quantity):
        return
    fees = tx.fees or 0.0
    gross = tx.original_amount + fees if tx.type in SELL_TYPES else tx.original_amount - fees
    if gross > 0:
        tx.unit_price = round(gross / tx.quantity, 6)
        tx.price_currency = tx.currency


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
    if tx_type not in VALID_TYPES:
        raise HTTPException(status_code=422, detail=TYPE_ERROR)
    _check_trade(db, payload.account_id, tx_type, payload.date, payload.ticker, payload.quantity)

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
        price_currency=(payload.price_currency or (currency if payload.unit_price else None) or "").upper() or None,
        fees=payload.fees,
        etf_profile_id=payload.etf_profile_id,
    )
    _derive_unit_price(tx)
    db.add(tx)

    from app.core.time import utcnow_naive
    account.last_verified_at = utcnow_naive()

    db.flush()
    await rebuild_holdings(db, payload.account_id)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{transaction_id}", status_code=204)
async def delete_investment_transaction(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(InvestmentTransaction).filter(InvestmentTransaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Investment transaction not found")
    account_id = tx.account_id
    from app.models.transaction import Transaction
    for linked in db.query(Transaction).filter(Transaction.linked_investment_transaction_id == tx.id).all():
        linked.linked_investment_transaction_id = None
        linked.is_transfer = False
    db.delete(tx)
    db.flush()
    await rebuild_holdings(db, account_id)
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
        if tx_type not in VALID_TYPES:
            raise HTTPException(status_code=422, detail=TYPE_ERROR)
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

    # Modifier la partie « titre » d'une opération couverte par le Point Zéro n'aurait aucun effet sur les
    # positions : on refuse, pour l'ancienne comme pour la nouvelle version (la note reste modifiable).
    if TRADE_FIELDS & data.keys():
        _check_trade(db, tx.account_id, tx.type, tx.date, tx.ticker, tx.quantity)
        _check_trade(
            db,
            tx.account_id,
            data.get("type", tx.type),
            new_date,
            data.get("ticker", tx.ticker),
            data.get("quantity", tx.quantity),
        )

    for key, value in data.items():
        setattr(tx, key, value)
    if tx.ticker:
        tx.ticker = tx.ticker.upper().strip()
    if tx.price_currency:
        tx.price_currency = tx.price_currency.upper()
    _derive_unit_price(tx)

    db.flush()
    await rebuild_holdings(db, tx.account_id)
    db.commit()
    db.refresh(tx)
    return tx
