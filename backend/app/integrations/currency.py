from datetime import date as date_type
from datetime import datetime, timedelta

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

# Simple cache for exchange rates
_rates_cache: dict[str, dict[str, float]] = {}
_cache_expiry: dict[str, datetime] = {}
CACHE_DURATION = timedelta(hours=6)

# Taux hors-ligne (1 EUR = X devise), utilisés uniquement si Frankfurter est injoignable
# et qu'aucun taux n'a jamais été récupéré.
OFFLINE_EUR_RATES: dict[str, float] = {"EUR": 1.0, "USD": 1.08, "GBP": 0.84, "CHF": 0.95}


class CurrencyConversionError(ValueError):
    """Aucun taux de change exploitable : on refuse de convertir plutôt que d'inventer un taux 1:1."""


def _offline_rates(base: str) -> dict[str, float]:
    """Taux hors-ligne exprimés pour `base` (dérivés de l'EUR si besoin)."""
    if base not in OFFLINE_EUR_RATES:
        return {base: 1.0}
    base_per_eur = OFFLINE_EUR_RATES[base]
    return {cur: rate / base_per_eur for cur, rate in OFFLINE_EUR_RATES.items()}


async def get_exchange_rates(base: str = "EUR") -> dict[str, float]:
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


async def fetch_historical_rate(date: date_type, currency: str) -> float | None:
    """Taux Frankfurter (1 EUR = X `currency`) à `date`, ou au jour ouvré précédent. None si indisponible.

    Réseau seulement : la mise en cache en base est faite par `services/comptes/exchange_rates.py`."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"https://api.frankfurter.dev/v1/{date.isoformat()}", params={"base": "EUR"})
            if response.status_code == 200:
                return response.json().get("rates", {}).get(currency) or None
    except Exception as e:
        logger.warning(f"Error fetching historical exchange rate: {e}")
    return None
