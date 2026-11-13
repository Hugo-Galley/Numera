from datetime import date as date_type
from datetime import datetime, timedelta

import httpx

from app.core.circuit_breaker import CircuitBreaker
from app.core.logging import get_logger
from app.core.time import now_local

logger = get_logger(__name__)

# Simple cache for exchange rates
_rates_cache: dict[str, dict[str, float]] = {}
_cache_expiry: dict[str, datetime] = {}
CACHE_DURATION = timedelta(hours=6)
# Cache négatif : après un échec, on ne réinterroge pas Frankfurter avant ce délai (taux hors ligne ou dernier connu)
FAILURE_CACHE_DURATION = timedelta(minutes=10)
_failed_until: dict[str, datetime] = {}
# Disjoncteur des taux historiques : 3 échecs consécutifs coupent les appels pendant 10 min
_historical_breaker = CircuitBreaker(threshold=3, cooldown=FAILURE_CACHE_DURATION)

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
    now = now_local()
    if base in _rates_cache and now < _cache_expiry.get(base, now):
        return _rates_cache[base]
    if now < _failed_until.get(base, now):
        return _fallback_rates(base)

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
                _failed_until.pop(base, None)
                return rates
            logger.warning(f"Frankfurter returned HTTP {response.status_code} for base={base}")
    except Exception as e:  # frontière réseau : repli sur les taux en cache ou de secours, jamais d'erreur pour l'appelant
        logger.warning(f"Error fetching exchange rates: {e}")

    _failed_until[base] = now + FAILURE_CACHE_DURATION
    return _fallback_rates(base)


def _fallback_rates(base: str) -> dict[str, float]:
    if base in _rates_cache:
        # Taux périmés mais réels : préférables à des valeurs figées
        return _rates_cache[base]
    return _offline_rates(base)


async def fetch_historical_rate(date: date_type, currency: str) -> float | None:
    """Taux Frankfurter (1 EUR = X `currency`) à `date`, ou au jour ouvré précédent. None si indisponible.

    Réseau seulement : la mise en cache en base est faite par `services/comptes/exchange_rates.py`."""
    if not _historical_breaker.allow():
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"https://api.frankfurter.dev/v1/{date.isoformat()}", params={"base": "EUR"})
        _historical_breaker.success()
        if response.status_code == 200:
            return response.json().get("rates", {}).get(currency) or None
    except Exception as e:  # frontière réseau : repli sur les taux en cache ou de secours, jamais d'erreur pour l'appelant
        _historical_breaker.failure()
        logger.warning(f"Error fetching historical exchange rate: {e}")
    return None


async def fetch_rate_series(start: date_type, end: date_type, currency: str) -> dict[date_type, float]:
    """Série Frankfurter (1 EUR = X `currency`) des jours ouvrés de `start` à `end`, en une seule requête.
    Vide si indisponible (disjoncteur ouvert, erreur réseau ou HTTP)."""
    if not _historical_breaker.allow():
        return {}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://api.frankfurter.dev/v1/{start.isoformat()}..{end.isoformat()}",
                params={"base": "EUR", "symbols": currency},
            )
        _historical_breaker.success()
        if response.status_code == 200:
            rates = response.json().get("rates", {})
            return {date_type.fromisoformat(day): by_currency[currency] for day, by_currency in rates.items()
                    if by_currency.get(currency)}
    except Exception as e:  # frontière réseau : repli sur les taux en cache ou de secours, jamais d'erreur pour l'appelant
        _historical_breaker.failure()
        logger.warning(f"Error fetching exchange rate series: {e}")
    return {}


def reset_state() -> None:
    """Vide les caches mémoire (tests)."""
    _rates_cache.clear()
    _cache_expiry.clear()
    _failed_until.clear()
