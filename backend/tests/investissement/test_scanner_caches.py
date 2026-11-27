"""Caches du scanner de diversification : taux de change de la période, références d'indice, fin d'historique des
cours, titres saisis à la main (skill numera-performance : pas de réseau ni de requête répétés à chaque scan)."""
import asyncio
from datetime import date, datetime, timedelta

import httpx
import pytest
from sqlalchemy.orm import Session

from app.core.time import today_local, utcnow_naive
from app.models.etf_profile import EtfProfile
from app.models.exchange_rate import HistoricalExchangeRate
from app.models.security import Security
from app.models.security_price import SecurityPrice
from app.repositories.investissement import securities
from app.services.comptes import exchange_rates
from app.services.investissement import etf_composition
from app.services.investissement.portfolio import books
from app.services.investissement.portfolio.books import FxBook, PriceBook, ensure_history

TODAY = today_local()
START = TODAY - timedelta(weeks=104)
FRIDAYS = [START + timedelta(days=(4 - START.weekday()) % 7 + 7 * i) for i in range(104)]


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def _cache_rates(db: Session, first: date, last: date) -> None:
    db.add_all(HistoricalExchangeRate(date=d, currency="USD", rate=1.1) for d in _days(first, last))
    db.commit()


def _forbid(*_args, **_kwargs):
    raise AssertionError("aucun appel réseau attendu")


def _convert_all(fx: FxBook) -> list[float | None]:
    async def run() -> list[float | None]:
        await fx.preload({"USD"}, "EUR", START, TODAY)
        return [await fx.convert(110.0, "USD", "EUR", friday) for friday in FRIDAYS]

    return asyncio.run(run())


def test_cached_period_is_neither_downloaded_nor_read_day_by_day(db_session: Session, monkeypatch, measure_queries):
    _cache_rates(db_session, START, TODAY)
    monkeypatch.setattr(exchange_rates, "fetch_rate_series", _forbid)
    monkeypatch.setattr(exchange_rates, "fetch_historical_rate", _forbid)

    converted, queries = measure_queries(lambda: _convert_all(FxBook(db_session)))

    assert converted == [pytest.approx(100.0)] * len(FRIDAYS)
    assert queries <= 2


def test_missing_period_is_written_in_one_statement(db_session: Session, monkeypatch, measure_queries):
    async def series(start, end, cur):
        return {d: 1.1 for d in _days(start, end) if d.weekday() < 5}

    monkeypatch.setattr(exchange_rates, "fetch_rate_series", series)
    monkeypatch.setattr(exchange_rates, "fetch_historical_rate", _forbid)

    converted, queries = measure_queries(lambda: _convert_all(FxBook(db_session)))

    assert converted == [pytest.approx(100.0)] * len(FRIDAYS)
    assert queries <= 4
    assert db_session.query(HistoricalExchangeRate).count() >= 700


def test_only_the_missing_tail_is_downloaded(db_session: Session, monkeypatch):
    _cache_rates(db_session, START, TODAY - timedelta(days=30))
    asked: list[date] = []

    async def series(start, end, cur):
        asked.append(start)
        return dict.fromkeys(_days(start, end), 1.2)

    monkeypatch.setattr(exchange_rates, "fetch_rate_series", series)

    asyncio.run(exchange_rates.preload_historical_rates(db_session, "USD", START, TODAY))

    assert asked and asked[0] >= TODAY - timedelta(days=40)
    assert exchange_rates.repo.find_rate(db_session, TODAY, "USD") == 1.2


def test_frankfurter_outage_is_memorized(db_session: Session, monkeypatch):
    calls: list[str] = []

    async def down(*_args, **_kwargs):
        calls.append("http")
        raise httpx.ConnectError("hors ligne")

    async def current(base="EUR"):
        return {"EUR": 1.0, "USD": 1.1}

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", down)
    monkeypatch.setattr(exchange_rates, "get_exchange_rates", current)

    first = _convert_all(FxBook(db_session))
    second = _convert_all(FxBook(db_session))

    assert first == second == [pytest.approx(100.0)] * len(FRIDAYS)
    assert calls == ["http"]


def test_index_reference_failure_is_memorized(db_session: Session, monkeypatch):
    attempts: list[str] = []

    async def unavailable(*_args, **_kwargs):
        attempts.append("collect")
        raise etf_composition.CompositionUnavailable("sources en échec")

    monkeypatch.setattr(etf_composition, "_collect", unavailable)

    assert asyncio.run(etf_composition.ensure_index_reference(db_session, "MSCI ACWI")) is None
    assert asyncio.run(etf_composition.ensure_index_reference(db_session, "MSCI ACWI")) is None

    assert attempts == ["collect"]
    assert db_session.query(EtfProfile).count() == 0


def test_stale_price_tail_is_completed_once(db_session: Session, monkeypatch):
    monkeypatch.setattr(books, "_HISTORY_ATTEMPTS", {})
    last = TODAY - timedelta(days=60)
    db_session.add_all(SecurityPrice(ticker="IWDA.AS", date=d, close=100.0, currency="EUR", source="test")
                       for d in _days(START - timedelta(days=3), last))
    db_session.commit()
    asked: list[date] = []

    async def history(db, ticker, start):
        asked.append(start)
        return 0

    monkeypatch.setattr(books.market_quotes, "fetch_price_history", history)

    for _ in range(2):
        asyncio.run(ensure_history(db_session, PriceBook(), ["IWDA.AS"], START, fetch=True))

    assert asked == [last]


def test_recent_prices_are_not_downloaded(db_session: Session, monkeypatch):
    monkeypatch.setattr(books, "_HISTORY_ATTEMPTS", {})
    db_session.add_all(SecurityPrice(ticker="IWDA.AS", date=d, close=100.0, currency="EUR", source="test")
                       for d in _days(START - timedelta(days=3), TODAY - timedelta(days=2)))
    db_session.commit()
    monkeypatch.setattr(books.market_quotes, "fetch_price_history", _forbid)

    asyncio.run(ensure_history(db_session, PriceBook(), ["IWDA.AS"], START, fetch=True))


def _security(db: Session, isin: str, *, country: str | None, updated_at: datetime) -> None:
    db.add(Security(isin=isin, ticker="ABC", name="Saisie", source="manual", country=country, sector=None,
                    updated_at=updated_at))
    db.commit()


def test_manual_security_without_metadata_is_marked_as_asked(db_session: Session):
    old = utcnow_naive() - timedelta(days=90)
    _security(db_session, "FR0000000001", country=None, updated_at=old)
    _security(db_session, "FR0000000002", country="FRA", updated_at=old)

    securities.upsert_many(db_session, [
        {"isin": isin, "ticker": "XYZ", "name": "Yahoo", "source": "yahoo", "country": "USA", "sector": "Finance"}
        for isin in ("FR0000000001", "FR0000000002")
    ])
    db_session.commit()
    db_session.expire_all()

    asked, kept = (db_session.get(Security, isin) for isin in ("FR0000000001", "FR0000000002"))
    assert asked is not None and kept is not None
    assert asked.updated_at > old
    assert (asked.source, asked.name, asked.ticker, asked.country, asked.sector) == ("manual", "Saisie", "ABC", None, None)
    assert (kept.updated_at, kept.name, kept.country) == (old, "Saisie", "FRA")
