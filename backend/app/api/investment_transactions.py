from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.dividends import match_dividend_ticker, sync_reinvestment
from app.core.holdings import SELL_TYPES, is_trade, rebuild_holdings, trade_cutoff
from app.db.session import get_db
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.schemas.investment import InvestmentTransactionCreate, InvestmentTransactionRead, InvestmentTransactionUpdate

router = APIRouter(prefix="/investment-transactions", tags=["investment-transactions"])

VALID_TYPES = {"versement", "retrait", "dividende", "achat", "vente", "frais"}
TRADE_FIELDS = {"type", "date", "ticker", "quantity", "unit_price", "price_currency", "fees"}
DIVIDEND_FIELDS = {"type", "date", "ticker", "quantity", "amount", "currency", "reinvested"}
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


def _check_dividend(db: Session, account_id: int, *, tx_type: str, date: datetime, ticker: str | None,
                    quantity: float | None, reinvested: bool, withholding_tax: float | None) -> None:
    """Retenue et réinvestissement n'existent que pour un dividende ; réinvestir exige titre + parts reçues."""
    if tx_type != "dividende":
        if reinvested or withholding_tax:
            raise HTTPException(status_code=422, detail="Retenue à la source et réinvestissement ne concernent que les dividendes")
        return
    if reinvested:
        if not ticker or not quantity or quantity <= 0:
            raise HTTPException(status_code=422, detail="Un dividende réinvesti exige un titre et le nombre de parts reçues")
        _check_trade(db, account_id, "achat", date, ticker, quantity)


def _flag_distributing(db: Session, account_id: int, ticker: str | None) -> None:
    """Un dividende saisi sur une position la marque comme distribuante (si non renseigné)."""
    if not ticker:
        return
    holding = db.query(PortfolioHolding).filter(
        PortfolioHolding.account_id == account_id, PortfolioHolding.ticker == ticker.upper().strip()
    ).first()
    if holding is not None and holding.pays_dividends is None:
        holding.pays_dividends = True


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


@router.post("/link-dividends")
def link_dividends(
    account_id: int = Query(...),
    dry_run: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    """
    Rattache les dividendes sans titre d'un compte à une de ses positions, d'après leur libellé
    (« Dividende Apple » → AAPL). `dry_run=true` (défaut) se contente de proposer ; les libellés
    ambigus ou inconnus restent non rattachés.
    """
    if not db.query(Account.id).filter(Account.id == account_id).first():
        raise HTTPException(status_code=404, detail="Account not found")

    candidates: dict[str, str] = {}
    for h in db.query(PortfolioHolding).filter(PortfolioHolding.account_id == account_id).all():
        candidates[h.ticker] = h.asset_name
    for b in db.query(HoldingBaselineItem).filter(HoldingBaselineItem.account_id == account_id).all():
        candidates.setdefault(b.ticker, b.asset_name)
    for ticker, name in (
        db.query(InvestmentTransaction.ticker, InvestmentTransaction.note)
        .filter(InvestmentTransaction.account_id == account_id, InvestmentTransaction.ticker.isnot(None))
        .distinct()
        .all()
    ):
        candidates.setdefault(ticker, name or ticker)

    pending = (
        db.query(InvestmentTransaction)
        .filter(
            InvestmentTransaction.account_id == account_id,
            InvestmentTransaction.type == "dividende",
            InvestmentTransaction.ticker.is_(None),
        )
        .order_by(InvestmentTransaction.date.asc())
        .all()
    )
    matched, unmatched = [], []
    for tx in pending:
        ticker = match_dividend_ticker(tx.note, list(candidates.items()))
        entry = {"id": tx.id, "date": tx.date.isoformat(), "note": tx.note, "amount": tx.amount, "currency": tx.currency}
        if ticker:
            matched.append({**entry, "ticker": ticker})
            if not dry_run:
                tx.ticker = ticker
        else:
            unmatched.append(entry)

    if not dry_run and matched:
        for ticker in {m["ticker"] for m in matched}:
            _flag_distributing(db, account_id, ticker)
        db.commit()
    return {"applied": not dry_run, "matched": matched, "unmatched": unmatched}


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
    if tx_type == "dividende" and not payload.ticker:
        raise HTTPException(status_code=422, detail="Un dividende doit être rattaché à un titre (ticker)")
    _check_dividend(
        db, payload.account_id, tx_type=tx_type, date=payload.date, ticker=payload.ticker,
        quantity=payload.quantity, reinvested=payload.reinvested, withholding_tax=payload.withholding_tax,
    )

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
        withholding_tax=payload.withholding_tax,
        reinvested=payload.reinvested,
        etf_profile_id=payload.etf_profile_id,
    )
    _derive_unit_price(tx)
    db.add(tx)

    from app.core.time import utcnow_naive
    account.last_verified_at = utcnow_naive()

    db.flush()
    if tx_type == "dividende":
        sync_reinvestment(db, tx)
    await rebuild_holdings(db, payload.account_id)
    if tx_type == "dividende":
        _flag_distributing(db, payload.account_id, tx.ticker)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{transaction_id}", status_code=204)
async def delete_investment_transaction(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(InvestmentTransaction).filter(InvestmentTransaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Investment transaction not found")
    if tx.reinvest_of_id is not None:
        raise HTTPException(status_code=409, detail="Cet achat vient d'un dividende réinvesti : modifie ou supprime le dividende")
    account_id = tx.account_id
    db.query(InvestmentTransaction).filter(InvestmentTransaction.reinvest_of_id == tx.id).delete()
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

    if tx.reinvest_of_id is not None:
        raise HTTPException(status_code=409, detail="Cet achat vient d'un dividende réinvesti : modifie le dividende")
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

    new_type = data.get("type", tx.type)
    if new_type != "dividende":
        # Hors dividende, ces champs n'ont plus de sens : on les remet à zéro (l'achat lié sera supprimé)
        data["reinvested"], data["withholding_tax"] = False, None
    if DIVIDEND_FIELDS & data.keys():
        # Pas de contrôle sur une simple retouche de libellé (ex. dividende réinvesti antérieur à un nouveau Point Zéro)
        _check_dividend(
            db, tx.account_id, tx_type=new_type, date=new_date,
            ticker=data.get("ticker", tx.ticker), quantity=data.get("quantity", tx.quantity),
            reinvested=bool(data.get("reinvested", tx.reinvested)),
            withholding_tax=data.get("withholding_tax", tx.withholding_tax),
        )

    for key, value in data.items():
        setattr(tx, key, value)
    if tx.ticker:
        tx.ticker = tx.ticker.upper().strip()
    if tx.price_currency:
        tx.price_currency = tx.price_currency.upper()
    _derive_unit_price(tx)

    db.flush()
    if DIVIDEND_FIELDS & data.keys():
        sync_reinvestment(db, tx)
    await rebuild_holdings(db, tx.account_id)
    if tx.type == "dividende":
        _flag_distributing(db, tx.account_id, tx.ticker)
    db.commit()
    db.refresh(tx)
    return tx
