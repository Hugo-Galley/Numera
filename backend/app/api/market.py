from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.market_data import search_market_assets, get_market_quotes

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/search")
async def market_search(
    q: str = Query(..., min_length=1, description="ISIN, ticker or asset name"),
    db: Session = Depends(get_db),
):
    """
    Search for market assets by ISIN code, Ticker symbol or Name.
    Returns matched ETF profiles and stocks with quotes.
    """
    return await search_market_assets(q, db=db)


@router.get("/quote")
async def market_quote(
    symbols: str = Query(..., description="Comma-separated list of symbols (e.g. CW8.PA,AAPL)"),
):
    """
    Get live market quotes and converted EUR prices for given symbols.
    """
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    return await get_market_quotes(sym_list)
