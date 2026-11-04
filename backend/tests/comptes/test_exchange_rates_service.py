"""Taux historiques : le service n'écrit que dans la transaction de l'appelant (jamais de commit caché)."""
import asyncio
from datetime import date

import pytest
from sqlalchemy.orm import sessionmaker

from app.integrations.currency import CurrencyConversionError
from app.models.account import Account
from app.models.exchange_rate import HistoricalExchangeRate
from app.repositories.comptes import exchange_rates as repo
from app.services.comptes import exchange_rates


def _fresh(db_session):
    return sessionmaker(bind=db_session.get_bind())()


def _patch_network(monkeypatch, rates: dict[str, float]):
    async def fetch(day, currency):
        return rates.get(currency)

    async def current(base="EUR"):
        return {"EUR": 1.0}

    monkeypatch.setattr(exchange_rates, "fetch_historical_rate", fetch)
    monkeypatch.setattr(exchange_rates, "get_exchange_rates", current)


def test_historical_rate_does_not_commit_caller_session(db_session, monkeypatch):
    _patch_network(monkeypatch, {"USD": 1.1})
    db_session.add(Account(name="Courant", type="courant"))
    db_session.flush()

    rate = asyncio.run(exchange_rates.get_historical_rate(db_session, date(2026, 1, 5), "USD"))
    db_session.rollback()

    assert rate == 1.1
    fresh = _fresh(db_session)
    assert fresh.query(Account).count() == 0
    assert fresh.query(HistoricalExchangeRate).count() == 0


def test_conversion_with_missing_second_rate_leaves_nothing_in_database(db_session, monkeypatch):
    _patch_network(monkeypatch, {"USD": 1.1})  # GBP introuvable, y compris au taux courant

    with pytest.raises(CurrencyConversionError):
        asyncio.run(exchange_rates.convert_amount(100.0, "USD", "GBP", date=date(2026, 1, 5), db=db_session))
    db_session.rollback()

    assert _fresh(db_session).query(HistoricalExchangeRate).count() == 0


def test_rate_is_cached_once_per_day_and_currency(db_session, monkeypatch):
    calls = []

    async def fetch(day, currency):
        calls.append(currency)
        return 1.1

    monkeypatch.setattr(exchange_rates, "fetch_historical_rate", fetch)
    for _ in range(2):
        asyncio.run(exchange_rates.get_historical_rate(db_session, date(2026, 1, 5), "USD"))

    assert calls == ["USD"]
    assert db_session.query(HistoricalExchangeRate).count() == 1


def test_store_rate_ignores_a_concurrent_duplicate(db_session):
    repo.store_rate(db_session, date(2026, 1, 5), "USD", 1.1)
    repo.store_rate(db_session, date(2026, 1, 5), "USD", 1.2)

    assert db_session.query(HistoricalExchangeRate).count() == 1
    assert repo.find_rate(db_session, date(2026, 1, 5), "USD") == 1.1
