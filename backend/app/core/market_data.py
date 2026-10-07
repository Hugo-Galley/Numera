import re
import json
import httpx
from datetime import date as date_type, datetime, timedelta
from urllib.parse import quote
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.currency import get_exchange_rates
from app.models.etf_profile import EtfProfile
from app.models.investment_transaction import InvestmentTransaction
from app.models.security_price import SecurityPrice

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

    # Name-based heuristic : nom vide => aucune correspondance (sinon "" est contenu dans tout),
    # et on exige que le nom complet du profil figure dans le libellé (pas l'inverse, trop large)
    if not norm_name:
        return None
    for p in profiles:
        p_name = p.name.lower().strip()
        if len(p_name) >= 6 and (p_name == norm_name or p_name in norm_name):
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
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        async with httpx.AsyncClient(headers=HEADERS, timeout=6.0) as client:
            resp = await client.get(url, params={"q": cleaned, "quotesCount": 10, "newsCount": 0})
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
                    if not etf_profile and db and (q_type in ("ETF", "MUTUALFUND") or sym.startswith("0P")):
                        try:
                            from app.core.etf_analyzer import auto_decompose_and_create_profile
                            etf_profile = await auto_decompose_and_create_profile(db, symbol=sym, name=short_name)
                        except Exception as e:
                            logger.warning(f"Could not auto-decompose searched ETF {sym}: {e}")

                    seen_symbols.add(sym)
                    results.append({
                        "symbol": sym,
                        "name": short_name,
                        "isin": None,
                        "type": q_type,
                        "exchange": exchange,
                        "currency": guess_quote_currency(sym),
                        "etf_profile_id": etf_profile.id if etf_profile else None,
                        "is_custom_etf": False,
                    })
    except Exception as e:
        logger.warning(f"Error querying market search API for '{cleaned}': {e}")

    return results


# Devise de cotation déduite du suffixe Yahoo (la recherche ne renvoie pas la devise)
QUOTE_SUFFIX_CURRENCIES: Dict[str, str] = {
    **{sfx: "EUR" for sfx in (".PA", ".AS", ".BR", ".DE", ".F", ".SG", ".MU", ".DU", ".HM", ".BE", ".MI", ".MC", ".VI", ".LS", ".HE", ".IR")},
    ".SW": "CHF",
    ".L": "GBP",
}


def guess_quote_currency(symbol: str) -> str:
    """Devise probable d'un ticker Yahoo (`CW8.PA` → EUR, `BTC-EUR` → EUR, `AAPL` → USD)."""
    sym = symbol.upper().strip()
    if "-" in sym and len(sym.rsplit("-", 1)[1]) == 3:
        return sym.rsplit("-", 1)[1]
    for suffix, currency in QUOTE_SUFFIX_CURRENCIES.items():
        if sym.endswith(suffix):
            return currency
    return "USD"


def _normalize_price(price: float, raw_currency: str) -> tuple[float, str]:
    if raw_currency in ("GBp", "GBX"):
        # Cotations LSE en pence : on ramène en livres
        return float(price) / 100.0, "GBP"
    return float(price), (raw_currency or "EUR").upper()


