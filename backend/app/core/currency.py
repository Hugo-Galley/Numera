import httpx
from datetime import datetime, timedelta, date as date_type
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models.exchange_rate import HistoricalExchangeRate

# Simple cache for exchange rates
_rates_cache: Dict[str, Dict[str, float]] = {}
_cache_expiry: Dict[str, datetime] = {}
CACHE_DURATION = timedelta(hours=6)

async def get_exchange_rates(base: str = "EUR") -> Dict[str, float]:
    """
    Fetch exchange rates from a free API (Frankfurter).
    Rates are cached for 6 hours.
    """
    now = datetime.now()
    if base in _rates_cache and now < _cache_expiry.get(base, now):
        return _rates_cache[base]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.frankfurter.dev/v1/latest?base={base}")
            if response.status_code == 200:
                data = response.json()
                rates = data.get("rates", {})
                # Frankfurter doesn't include the base currency in the rates, add it as 1.0
                rates[base] = 1.0
                _rates_cache[base] = rates
                _cache_expiry[base] = now + CACHE_DURATION
                return rates
    except Exception as e:
        print(f"Error fetching exchange rates: {e}")
        # Fallback to a very basic set of rates if API is down
        if base == "EUR":
            return {"EUR": 1.0, "USD": 1.08, "GBP": 0.84, "CHF": 0.95}
        
    return _rates_cache.get(base, {base: 1.0})

async def get_historical_rate(db: Session, date: date_type, currency: str, base: str = "EUR") -> float:
    """
    Get the exchange rate for a specific date and currency.
    Results are cached in the database.
    Rate returned is: 1 base = X currency.
    """
    if currency == base:
        return 1.0

    # Try to find in DB
    existing = db.query(HistoricalExchangeRate).filter(
        HistoricalExchangeRate.date == date,
        HistoricalExchangeRate.currency == currency
    ).first()

    if existing:
        return existing.rate

    # Fetch from API
    try:
        date_str = date.isoformat()
        async with httpx.AsyncClient() as client:
            # Frankfurter returns the rate for the given date or the closest previous business day
            response = await client.get(f"https://api.frankfurter.dev/v1/{date_str}?base={base}")
            if response.status_code == 200:
                data = response.json()
                rate = data.get("rates", {}).get(currency)
                if rate:
                    # Save to DB (optional: we could save all rates from this date to optimize)
                    new_rate = HistoricalExchangeRate(date=date, currency=currency, rate=rate)
                    db.add(new_rate)
                    db.commit()
                    return rate
    except Exception as e:
        print(f"Error fetching historical exchange rate: {e}")

    # Fallback to current rate if historical is not available
    current_rates = await get_exchange_rates(base)
    return current_rates.get(currency, 1.0)

async def convert_amount(
    amount: float, 
    from_currency: str, 
    to_currency: str = "EUR", 
    date: Optional[date_type] = None,
    db: Optional[Session] = None
) -> float:
    """
    Convert an amount from one currency to another.
    If date and db are provided, uses historical rates.
    """
    if from_currency == to_currency:
        return amount
    
    if date and db and to_currency == "EUR":
        rate = await get_historical_rate(db, date, from_currency, base=to_currency)
        return amount / rate

    # Default to current rates
    rates = await get_exchange_rates(to_currency)
    rate = rates.get(from_currency)
    if rate:
        return amount / rate
        
    return amount
