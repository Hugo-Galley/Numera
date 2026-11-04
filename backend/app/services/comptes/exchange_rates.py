"""Taux de change datés et conversion de montants.

Ne commit jamais : le taux découvert est écrit (flush) dans la transaction de l'appelant, qui décide de la valider."""
from datetime import date as date_type

from sqlalchemy.orm import Session

from app.integrations.currency import CurrencyConversionError, fetch_historical_rate, get_exchange_rates
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
