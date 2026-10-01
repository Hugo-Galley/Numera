from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.market_data import search_market_assets, get_market_quotes

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
    return await search_market_assets(search_str, db=db)


@router.get("/validate")
async def market_validate(
    symbol_or_isin: str = Query(..., min_length=1, description="Ticker symbol or ISIN to validate"),
    db: Session = Depends(get_db),
):
    """
    Validates if a symbol or ISIN exists and returns real-time verification details.
    """
    term = symbol_or_isin.strip()
    if not term:
        return {
            "valid": False,
            "symbol": "",
            "name": None,
            "isin": None,
            "type": None,
            "currency": "EUR",
            "price": None,
            "price_eur": None,
            "etf_profile_id": None,
        }

    assets = await search_market_assets(term, db=db)
    match = None
    for a in assets:
        if a["symbol"].upper() == term.upper() or (a.get("isin") and a["isin"].upper() == term.upper()):
            match = a
            break
    if not match and assets:
        first = assets[0]
        if term.upper() in first["symbol"].upper() or (first.get("isin") and term.upper() == first["isin"].upper()):
            match = first

    if match:
        quote_data = await get_market_quotes([match["symbol"]])
        q_info = quote_data.get(match["symbol"].upper(), {})
        return {
            "valid": True,
            "symbol": match["symbol"],
            "name": match["name"],
            "isin": match.get("isin"),
            "type": match.get("type", "EQUITY"),
            "currency": q_info.get("currency") or match.get("currency", "EUR"),
            "price": q_info.get("price") if q_info.get("type") != "UNKNOWN" else None,
            "price_eur": q_info.get("price_eur") if q_info.get("type") != "UNKNOWN" else None,
            "etf_profile_id": match.get("etf_profile_id"),
        }

    quotes = await get_market_quotes([term])
    if term.upper() in quotes:
        q_info = quotes[term.upper()]
        if q_info.get("type") != "UNKNOWN" and (q_info.get("price") or 0) > 0:
            return {
                "valid": True,
                "symbol": term.upper(),
                "name": q_info.get("name", term.upper()),
                "isin": None,
                "type": q_info.get("type", "EQUITY"),
                "currency": q_info.get("currency", "EUR"),
                "price": q_info.get("price"),
                "price_eur": q_info.get("price_eur"),
                "etf_profile_id": None,
            }

    return {
        "valid": False,
        "symbol": term.upper(),
        "name": None,
        "isin": None,
        "type": None,
        "currency": "EUR",
        "price": None,
        "price_eur": None,
        "etf_profile_id": None,
    }


@router.get("/quote")
async def market_quote(
    symbols: str = Query(..., description="Comma-separated list of symbols (e.g. CW8.PA,AAPL)"),
):
    """
    Get live market quotes and converted EUR prices for given symbols.
    """
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    return await get_market_quotes(sym_list)
