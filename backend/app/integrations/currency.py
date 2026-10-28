import httpx
from datetime import datetime, timedelta, date as date_type
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.exchange_rate import HistoricalExchangeRate

logger = get_logger(__name__)

# Simple cache for exchange rates
_rates_cache: Dict[str, Dict[str, float]] = {}
_cache_expiry: Dict[str, datetime] = {}
CACHE_DURATION = timedelta(hours=6)

# Taux hors-ligne (1 EUR = X devise), utilisés uniquement si Frankfurter est injoignable
# et qu'aucun taux n'a jamais été récupéré.
OFFLINE_EUR_RATES: Dict[str, float] = {"EUR": 1.0, "USD": 1.08, "GBP": 0.84, "CHF": 0.95}


class CurrencyConversionError(ValueError):
    """Aucun taux de change exploitable : on refuse de convertir plutôt que d'inventer un taux 1:1."""


def _offline_rates(base: str) -> Dict[str, float]:
    """Taux hors-ligne exprimés pour `base` (dérivés de l'EUR si besoin)."""
    if base not in OFFLINE_EUR_RATES:
        return {base: 1.0}
    base_per_eur = OFFLINE_EUR_RATES[base]
    return {cur: rate / base_per_eur for cur, rate in OFFLINE_EUR_RATES.items()}


async def get_exchange_rates(base: str = "EUR") -> Dict[str, float]:
    """
    Fetch exchange rates from a free API (Frankfurter).
    Rates are cached for 6 hours. En cas d'échec : dernier cache connu (même expiré),
    sinon taux hors-ligne.
    """
    now = datetime.now()
    if base in _rates_cache and now < _cache_expiry.get(base, now):
        return _rates_cache[base]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get("https://api.frankfurter.dev/v1/latest", params={"base": base})
            if response.status_code == 200:
                data = response.json()
                rates = data.get("rates", {})
                # Frankfurter doesn't include the base currency in the rates, add it as 1.0
                rates[base] = 1.0
                _rates_cache[base] = rates
                _cache_expiry[base] = now + CACHE_DURATION
                return rates
            logger.warning(f"Frankfurter returned HTTP {response.status_code} for base={base}")
    except Exception as e:
        logger.warning(f"Error fetching exchange rates: {e}")

    if base in _rates_cache:
        # Taux périmés mais réels : préférables à des valeurs figées
        return _rates_cache[base]
    return _offline_rates(base)


async def get_historical_rate(db: Session, date: date_type, currency: str, base: str = "EUR") -> float:
    """
    Get the exchange rate for a specific date and currency.
    Results are cached in the database.
    Rate returned is: 1 base = X currency.
    """
    if currency == base:
        return 1.0

    # Try to find in DB (la table ne stocke que des taux exprimés en base EUR)
    existing = db.query(HistoricalExchangeRate).filter(
        HistoricalExchangeRate.date == date,
        HistoricalExchangeRate.currency == currency
    ).first() if base == "EUR" else None

    if existing:
        return existing.rate

    # Fetch from API
    try:
        date_str = date.isoformat()
        async with httpx.AsyncClient(timeout=8.0) as client:
            # Frankfurter returns the rate for the given date or the closest previous business day
            response = await client.get(f"https://api.frankfurter.dev/v1/{date_str}", params={"base": base})
            if response.status_code == 200:
                data = response.json()
                rate = data.get("rates", {}).get(currency)
                if rate:
                    if base == "EUR":
                        db.add(HistoricalExchangeRate(date=date, currency=currency, rate=rate))
                        db.commit()
                    return rate
    except Exception as e:
        logger.warning(f"Error fetching historical exchange rate: {e}")

    # Fallback to current rate if historical is not available
    current_rates = await get_exchange_rates(base)
    rate = current_rates.get(currency)
    if not rate:
        raise CurrencyConversionError(f"No exchange rate available for {currency} (base {base})")
    return rate


async def convert_amount(
    amount: float,
    from_currency: str,
    to_currency: str = "EUR",
    date: Optional[date_type] = None,
    db: Optional[Session] = None
) -> float:
    """
    Convert an amount from one currency to another.
    If date and db are provided, uses historical rates (cross-rate via EUR for any
    currency pair), otherwise current rates.
    Raises CurrencyConversionError when no rate is available.
    """
    if from_currency == to_currency:
        return amount

    if date and db:
        # 1 EUR = X from_currency ; 1 EUR = Y to_currency  =>  amount / X * Y
        from_per_eur = await get_historical_rate(db, date, from_currency, base="EUR")
        to_per_eur = await get_historical_rate(db, date, to_currency, base="EUR")
        return amount / from_per_eur * to_per_eur

    # Default to current rates
    rates = await get_exchange_rates(to_currency)
    rate = rates.get(from_currency)
    if not rate:
        raise CurrencyConversionError(f"No exchange rate available for {from_currency} -> {to_currency}")
    return amount / rate
