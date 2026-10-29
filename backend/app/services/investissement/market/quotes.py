"""Cours des titres : cotation actuelle (cache mémoire 1 h, enregistrée en base), historique et cours à une date."""
from datetime import date as date_type, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.market import guess_quote_currency, normalize_price, to_eur
from app.integrations import yahoo_finance
from app.integrations.currency import get_exchange_rates
from app.repositories.investissement import security_prices

logger = get_logger(__name__)

# In-memory quote cache
# symbol -> {"price": float, "currency": str, "name": str, "type": str, "price_eur": float, "expires_at": datetime}
_QUOTES_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = timedelta(hours=1)


def _demo_stored_quote(db: Optional[Session], sym: str) -> Optional[Dict[str, Any]]:
    from app.db.session import SessionLocal

    session = db or SessionLocal()
    try:
        last = security_prices.latest_demo(session, sym)
    finally:
        if db is None:
            session.close()
    if last is None:
        return None
    return {
        "symbol": sym,
        "name": sym,
        "price": round(last.close, 4),
        "currency": last.currency,
        "price_eur": round(last.close, 4),
        "type": "ETF",
        "price_date": last.date.isoformat(),
        "stale": False,
        "expires_at": datetime.now() + timedelta(minutes=5),
    }


def _cached_or_demo(symbols: List[str], db: Optional[Session], now: datetime) -> tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Cotations déjà connues (démo, cache valide) et symboles à interroger."""
    output: Dict[str, Dict[str, Any]] = {}
    missing_symbols: List[str] = []
    for s in symbols:
        sym = s.strip().upper()
        if not sym:
            continue
        # Démo : les titres du jeu fictif gardent leurs cours générés (un cours réel casserait la courbe)
        demo_price = _demo_stored_quote(db, sym) if settings.DEMO_MODE else None
        if demo_price is not None:
            output[sym] = demo_price
            continue
        cached = _QUOTES_CACHE.get(sym)
        if cached and cached.get("expires_at", now) > now:
            output[sym] = cached
        else:
            missing_symbols.append(sym)
    return output, missing_symbols


async def _fetch_quote(client, sym: str, rates: Dict[str, float], now: datetime) -> Optional[tuple[Dict[str, Any], date_type, float]]:
    """Cotation Yahoo du jour : (cotation, jour du cours, cours) ou None si Yahoo n'a pas de cours."""
    result = await yahoo_finance.fetch_chart(client, sym, {"interval": "1d", "range": "1d"})
    if not result:
        return None
    meta = result.get("meta", {})
    raw_price = meta.get("regularMarketPrice") or meta.get("previousClose") or 0.0
    if not raw_price:
        return None
    price, currency = normalize_price(raw_price, meta.get("currency") or "EUR")
    market_time = meta.get("regularMarketTime")
    price_day = datetime.fromtimestamp(market_time).date() if market_time else now.date()
    price_eur = to_eur(price, currency, rates)
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
    return quote_data, price_day, price


def _fallback_quote(db: Optional[Session], sym: str, rates: Dict[str, float], now: datetime) -> Dict[str, Any]:
    """Échec : dernier cours enregistré si on en a un, sinon cotation vide."""
    last = security_prices.latest(db, sym) if db is not None else None
    if last is not None:
        price_eur = to_eur(last.close, last.currency, rates)
        return {
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
    return {
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


async def get_market_quotes(symbols: List[str], db: Optional[Session] = None) -> Dict[str, Dict[str, Any]]:
    """
    Cours actuels d'une liste de tickers, avec conversion en EUR (cache mémoire 1 h).

    Avec `db`, chaque cours obtenu est enregistré dans `security_prices` ; si Yahoo ne répond pas,
    on renvoie le dernier cours enregistré avec `stale=True` plutôt qu'un prix nul.
    Chaque cotation porte `price_date` et `stale`. `price == 0` signifie « aucun cours connu ».
    """
    now = datetime.now()
    output, missing_symbols = _cached_or_demo(symbols, db, now)
    if not missing_symbols:
        return output

    rates = await get_exchange_rates("EUR")
    stored_any = False

    async with yahoo_finance.client(8.0) as client:
        for sym in missing_symbols:
            try:
                fetched = await _fetch_quote(client, sym, rates, now)
                if fetched:
                    quote_data, price_day, price = fetched
                    _QUOTES_CACHE[sym] = quote_data
                    output[sym] = quote_data
                    if db is not None:
                        security_prices.store_price(db, sym, price_day, round(price, 6), quote_data["currency"])
                        stored_any = True
                    continue
            except Exception as e:
                logger.warning(f"Error fetching quote for '{sym}': {e}")
            output[sym] = _fallback_quote(db, sym, rates, now)

    if stored_any:
        db.commit()
    return output


async def fetch_price_history(db: Session, ticker: str, start: date_type) -> int:
    """Télécharge les clôtures journalières de `ticker` depuis `start` et les enregistre. Renvoie le nombre de jours."""
    sym = ticker.upper().strip()
    period1 = int(datetime.combine(start, datetime.min.time()).timestamp())
    period2 = int(datetime.now().timestamp())
    async with yahoo_finance.client(15.0) as client:
        result = await yahoo_finance.fetch_chart(client, sym, {"interval": "1d", "period1": str(period1), "period2": str(period2)})
    if not result:
        return 0
    raw_currency = result.get("meta", {}).get("currency") or guess_quote_currency(sym)
    timestamps = result.get("timestamp") or []
    closes = ((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    count = 0
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        price, currency = normalize_price(close, raw_currency)
        security_prices.store_price(db, sym, datetime.fromtimestamp(ts).date(), round(price, 6), currency)
        count += 1
    db.commit()
    return count


async def get_price_on(db: Session, ticker: str, day: date_type, max_gap_days: int = 7) -> Optional[Dict[str, Any]]:
    """
    Cours de clôture de `ticker` au jour `day` (ou au dernier jour de cotation précédent).
    Si la base n'a rien de suffisamment proche, on télécharge l'historique depuis `day`.
    Renvoie {"price", "currency", "date"} ou None.
    """
    row = security_prices.latest(db, ticker, on_or_before=day)
    if row is None or (day - row.date).days > max_gap_days:
        try:
            await fetch_price_history(db, ticker, day - timedelta(days=max_gap_days))
        except Exception as e:
            logger.warning(f"Could not fetch price history for '{ticker}': {e}")
        row = security_prices.latest(db, ticker, on_or_before=day)
    if row is None or (day - row.date).days > max_gap_days:
        return None
    return {"price": row.close, "currency": row.currency, "date": row.date.isoformat()}


async def refresh_held_prices(db: Session) -> int:
    """Rafraîchit et enregistre le cours de tous les titres détenus (tâche de fond)."""
    tickers = security_prices.held_tickers(db)
    if tickers:
        await get_market_quotes(tickers, db=db)
    return len(tickers)
