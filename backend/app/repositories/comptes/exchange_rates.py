"""Taux de change historiques mis en cache (`historical_exchange_rates`)."""
from datetime import date as date_type

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.models.exchange_rate import HistoricalExchangeRate


def find_rate(db: Session, day: date_type, currency: str) -> float | None:
    row = (
        db.query(HistoricalExchangeRate.rate)
        .filter(HistoricalExchangeRate.date == day, HistoricalExchangeRate.currency == currency)
        .first()
    )
    return row[0] if row else None


def store_rate(db: Session, day: date_type, currency: str, rate: float) -> None:
    """Enregistre un taux sans erreur si un autre appel l'a déjà fait. Ne commit pas."""
    db.execute(
        insert(HistoricalExchangeRate)
        .values(date=day, currency=currency, rate=rate)
        .on_conflict_do_nothing(index_elements=["date", "currency"])
    )


def rates_between(db: Session, currency: str, start: date_type, end: date_type) -> dict[date_type, float]:
    """Taux (1 EUR = X `currency`) stockés de `start` inclus à `end` exclu, en une requête."""
    rows = (
        db.query(HistoricalExchangeRate.date, HistoricalExchangeRate.rate)
        .filter(HistoricalExchangeRate.currency == currency,
                HistoricalExchangeRate.date >= start, HistoricalExchangeRate.date < end)
        .all()
    )
    return dict(rows)


def store_rates(db: Session, currency: str, rates: dict[date_type, float]) -> None:
    """Enregistre une série de taux en une instruction groupée, sans erreur sur un jour déjà présent. Ne commit pas."""
    if not rates:
        return
    db.execute(
        insert(HistoricalExchangeRate).on_conflict_do_nothing(index_elements=["date", "currency"]),
        [{"date": day, "currency": currency, "rate": rate} for day, rate in rates.items()],
    )
