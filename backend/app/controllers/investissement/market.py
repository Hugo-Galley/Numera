from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.investissement.market import quotes, search

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/search")
async def market_search(
    q: Optional[str] = Query(default=None, description="ISIN, ticker or asset name"),
    query: Optional[str] = Query(default=None, description="ISIN, ticker or asset name"),
    db: Session = Depends(get_db),
):
    """
    Search for market assets by ISIN code, Ticker symbol or Name.
    Returns matched ETF profiles and stocks with quotes.
    """
    search_str = (q or query or "").strip()
    if not search_str:
        return []
    return await search.search_market_assets(search_str, db=db)


@router.get("/validate")
async def market_validate(
    symbol_or_isin: str = Query(..., min_length=1, description="Ticker symbol or ISIN to validate"),
    db: Session = Depends(get_db),
):
    """
    Validates if a symbol or ISIN exists and returns real-time verification details.
    """
    return await search.validate_symbol(db, symbol_or_isin)


@router.get("/quote")
async def market_quote(
    symbols: str = Query(..., description="Comma-separated list of symbols (e.g. CW8.PA,AAPL)"),
):
    """
    Get live market quotes and converted EUR prices for given symbols.
    """
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    return await quotes.get_market_quotes(sym_list)
