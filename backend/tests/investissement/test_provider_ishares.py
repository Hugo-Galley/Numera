"""iShares : catalogue des fonds et composition complète."""
import asyncio
from datetime import date

import httpx
import pytest

from app.domain.etf_normalize import is_equity_line
from app.integrations.etf_providers.base import ProviderUnavailable
from app.integrations.etf_providers.ishares import IShares
from tests.investissement.etf_provider_helpers import fixture_bytes, mock_factory


def _serve(request: httpx.Request) -> httpx.Response:
    if "product-screener" in str(request.url):
        return httpx.Response(200, content=fixture_bytes("ishares_catalog.json"))
    assert request.url.params["portfolioId"] == "251882"
    return httpx.Response(200, content=fixture_bytes("ishares_holdings_251882.json"))


def _provider(handler=_serve, seen=None) -> IShares:
    return IShares(client_factory=mock_factory(handler, seen))


def test_lookup_returns_the_fund_of_an_isin():
    fund = asyncio.run(_provider().lookup("IE00B4L5Y983"))
    assert fund is not None
    assert (fund.provider, fund.ref, fund.isin, fund.ticker, fund.replication) == (
        "ishares", "251882", "IE00B4L5Y983", "SWDA", "physical")
    assert fund.name == "iShares Core MSCI World UCITS ETF"


def test_lookup_marks_a_swap_fund_synthetic():
    fund = asyncio.run(_provider().lookup("IE000OY7BDY9"))
    assert fund is not None
    assert fund.replication == "synthetic"
    assert "\xa0" not in fund.name


def test_lookup_of_an_unknown_isin_returns_none():
    assert asyncio.run(_provider().lookup("FR0000000000")) is None


def test_catalog_is_downloaded_once():
    seen: list[httpx.Request] = []
    provider = _provider(seen=seen)

    async def twice():
        await provider.lookup("IE00B4L5Y983")
        await provider.find_isin_by_ticker("CSPX.L")

    asyncio.run(twice())
    assert len(seen) == 1


def test_find_isin_by_london_ticker():
    assert asyncio.run(_provider().find_isin_by_ticker("SWDA.L")) == "IE00B4L5Y983"


@pytest.mark.parametrize("symbol", ["SWDA", "SWDA.PA", "SWDA.MI", "INCONNU.L"])
def test_find_isin_refuses_other_exchanges_and_unknown_tickers(symbol):
    """Le catalogue ne donne que le ticker de Londres : un même ticker ailleurs peut désigner un autre titre."""
    assert asyncio.run(_provider().find_isin_by_ticker(symbol)) is None


def test_fetch_returns_every_line():
    provider = _provider()

    async def run():
        fund = await provider.lookup("IE00B4L5Y983")
        return await provider.fetch(fund)

    composition = asyncio.run(run())
    assert composition.as_of == date(2026, 11, 25)
    apple = composition.lines[0]
    assert (apple.isin, apple.ticker, apple.weight, apple.country, apple.sector, apple.exchange) == (
        "US0378331005", "AAPL", 6.13244, "USA", "Technologie", "NASDAQ")
    assert len(composition.lines) == 28
    cash = [line for line in composition.lines if line.asset_class in ("Cash", "Money Market")]
    assert len(cash) == 3
    assert not any(is_equity_line(line.asset_class, None) for line in cash)
    assert cash[0].isin is None and cash[0].exchange is None


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(200, text="<html>maintenance</html>"),
        httpx.Response(200, json={"componentsByNameMap": {}}),
        httpx.Response(200, json=[]),
    ],
    ids=["http-500", "html", "sans-holdings", "liste"],
)
def test_fetch_unusable_answer_is_unavailable(response):
    def handler(request: httpx.Request) -> httpx.Response:
        if "product-screener" in str(request.url):
            return _serve(request)
        return response

    provider = _provider(handler)

    async def run():
        fund = await provider.lookup("IE00B4L5Y983")
        await provider.fetch(fund)

    with pytest.raises(ProviderUnavailable):
        asyncio.run(run())


def test_catalog_failure_is_not_retried_immediately():
    seen: list[httpx.Request] = []

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("injoignable", request=request)

    provider = _provider(down, seen)

    async def run():
        for _ in range(3):
            with pytest.raises(ProviderUnavailable):
                await provider.lookup("IE00B4L5Y983")

    asyncio.run(run())
    assert len(seen) == 1
