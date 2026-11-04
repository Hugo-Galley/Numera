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
