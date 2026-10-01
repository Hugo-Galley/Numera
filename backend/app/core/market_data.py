import re
import json
import httpx
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.currency import get_exchange_rates
from app.models.etf_profile import EtfProfile
from app.models.investment_transaction import InvestmentTransaction

logger = get_logger(__name__)

# In-memory quote cache
# symbol -> {"price": float, "currency": str, "name": str, "type": str, "price_eur": float, "expires_at": datetime}
_QUOTES_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = timedelta(hours=1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def _match_etf_profile(db: Session, symbol: str, isin: Optional[str] = None, name: Optional[str] = None) -> Optional[EtfProfile]:
    """Find matching EtfProfile by ticker, isin or alias."""
    profiles = db.query(EtfProfile).all()
    norm_symbol = symbol.upper().strip()
    norm_isin = (isin or "").upper().strip()
    norm_name = (name or "").lower().strip()

    # Exact isin or ticker match
    for p in profiles:
        if norm_isin and p.isin and p.isin.upper() == norm_isin:
            return p
        if p.ticker.upper() == norm_symbol:
            return p
        
        # Check aliases
        try:
            aliases = json.loads(p.aliases)
            for alias in aliases:
                if alias.upper() in (norm_symbol, norm_symbol.split(".")[0], norm_isin):
                    return p
        except Exception:
            pass

    # Name-based heuristic
    for p in profiles:
        p_name = p.name.lower()
        if p_name in norm_name or norm_name in p_name:
            return p

    return None


async def search_market_assets(query: str, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """
    Search for market assets by ISIN code, Ticker symbol or Name.
    Combines local ETF profiles and Yahoo Finance public search.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    results: List[Dict[str, Any]] = []
    seen_symbols = set()

    # 1. Search in local ETF profiles first
    if db:
        profiles = db.query(EtfProfile).all()
        for p in profiles:
            p_name = p.name.lower()
            p_ticker = p.ticker.lower()
            p_isin = (p.isin or "").lower()
            q_lower = cleaned.lower()

            matches = (
                q_lower in p_name
                or q_lower == p_ticker
                or q_lower in p_ticker
                or (p_isin and q_lower == p_isin)
            )
            if not matches:
                try:
                    aliases = [a.lower() for a in json.loads(p.aliases)]
                    if any(q_lower in a or a in q_lower for a in aliases):
                        matches = True
                except Exception:
                    pass

            if matches:
                sym = p.ticker
                if sym not in seen_symbols:
                    seen_symbols.add(sym)
                    results.append({
                        "symbol": p.ticker,
                        "name": p.name,
                        "isin": p.isin,
                        "type": "ETF",
                        "exchange": "EUR",
                        "currency": "EUR",
                        "etf_profile_id": p.id,
                        "is_custom_etf": not p.is_system,
                    })

    # 2. Query Yahoo Finance public search API
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={cleaned}&quotesCount=10&newsCount=0"
        async with httpx.AsyncClient(headers=HEADERS, timeout=6.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                quotes = data.get("quotes", [])
                for q in quotes:
                    sym = q.get("symbol")
                    if not sym or sym in seen_symbols:
                        continue

                    # Filter out obscure or non-quote types if any
                    q_type = q.get("quoteType", "EQUITY")
                    short_name = q.get("shortname") or q.get("longname") or sym
                    exchange = q.get("exchange", "")

                    # Check if matches an ETF profile in DB
                    etf_profile = _match_etf_profile(db, sym, None, short_name) if db else None

                    seen_symbols.add(sym)
                    results.append({
                        "symbol": sym,
                        "name": short_name,
                        "isin": None,
                        "type": q_type,
                        "exchange": exchange,
                        "currency": "EUR" if exchange in ("PAR", "AMS", "BRU", "GER", "FRA", "EAM") else "USD",
                        "etf_profile_id": etf_profile.id if etf_profile else None,
                        "is_custom_etf": False,
                    })
    except Exception as e:
        logger.warning(f"Error querying market search API for '{cleaned}': {e}")

    return results


async def get_market_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Get live market quotes for a list of symbols with in-memory caching (TTL 1 hour).
    Returns quotes with price converted to EUR.
    """
    now = datetime.now()
    output: Dict[str, Dict[str, Any]] = {}
    missing_symbols: List[str] = []

    # Check cache
    for s in symbols:
        sym = s.strip().upper()
        if not sym:
            continue
        cached = _QUOTES_CACHE.get(sym)
        if cached and cached.get("expires_at", now) > now:
            output[sym] = cached
        else:
            missing_symbols.append(sym)

    if not missing_symbols:
        return output

    # Fetch exchange rates for EUR conversions
    rates = await get_exchange_rates("EUR")

    async with httpx.AsyncClient(headers=HEADERS, timeout=8.0) as client:
        for sym in missing_symbols:
            try:
                # Query chart endpoint for live quote (query2 preferred)
                url = f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
                resp = await client.get(url)
                if resp.status_code != 200:
                    resp = await client.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d")
                if resp.status_code == 200:
                    data = resp.json()
                    res_list = data.get("chart", {}).get("result", [])
                    if res_list:
                        meta = res_list[0].get("meta", {})
                        price = meta.get("regularMarketPrice") or meta.get("previousClose") or 0.0
                        currency = (meta.get("currency") or "EUR").upper()
                        short_name = meta.get("shortName") or meta.get("symbol") or sym
                        instrument_type = meta.get("instrumentType") or "EQUITY"

                        # Convert price to EUR
                        fx_rate = rates.get(currency, 1.0)
                        price_eur = price / fx_rate if fx_rate > 0 else price

                        quote_data = {
                            "symbol": sym,
                            "name": short_name,
                            "price": round(float(price), 4),
                            "currency": currency,
                            "price_eur": round(float(price_eur), 4),
                            "type": instrument_type,
                            "expires_at": now + CACHE_TTL,
                        }
                        _QUOTES_CACHE[sym] = quote_data
                        output[sym] = quote_data
                        continue
            except Exception as e:
                logger.warning(f"Error fetching quote for '{sym}': {e}")

            # Fallback for failed quote
            fallback = {
                "symbol": sym,
                "name": sym,
                "price": 0.0,
                "currency": "EUR",
                "price_eur": 0.0,
                "type": "UNKNOWN",
                "expires_at": now + timedelta(minutes=5),
            }
            output[sym] = fallback

    return output


def extract_asset_clean_name(note: str) -> Optional[str]:
    """Clean up transaction note to extract company or asset name."""
    if not note:
        return None
    cleaned = note.strip()
    
    # Remove common prefix words: "Achat ", "Dividende ", "Vente ", "Achat d'actions "
    cleaned = re.sub(r'^(achat d\'actions|achat actions|achat action|achat de|achat|dividende de|dividende|vente de|vente)\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\(.*\)', '', cleaned) # Remove parentheses
    cleaned = cleaned.strip()

    if len(cleaned) < 2:
        return None

    # Common mappings
    mapping = {
        "apple": "Apple",
        "total": "TotalEnergies",
        "total energie": "TotalEnergies",
        "totalenergies": "TotalEnergies",
        "microsoft": "Microsoft",
        "cisco": "Cisco",
        "blackrock": "BlackRock",
        "air liquide": "Air Liquide",
        "airliquide": "Air Liquide",
        "lvmh": "LVMH",
        "cw8": "Amundi MSCI World",
        "wpea": "iShares MSCI World Swap PEA",
        "ese": "BNP Paribas Easy S&P 500",
    }
    return mapping.get(cleaned.lower(), cleaned)


async def suggest_holdings_from_notes(db: Session, account_id: int) -> List[Dict[str, Any]]:
    """
    Intelligently analyzes historical notes in investment_transactions for an account,
    identifies past assets (e.g. Apple, Total, Microsoft, Cisco...) and proposes suggestions
    for the Point Zéro baseline inventory.
    """
    txs = db.query(InvestmentTransaction).filter(
        InvestmentTransaction.account_id == account_id
    ).all()

    # Aggregate by identified clean asset name
    aggregated: Dict[str, Dict[str, Any]] = {}
    for tx in txs:
        raw_name = tx.ticker or tx.note or ""
        clean_name = extract_asset_clean_name(raw_name)
        if not clean_name:
            continue

        if clean_name not in aggregated:
            aggregated[clean_name] = {
                "name": clean_name,
                "tx_count": 0,
                "net_amount": 0.0,
                "last_date": tx.date,
            }

        aggregated[clean_name]["tx_count"] += 1
        if tx.type == "versement":
            aggregated[clean_name]["net_amount"] += tx.amount
        elif tx.type == "retrait":
            aggregated[clean_name]["net_amount"] -= tx.amount

        if tx.date > aggregated[clean_name]["last_date"]:
            aggregated[clean_name]["last_date"] = tx.date

    # Resolve tickers for top suggestions
    suggestions: List[Dict[str, Any]] = []
    for asset_name, item in aggregated.items():
        search_res = await search_market_assets(asset_name, db=db)
        best_match = search_res[0] if search_res else None

        symbol = best_match["symbol"] if best_match else asset_name
        official_name = best_match["name"] if best_match else asset_name
        etf_id = best_match.get("etf_profile_id") if best_match else None

        suggestions.append({
            "name": official_name,
            "ticker": symbol,
            "isin": best_match.get("isin") if best_match else None,
            "historical_net_invested": round(item["net_amount"], 2),
            "tx_count": item["tx_count"],
            "etf_profile_id": etf_id,
            "is_etf": bool(etf_id or (best_match and best_match.get("type") == "ETF")),
        })

    # Sort by historical net invested descending
    suggestions.sort(key=lambda x: x["historical_net_invested"], reverse=True)
    return suggestions