async def _fetch_chart(client: httpx.AsyncClient, sym: str, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Appelle l'endpoint chart de Yahoo (query2 puis query1) et renvoie le premier résultat."""
    quoted_sym = quote(sym, safe="")
    for host in ("query2", "query1"):
        resp = await client.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{quoted_sym}", params=params)
        if resp.status_code == 200:
            res_list = resp.json().get("chart", {}).get("result") or []
            return res_list[0] if res_list else None
    return None


def store_price(db: Session, ticker: str, day: date_type, close: float, currency: str, source: str = "yahoo") -> None:
    """Enregistre (ou met à jour) le cours de clôture d'un titre pour un jour donné. Ne commit pas."""
    sym = ticker.upper().strip()
    row = db.query(SecurityPrice).filter(SecurityPrice.ticker == sym, SecurityPrice.date == day).first()
    if row is None:
        db.add(SecurityPrice(ticker=sym, date=day, close=close, currency=currency, source=source))
    else:
        row.close, row.currency, row.source = close, currency, source


def _latest_stored_price(db: Session, ticker: str, on_or_before: Optional[date_type] = None) -> Optional[SecurityPrice]:
    q = db.query(SecurityPrice).filter(SecurityPrice.ticker == ticker.upper().strip())
    if on_or_before is not None:
        q = q.filter(SecurityPrice.date <= on_or_before)
    return q.order_by(SecurityPrice.date.desc()).first()


def _to_eur(price: float, currency: str, rates: Dict[str, float]) -> Optional[float]:
    rate = rates.get(currency)
    if not rate:
        logger.warning(f"No EUR exchange rate for {currency}: price left unconverted")
        return None
    return price / rate


async def get_market_quotes(symbols: List[str], db: Optional[Session] = None) -> Dict[str, Dict[str, Any]]:
    """
    Cours actuels d'une liste de tickers, avec conversion en EUR (cache mémoire 1 h).

    Avec `db`, chaque cours obtenu est enregistré dans `security_prices` ; si Yahoo ne répond pas,
    on renvoie le dernier cours enregistré avec `stale=True` plutôt qu'un prix nul.
    Chaque cotation porte `price_date` et `stale`. `price == 0` signifie « aucun cours connu ».
    """
    now = datetime.now()
    output: Dict[str, Dict[str, Any]] = {}
    missing_symbols: List[str] = []

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

    rates = await get_exchange_rates("EUR")
    stored_any = False

    async with httpx.AsyncClient(headers=HEADERS, timeout=8.0) as client:
        for sym in missing_symbols:
            try:
                result = await _fetch_chart(client, sym, {"interval": "1d", "range": "1d"})
                if result:
                    meta = result.get("meta", {})
                    raw_price = meta.get("regularMarketPrice") or meta.get("previousClose") or 0.0
                    if raw_price:
                        price, currency = _normalize_price(raw_price, meta.get("currency") or "EUR")
                        market_time = meta.get("regularMarketTime")
                        price_day = datetime.fromtimestamp(market_time).date() if market_time else now.date()
                        price_eur = _to_eur(price, currency, rates)
                        quote_data = {
                            "symbol": sym,
                            "name": meta.get("shortName") or meta.get("symbol") or sym,
                            "price": round(price, 4),
                            "currency": currency,
                            "price_eur": round(price_eur, 4) if price_eur is not None else 0.0,
                            "type": meta.get("instrumentType") or "EQUITY",
                            "price_date": price_day.isoformat(),
                            "stale": False,
                            "expires_at": now + CACHE_TTL,
                        }
                        _QUOTES_CACHE[sym] = quote_data
                        output[sym] = quote_data
                        if db is not None:
                            store_price(db, sym, price_day, round(price, 6), currency)
                            stored_any = True
                        continue
            except Exception as e:
                logger.warning(f"Error fetching quote for '{sym}': {e}")

            # Échec : dernier cours enregistré si on en a un, sinon cotation vide
            last = _latest_stored_price(db, sym) if db is not None else None
            if last is not None:
                price_eur = _to_eur(last.close, last.currency, rates)
                output[sym] = {
                    "symbol": sym,
                    "name": sym,
                    "price": round(last.close, 4),
                    "currency": last.currency,
                    "price_eur": round(price_eur, 4) if price_eur is not None else 0.0,
                    "type": "UNKNOWN",
                    "price_date": last.date.isoformat(),
                    "stale": True,
                    "expires_at": now + timedelta(minutes=5),
                }
            else:
                output[sym] = {
                    "symbol": sym,
                    "name": sym,
                    "price": 0.0,
                    "currency": guess_quote_currency(sym),
                    "price_eur": 0.0,
                    "type": "UNKNOWN",
                    "price_date": None,
                    "stale": True,
                    "expires_at": now + timedelta(minutes=5),
                }

    if stored_any:
        db.commit()
    return output


async def fetch_price_history(db: Session, ticker: str, start: date_type) -> int:
    """Télécharge les clôtures journalières de `ticker` depuis `start` et les enregistre. Renvoie le nombre de jours."""
    sym = ticker.upper().strip()
    period1 = int(datetime.combine(start, datetime.min.time()).timestamp())
    period2 = int(datetime.now().timestamp())
    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
        result = await _fetch_chart(client, sym, {"interval": "1d", "period1": str(period1), "period2": str(period2)})
    if not result:
        return 0
    raw_currency = result.get("meta", {}).get("currency") or guess_quote_currency(sym)
    timestamps = result.get("timestamp") or []
    closes = ((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    count = 0
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        price, currency = _normalize_price(close, raw_currency)
        store_price(db, sym, datetime.fromtimestamp(ts).date(), round(price, 6), currency)
        count += 1
    db.commit()
    return count


async def get_price_on(db: Session, ticker: str, day: date_type, max_gap_days: int = 7) -> Optional[Dict[str, Any]]:
    """
    Cours de clôture de `ticker` au jour `day` (ou au dernier jour de cotation précédent).
    Si la base n'a rien de suffisamment proche, on télécharge l'historique depuis `day`.
    Renvoie {"price", "currency", "date"} ou None.
    """
    row = _latest_stored_price(db, ticker, on_or_before=day)
    if row is None or (day - row.date).days > max_gap_days:
        try:
            await fetch_price_history(db, ticker, day - timedelta(days=max_gap_days))
        except Exception as e:
            logger.warning(f"Could not fetch price history for '{ticker}': {e}")
        row = _latest_stored_price(db, ticker, on_or_before=day)
    if row is None or (day - row.date).days > max_gap_days:
        return None
    return {"price": row.close, "currency": row.currency, "date": row.date.isoformat()}


async def refresh_held_prices(db: Session) -> int:
    """Rafraîchit et enregistre le cours de tous les titres détenus (tâche de fond)."""
    from app.models.portfolio_holding import PortfolioHolding

    tickers = sorted({t for (t,) in db.query(PortfolioHolding.ticker).filter(PortfolioHolding.quantity > 0).distinct()})
    if tickers:
        await get_market_quotes(tickers, db=db)
    return len(tickers)


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
