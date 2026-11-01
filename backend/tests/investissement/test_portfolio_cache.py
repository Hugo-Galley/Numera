"""Valorisation d'un compte titres : mise en cache brève, invalidée par toute écriture en base."""
import asyncio
from datetime import datetime, timedelta

import pytest

import app.integrations.currency as currency_mod
import app.integrations.yahoo_finance as yahoo_finance
import app.repositories.investissement.security_prices as security_prices
import app.services.investissement.market.quotes as market_quotes
from app.models.account import Account
from app.services.investissement.portfolio.compute import compute_portfolio


@pytest.fixture(autouse=True)
def offline_market(monkeypatch):
    async def no_chart(client, sym, params):
        return None

    async def fake_historical_rate(db, day, currency, base="EUR"):
        return {"EUR": 1.0, "USD": 2.0}[currency]

    monkeypatch.setattr(yahoo_finance, "fetch_chart", no_chart)
    monkeypatch.setattr(currency_mod, "get_historical_rate", fake_historical_rate)
    market_quotes._QUOTES_CACHE.clear()
    yield
    market_quotes._QUOTES_CACHE.clear()


def _iso(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).replace(microsecond=0).isoformat()


def _account(client, db_session) -> Account:
    account_id = client.post(
        "/accounts", json={"name": "CTO", "type": "investissement", "currency": "EUR", "color": None}
    ).json()["id"]
    client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(200),
        "holdings": [{"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": 10, "buy_price_avg": 100.0, "currency": "EUR"}],
    })
    security_prices.store_price(db_session, "CW8.PA", (datetime.now() - timedelta(days=1)).date(), 120.0, "EUR")
    db_session.commit()
    return db_session.get(Account, account_id)


def _compute(db_session, account, **kwargs):
    return asyncio.run(compute_portfolio(db_session, account, history=False, **kwargs))


def test_second_call_is_served_from_cache(client, db_session, measure_queries):
    account = _account(client, db_session)
    first, first_queries = measure_queries(lambda: _compute(db_session, account))
    second, second_queries = measure_queries(lambda: _compute(db_session, account))

    assert first_queries > 0
    assert second_queries == 0
    assert second["value_eur"] == first["value_eur"]


def test_cache_is_distinct_per_history_flag(client, db_session, measure_queries):
    account = _account(client, db_session)
    _compute(db_session, account)
    _, queries = measure_queries(lambda: asyncio.run(compute_portfolio(db_session, account, history=True)))

    assert queries > 0


def test_write_invalidates_cache(client, db_session):
    account = _account(client, db_session)
    before = _compute(db_session, account)

    resp = client.post("/investment-transactions", json={
        "account_id": account.id, "date": _iso(10), "type": "versement", "amount": 500.0,
    })
    assert resp.status_code == 201, resp.text
    after = _compute(db_session, account)

    assert after["value_eur"] == pytest.approx(before["value_eur"] + 500.0)


def test_flush_without_commit_invalidates_cache(client, db_session, measure_queries):
    account = _account(client, db_session)
    _compute(db_session, account)

    account.name = "CTO renommé"
    db_session.flush()
    _, queries = measure_queries(lambda: _compute(db_session, account))

    assert queries > 0


def test_caller_cannot_corrupt_cached_result(client, db_session):
    account = _account(client, db_session)
    first = _compute(db_session, account)
    expected = first["value_eur"]
    first["value_eur"] = -1.0
    first["warnings"].append("pollué")

    second = _compute(db_session, account)

    assert second["value_eur"] == expected
    assert "pollué" not in second["warnings"]
