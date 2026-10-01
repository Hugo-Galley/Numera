from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account import Account
from app.models.portfolio_holding import PortfolioHolding
from app.models.etf_profile import EtfProfile
from app.schemas.holding import (
    PortfolioHoldingCreate,
    PortfolioHoldingRead,
    PortfolioHoldingUpdate,
    BaselineInventoryRequest,
)
from app.core.market_data import get_market_quotes, suggest_holdings_from_notes

router = APIRouter(prefix="/holdings", tags=["holdings"])


async def _enrich_holding_with_quote(holding: PortfolioHolding, quotes: dict) -> PortfolioHoldingRead:
    sym = holding.ticker.upper().strip()
    quote = quotes.get(sym, {})
    price = quote.get("price", 0.0)
    price_eur = quote.get("price_eur", price)

    curr_val_eur = holding.quantity * price_eur if price_eur > 0 else 0.0
    tot_invested_eur = (holding.quantity * holding.buy_price_avg) if (holding.buy_price_avg and holding.buy_price_avg > 0) else None

    gain_eur = None
    gain_pct = None
    if tot_invested_eur is not None and tot_invested_eur > 0 and curr_val_eur > 0:
        gain_eur = round(curr_val_eur - tot_invested_eur, 2)
        gain_pct = round((gain_eur / tot_invested_eur) * 100.0, 2)

    return PortfolioHoldingRead(
        id=holding.id,
        account_id=holding.account_id,
        ticker=holding.ticker,
        isin=holding.isin,
        asset_name=holding.asset_name,
        quantity=holding.quantity,
        buy_price_avg=holding.buy_price_avg,
        currency=holding.currency,
        etf_profile_id=holding.etf_profile_id,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
        current_price=round(price, 4) if price > 0 else None,
        current_price_eur=round(price_eur, 4) if price_eur > 0 else None,
        current_value_eur=round(curr_val_eur, 2) if curr_val_eur > 0 else None,
        total_invested_eur=round(tot_invested_eur, 2) if tot_invested_eur is not None else None,
        gain_eur=gain_eur,
        gain_pct=gain_pct,
        is_etf=bool(holding.etf_profile_id or quote.get("type") == "ETF"),
    )


@router.get("", response_model=List[PortfolioHoldingRead])
async def list_holdings(
    account_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(PortfolioHolding)
    if account_id is not None:
        query = query.filter(PortfolioHolding.account_id == account_id)
    holdings = query.order_by(PortfolioHolding.id.asc()).all()

    # Pre-fetch live quotes for all tickers
    symbols = [h.ticker for h in holdings]
    quotes = await get_market_quotes(symbols)

    return [await _enrich_holding_with_quote(h, quotes) for h in holdings]


@router.get("/suggestions")
async def get_holding_suggestions(
    account_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """
    Suggests holdings for the Point Zéro baseline by analyzing historical transaction notes.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return await suggest_holdings_from_notes(db, account_id)


@router.post("/baseline", response_model=List[PortfolioHoldingRead])
async def set_baseline_inventory(
    payload: BaselineInventoryRequest,
    db: Session = Depends(get_db),
):
    """
    Point Zéro / État des Lieux initial:
    Sets the current inventory of holdings for an account without touching historical transactions.
    """
    account = db.query(Account).filter(Account.id == payload.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Clear existing holdings for this account
    db.query(PortfolioHolding).filter(PortfolioHolding.account_id == payload.account_id).delete()

    created_holdings = []
    for item in payload.holdings:
        if item.quantity <= 0:
            continue

        holding = PortfolioHolding(
            account_id=payload.account_id,
            ticker=item.ticker.upper().strip(),
            isin=item.isin.upper().strip() if item.isin else None,
            asset_name=item.asset_name.strip(),
            quantity=item.quantity,
            buy_price_avg=item.buy_price_avg,
            currency=item.currency.upper(),
            etf_profile_id=item.etf_profile_id,
        )
        db.add(holding)
        created_holdings.append(holding)

    db.commit()
    for h in created_holdings:
        db.refresh(h)

    symbols = [h.ticker for h in created_holdings]
    quotes = await get_market_quotes(symbols)
    return [await _enrich_holding_with_quote(h, quotes) for h in created_holdings]


@router.post("", response_model=PortfolioHoldingRead, status_code=201)
async def create_holding(
    payload: PortfolioHoldingCreate,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == payload.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    holding = PortfolioHolding(
        account_id=payload.account_id,
        ticker=payload.ticker.upper().strip(),
        isin=payload.isin.upper().strip() if payload.isin else None,
        asset_name=payload.asset_name.strip(),
        quantity=payload.quantity,
        buy_price_avg=payload.buy_price_avg,
        currency=payload.currency.upper(),
        etf_profile_id=payload.etf_profile_id,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)

    quotes = await get_market_quotes([holding.ticker])
    return await _enrich_holding_with_quote(holding, quotes)


@router.put("/{holding_id}", response_model=PortfolioHoldingRead)
async def update_holding(
    holding_id: int,
    payload: PortfolioHoldingUpdate,
    db: Session = Depends(get_db),
):
    holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    if payload.ticker is not None:
        holding.ticker = payload.ticker.upper().strip()
    if payload.isin is not None:
        holding.isin = payload.isin.upper().strip() if payload.isin else None
    if payload.asset_name is not None:
        holding.asset_name = payload.asset_name.strip()
    if payload.quantity is not None:
        holding.quantity = payload.quantity
    if payload.buy_price_avg is not None:
        holding.buy_price_avg = payload.buy_price_avg
    if payload.currency is not None:
        holding.currency = payload.currency.upper()
    if payload.etf_profile_id is not None:
        holding.etf_profile_id = payload.etf_profile_id

    db.commit()
    db.refresh(holding)

    quotes = await get_market_quotes([holding.ticker])
    return await _enrich_holding_with_quote(holding, quotes)


@router.delete("/{holding_id}", status_code=204)
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(holding)
    db.commit()
