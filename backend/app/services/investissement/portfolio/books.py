"""Cours et taux historiques d'une valorisation : cours stockés en mémoire, conversions datées mémorisées."""
from bisect import bisect_right
from datetime import date as date_type
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.time import now_local, today_local
from app.domain.portfolio import SNAPSHOT_MATCH_DAYS
from app.integrations.currency import CurrencyConversionError
from app.repositories.investissement import security_prices
from app.services.comptes.exchange_rates import convert_amount, preload_historical_rates
from app.services.investissement.market import quotes as market_quotes

logger = get_logger(__name__)

HISTORY_RETRY = timedelta(hours=6)
_HISTORY_ATTEMPTS: dict[str, datetime] = {}


class PriceBook:
    """Cours de clôture stockés, chargés en mémoire ; report du dernier cours connu les jours sans cotation."""

    def __init__(self) -> None:
        self._series: dict[str, tuple[list[date_type], list[float], list[str]]] = {}

    def load(self, db: Session, tickers: list[str]) -> None:
        for ticker, rows in security_prices.series_by_ticker(db, tickers).items():
            self._series[ticker] = ([r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows])

    def currencies(self) -> set[str]:
        """Devises de cotation des titres chargés."""
        return {c for _, _, currencies in self._series.values() for c in set(currencies)}

    def has(self, ticker: str) -> bool:
        return bool(self._series.get(ticker, ([], [], []))[0])

    def first_date(self, ticker: str) -> date_type | None:
        """Date du premier cours chargé, None sans cours."""
        dates = self._series.get(ticker, ([], [], []))[0]
        return dates[0] if dates else None

    def last_date(self, ticker: str) -> date_type | None:
        """Date du dernier cours chargé, None sans cours."""
        dates = self._series.get(ticker, ([], [], []))[0]
        return dates[-1] if dates else None

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


def _missing_since(book: PriceBook, ticker: str, start: date_type, today: date_type) -> date_type | None:
    """Date d'où télécharger les cours d'un titre : début manquant, sinon fin trop ancienne (sans cours depuis plus
    d'une semaine, le report du dernier cours fausserait les rendements) ; None si l'historique couvre la période."""
    if not book.covers(ticker, start):
        return start - timedelta(days=SNAPSHOT_MATCH_DAYS)
    last = book.last_date(ticker)
    if last is not None and last < today - timedelta(days=SNAPSHOT_MATCH_DAYS):
        return last
    return None


async def ensure_history(db: Session, book: PriceBook, tickers: list[str], start: date_type, fetch: bool) -> None:
    """Charge les cours stockés ; télécharge le début ou la fin manquants (au plus une tentative / 6 h par titre)."""
    book.load(db, tickers)
    if not fetch:
        return
    now = now_local()
    today = today_local()
    for ticker in tickers:
        since = _missing_since(book, ticker, start, today)
        if since is None:
            continue
        last_try = _HISTORY_ATTEMPTS.get(ticker)
        if last_try and now - last_try < HISTORY_RETRY:
            continue
        _HISTORY_ATTEMPTS[ticker] = now
        try:
            await market_quotes.fetch_price_history(db, ticker, since)
        except Exception as exc:  # réseau, format inattendu : on continue avec ce qu'on a
            logger.warning(f"Price history unavailable for {ticker}: {exc}")
    market_quotes.persist_fetched_prices(db)
    book.load(db, tickers)


class FxBook:
    """Conversions datées mémorisées. Après `preload`, les taux de la période sont en mémoire : aucune requête par
    jour. Un jour absent de la série passe par `convert_amount` (taux en base, sinon Frankfurter, dont l'échec de la
    série est mémorisé : pas d'appel réseau par jour pendant une panne)."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._memo: dict[tuple[str, str, date_type | None], float | None] = {}
        self._rates: dict[str, dict[date_type, float]] = {}

    async def preload(self, currencies: set[str], target: str, start: date_type, end: date_type) -> None:
        """Charge la série de taux de la période, une requête par devise (téléchargée seulement si elle manque)."""
        for currency in sorted((currencies | {target}) - {"EUR"}):
            self._rates[currency] = await preload_historical_rates(self._db, currency, start, end)

    def _loaded_rate(self, currency: str, day: date_type) -> float | None:
        """1 EUR = X `currency` à `day` depuis la série préchargée, None si ce jour n'y est pas (même règle que
        `get_historical_rate`, qui lit le taux du jour exact)."""
        if currency == "EUR":
            return 1.0
        return self._rates.get(currency, {}).get(day)

    async def _unit(self, source: str, target: str, day: date_type | None) -> float:
        if day is not None:
            from_per_eur, to_per_eur = self._loaded_rate(source, day), self._loaded_rate(target, day)
            if from_per_eur and to_per_eur:
                return to_per_eur / from_per_eur
        return await convert_amount(1.0, source, target, date=day, db=self._db if day else None)

    async def convert(self, amount: float, source: str, target: str, day: date_type | None = None) -> float | None:
        if source == target:
            return amount
        key = (source, target, day)
        if key not in self._memo:
            try:
                self._memo[key] = await self._unit(source, target, day)
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
