"""Taux de change datés et conversion de montants.

Ne commit jamais : le taux découvert est écrit (flush) dans la transaction de l'appelant, qui décide de la valider."""
from datetime import date as date_type
from datetime import timedelta

from sqlalchemy.orm import Session

from app.integrations.currency import CurrencyConversionError, fetch_historical_rate, fetch_rate_series, get_exchange_rates
from app.repositories.comptes import exchange_rates as repo


async def get_historical_rate(db: Session, date: date_type, currency: str, base: str = "EUR") -> float:
    """Taux à une date (1 `base` = X `currency`), mis en cache en base (taux exprimés en EUR uniquement)."""
    if currency == base:
        return 1.0

    if base == "EUR":
        cached = repo.find_rate(db, date, currency)
        if cached:
            return cached
        rate = await fetch_historical_rate(date, currency)
        if rate:
            repo.store_rate(db, date, currency, rate)
            db.flush()
            return rate

    # Repli sur le taux courant si l'historique est indisponible
    rate = (await get_exchange_rates(base)).get(currency)
    if not rate:
        raise CurrencyConversionError(f"No exchange rate available for {currency} (base {base})")
    return rate


# Le dernier taux publié peut dater de quelques jours (week-end, fériés, publication en fin d'après-midi)
PUBLICATION_LAG = timedelta(days=4)


async def preload_historical_rates(
    db: Session, currency: str, start: date_type, end: date_type,
) -> dict[date_type, float]:
    """Taux (1 EUR = X `currency`) de `start` à `end`, lus en une requête ; seule la période absente de la base est
    demandée à Frankfurter (une requête de série) et écrite en une instruction groupée.

    Les jours sans publication (week-ends, fériés) reprennent le dernier taux connu, comme le fait Frankfurter pour
    une date isolée. Rien n'est écrit au-delà du dernier taux publié (dates futures). Réseau en échec : les taux déjà
    en base, sans erreur (l'échec est mémorisé par `fetch_rate_series`)."""
    if currency == "EUR":
        return {}
    cached = repo.rates_between(db, currency, start, end + timedelta(days=1))
    head_known = start in cached
    if head_known and max(cached) >= end - PUBLICATION_LAG:
        return cached
    fetch_from = max(cached) + timedelta(days=1) if head_known else start
    series = await fetch_rate_series(fetch_from - timedelta(days=7), end, currency)
    if not series:
        return cached
    fetched: dict[date_type, float] = {}
    rate = None
    day = min(series)
    while day <= min(end, max(series)):
        rate = series.get(day, rate)
        if day >= fetch_from and rate is not None:
            fetched[day] = rate
        day += timedelta(days=1)
    repo.store_rates(db, currency, {d: r for d, r in fetched.items() if d not in cached})
    db.flush()
    return cached | fetched


async def convert_amount(
    amount: float,
    from_currency: str,
    to_currency: str = "EUR",
    date: date_type | None = None,
    db: Session | None = None,
) -> float:
    """Convertit un montant. Avec `date` et `db`, taux historiques (taux croisé via l'EUR pour toute paire),
    sinon taux courants. Lève `CurrencyConversionError` si aucun taux n'est disponible."""
    if from_currency == to_currency:
        return amount

    if date and db:
        # 1 EUR = X from_currency ; 1 EUR = Y to_currency  =>  amount / X * Y
        from_per_eur = await get_historical_rate(db, date, from_currency, base="EUR")
        to_per_eur = await get_historical_rate(db, date, to_currency, base="EUR")
        return amount / from_per_eur * to_per_eur

    rates = await get_exchange_rates(to_currency)
    rate = rates.get(from_currency)
    if not rate:
        raise CurrencyConversionError(f"No exchange rate available for {from_currency} -> {to_currency}")
    return amount / rate
