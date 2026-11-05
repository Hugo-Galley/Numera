"""Pannes de Yahoo / Frankfurter : cache négatif, disjoncteur, repli query1, cotations parallèles, série de taux.

Le réseau est simulé par `httpx.MockTransport` avec un compteur d'appels."""
import asyncio
from datetime import date, timedelta

import httpx
import pytest

from app.integrations import currency, yahoo_finance
from app.repositories.comptes import exchange_rates as rates_repo
from app.services.comptes import exchange_rates
from app.services.investissement.market import quotes


@pytest.fixture()
def network(monkeypatch):
    """`network(handler)` branche le handler sur tous les `httpx.AsyncClient` ; renvoie la liste des requêtes vues."""
    real = httpx.AsyncClient
    seen: list[httpx.Request] = []

    def install(handler):
        async def counting(request):
            seen.append(request)
            return await handler(request)

        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(counting), **kw))
        return seen

    return install


async def _timeout(request):
    raise httpx.ConnectTimeout("panne", request=request)


def _chart(price=100.0):
    return {"chart": {"result": [{"meta": {"regularMarketPrice": price, "currency": "EUR", "shortName": "X"}}]}}


def test_exchange_rates_failure_is_cached_for_a_few_minutes(network):
    asyncio.run(_test_exchange_rates_failure_is_cached_for_a_few_minutes(network))


async def _test_exchange_rates_failure_is_cached_for_a_few_minutes(network):
    seen = network(_timeout)
    for _ in range(5):
        rates = await currency.get_exchange_rates("EUR")
    assert rates["USD"] == currency.OFFLINE_EUR_RATES["USD"]
    assert len(seen) == 1


def test_historical_rate_breaker_stops_calling_after_repeated_failures(network):
    asyncio.run(_test_historical_rate_breaker_stops_calling_after_repeated_failures(network))


async def _test_historical_rate_breaker_stops_calling_after_repeated_failures(network):
    seen = network(_timeout)
    for i in range(10):
        assert await currency.fetch_historical_rate(date(2026, 1, 1) + timedelta(days=i), "USD") is None
    assert len(seen) == 3


def test_chart_tries_query1_when_query2_raises(network):
    asyncio.run(_test_chart_tries_query1_when_query2_raises(network))


async def _test_chart_tries_query1_when_query2_raises(network):
    async def handler(request):
        if request.url.host == "query2.finance.yahoo.com":
            raise httpx.ConnectTimeout("panne", request=request)
        return httpx.Response(200, json=_chart(42.0))

    seen = network(handler)
    async with yahoo_finance.client(1.0) as client:
        result = await yahoo_finance.fetch_chart(client, "AAA", {"interval": "1d"})
    assert result["meta"]["regularMarketPrice"] == 42.0
    assert [r.url.host for r in seen] == ["query2.finance.yahoo.com", "query1.finance.yahoo.com"]


def test_failed_quotes_are_not_requested_again(network):
    asyncio.run(_test_failed_quotes_are_not_requested_again(network))


async def _test_failed_quotes_are_not_requested_again(network):
    seen = network(_timeout)
    for _ in range(3):
        out = await quotes.get_market_quotes(["AAA", "BBB"])
    assert out["AAA"]["stale"] is True
    assert len([r for r in seen if 'yahoo' in r.url.host]) <= 4  # une tentative par titre (query2 puis query1), puis cache négatif


def test_quotes_are_fetched_in_parallel_with_bounded_concurrency(network):
    asyncio.run(_test_quotes_are_fetched_in_parallel_with_bounded_concurrency(network))


async def _test_quotes_are_fetched_in_parallel_with_bounded_concurrency(network):
    in_flight = peak = 0

    async def handler(request):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return httpx.Response(200, json=_chart())

    network(handler)
    symbols = [f"S{i}" for i in range(12)]
    out = await quotes.get_market_quotes(symbols)
    assert all(out[s]["price"] == 100.0 for s in symbols)
    assert 1 < peak <= quotes.MAX_CONCURRENT_QUOTES


def test_quotes_cache_returns_independent_copies(network):
    asyncio.run(_test_quotes_cache_returns_independent_copies(network))


async def _test_quotes_cache_returns_independent_copies(network):
    network(lambda request: _async(httpx.Response(200, json=_chart())))
    first = await quotes.get_market_quotes(["AAA"])
    first["AAA"]["price"] = -1
    second = await quotes.get_market_quotes(["AAA"])
    second["AAA"]["price"] = -2
    assert (await quotes.get_market_quotes(["AAA"]))["AAA"]["price"] == 100.0


async def _async(value):
    return value


def test_rate_series_is_one_request_and_fills_weekends(db_session, network):
    asyncio.run(_test_rate_series_is_one_request_and_fills_weekends(db_session, network))


async def _test_rate_series_is_one_request_and_fills_weekends(db_session, network):
    async def handler(request):
        assert str(request.url.path).endswith("2025-12-26..2026-01-12")  # une semaine avant : le 1er jour peut être férié
        return httpx.Response(200, json={"rates": {"2026-01-02": {"USD": 1.1}, "2026-01-05": {"USD": 1.2},
                                                   "2026-01-12": {"USD": 1.3}}})

    seen = network(handler)
    await exchange_rates.preload_historical_rates(db_session, "USD", date(2026, 1, 2), date(2026, 1, 12))
    assert len(seen) == 1
    assert rates_repo.find_rate(db_session, date(2026, 1, 3), "USD") == 1.1  # samedi : dernier jour ouvré
    assert rates_repo.find_rate(db_session, date(2026, 1, 9), "USD") == 1.2
    assert await exchange_rates.get_historical_rate(db_session, date(2026, 1, 6), "USD") == 1.2
    assert len(seen) == 1
