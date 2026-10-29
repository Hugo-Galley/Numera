"""Cours et taux historiques d'une valorisation : cours stockés en mémoire, conversions datées mémorisées."""
from bisect import bisect_right
from datetime import date as date_type, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.portfolio import SNAPSHOT_MATCH_DAYS
from app.integrations.currency import CurrencyConversionError, convert_amount
from app.repositories import security_prices
from app.services.market import quotes as market_quotes

logger = get_logger(__name__)

HISTORY_RETRY = timedelta(hours=6)
_HISTORY_ATTEMPTS: dict[str, datetime] = {}


class PriceBook:
    """Cours de clôture stockés, chargés en mémoire ; report du dernier cours connu les jours sans cotation."""

    def __init__(self) -> None:
        self._series: dict[str, tuple[list[date_type], list[float], list[str]]] = {}

    def load(self, db: Session, tickers: list[str]) -> None:
        for ticker in tickers:
            rows = security_prices.series(db, ticker)
            self._series[ticker] = ([r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows])

    def has(self, ticker: str) -> bool:
        return bool(self._series.get(ticker, ([], [], []))[0])

    def covers(self, ticker: str, day: date_type, gap_days: int = SNAPSHOT_MATCH_DAYS) -> bool:
        dates = self._series.get(ticker, ([], [], []))[0]
        return bool(dates) and dates[0] <= day + timedelta(days=gap_days)

    def price_on(self, ticker: str, day: date_type) -> tuple[float, str] | None:
        """(cours, devise) à `day` ; avant le premier cours connu, on prend le premier (approximation)."""
        dates, closes, currencies = self._series.get(ticker, ([], [], []))
        if not dates:
            return None
        index = max(bisect_right(dates, day) - 1, 0)
        return closes[index], currencies[index]


async def ensure_history(db: Session, book: PriceBook, tickers: list[str], start: date_type, fetch: bool) -> None:
    """Charge les cours stockés ; télécharge l'historique manquant (au plus une tentative / 6 h par titre)."""
    book.load(db, tickers)
    if not fetch:
        return
    now = datetime.now()
    for ticker in tickers:
        if book.covers(ticker, start):
            continue
        last_try = _HISTORY_ATTEMPTS.get(ticker)
        if last_try and now - last_try < HISTORY_RETRY:
            continue
        _HISTORY_ATTEMPTS[ticker] = now
        try:
            await market_quotes.fetch_price_history(db, ticker, start - timedelta(days=SNAPSHOT_MATCH_DAYS))
        except Exception as exc:  # réseau, format inattendu : on continue avec ce qu'on a
            logger.warning(f"Price history unavailable for {ticker}: {exc}")
    book.load(db, tickers)


class FxBook:
    """Conversions datées mémorisées (une seule requête de taux par couple devise/jour)."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._memo: dict[tuple[str, str, date_type | None], float | None] = {}

    async def convert(self, amount: float, source: str, target: str, day: date_type | None = None) -> float | None:
        if source == target:
            return amount
        key = (source, target, day)
        if key not in self._memo:
            try:
                self._memo[key] = await convert_amount(1.0, source, target, date=day, db=self._db if day else None)
            except CurrencyConversionError as exc:
                logger.warning(f"Portfolio FX: {exc}")
                self._memo[key] = None
        unit = self._memo[key]
        return None if unit is None else amount * unit


async def unit_price(book: PriceBook, fx: FxBook, ticker: str, day: date_type, currency: str) -> float | None:
    """Cours d'un titre à `day`, converti dans la devise du compte."""
    found = book.price_on(ticker, day)
    if found is None:
        return None
    return await fx.convert(found[0], found[1], currency, day)
