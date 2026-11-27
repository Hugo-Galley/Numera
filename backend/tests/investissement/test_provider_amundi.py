"""Amundi : fiche d'un fonds et composition complète (API publique JSON)."""
import asyncio
import json
from datetime import date

import httpx
import pytest

from app.domain.isin import IsinCandidate, pick_isin
from app.integrations.etf_providers.amundi import Amundi
from app.integrations.etf_providers.base import ProviderUnavailable
from tests.investissement.etf_provider_helpers import fixture_bytes, mock_factory


def _serve(request: httpx.Request) -> httpx.Response:
    isin = json.loads(request.content)["productIds"][0]
    if isin in ("IE000BI8OT95", "LU1681043599"):
        return httpx.Response(200, content=fixture_bytes(f"amundi_{isin}.json"))
    return httpx.Response(200, json={"products": []})


def _composition(isin: str, handler=_serve, seen=None):
    provider = Amundi(client_factory=mock_factory(handler, seen))

    async def run():
        return await provider.fetch(await provider.lookup(isin))

    return asyncio.run(run())


def _lookup(isin: str, handler=_serve):
    return asyncio.run(Amundi(client_factory=mock_factory(handler)).lookup(isin))


def test_lookup_reads_name_ticker_and_replication():
    fund = _lookup("IE000BI8OT95")
    assert (fund.provider, fund.ref, fund.isin, fund.name, fund.ticker, fund.replication) == (
        "amundi", "IE000BI8OT95", "IE000BI8OT95", "Amundi Core MSCI World UCITS ETF Acc", "MWRD", "physical")


def test_lookup_marks_a_swap_fund_synthetic():
    assert _lookup("LU1681043599").replication == "synthetic"


def test_lookup_of_an_unknown_product_returns_none():
    assert _lookup("FR0000000000") is None


def test_isin_is_never_guessed_from_a_ticker():
    provider = Amundi(client_factory=mock_factory(_serve))
    assert asyncio.run(provider.find_isin_by_ticker("MWRD.PA")) is None


def test_amundi_weights_are_percent():
    composition = _composition("IE000BI8OT95")
    apple = composition.lines[0]
    assert apple.weight == pytest.approx(6.081388, abs=1e-6)
    assert (apple.isin, apple.ticker, apple.name, apple.country, apple.sector, apple.asset_class, apple.exchange) == (
        "US0378331005", "AAPL", "APPLE INC", "USA", "Technologie", "EQUITY_ORDINARY", "NASDAQ")
    assert composition.as_of == date(2026, 11, 24)


def test_lines_without_bloomberg_code_have_no_ticker_nor_exchange():
    line = _composition("LU1681043599").lines[0]
    assert (line.isin, line.ticker, line.exchange) == ("NL0010273215", None, None)


def test_the_composition_request_asks_for_the_bloomberg_code():
    seen: list[httpx.Request] = []
    _composition("IE000BI8OT95", seen=seen)
    assert "bbg" in json.loads(seen[-1].content)["composition"]["compositionFields"]
    assert seen[-1].method == "POST"


def _with_line(**line):
    base = {"date": "2026-11-25", "name": "X", "weight": 0.5, "type": "EQUITY_ORDINARY", "sector": "Energy",
            "countryOfRisk": "Canada", "isin": "CA00206R1029", **line}
    product = {"productId": "IE000BI8OT95", "characteristics": {"SHARE_MARKETING_NAME": "F"},
               "composition": {"compositionData": [{"compositionCharacteristics": base, "weight": base["weight"]}]}}
    return lambda _request: httpx.Response(200, json={"products": [product]})


@pytest.mark.parametrize(
    ("bbg", "symbol", "ticker"),
    [
        ("AAPL UW", "AAPL", "AAPL"), ("ABC UQ", "ABC", "ABC"), ("LLY UN", "LLY", "LLY"), ("T CN", "T.TO", "T"),
        ("T CT", "T.TO", "T"), ("MC FP", "MC.PA", "MC"), ("BP/ LN", "BP.L", "BP"), ("SIE GY", "SIE.DE", "SIE"),
        ("7203 JT", "7203.T", "7203"), ("ASML NA", "ASML.AS", "ASML"), ("ENI IM", "ENI.MI", "ENI"),
        ("NOVN SE", "NOVN.SW", "NOVN"), ("SAN SM", "SAN.MC", "SAN"), ("ABI BB", "ABI.BR", "ABI"),
        ("EDP PL", "EDP.LS", "EDP"), ("NOKIA FH", "NOKIA.HE", "NOKIA"), ("VOLVB SS", "VOLVB.ST", "VOLVB"),
        ("NOVOB DC", "NOVOB.CO", "NOVOB"), ("EQNR NO", "EQNR.OL", "EQNR"), ("OMV AV", "OMV.VI", "OMV"),
        ("BHP AT", "BHP.AX", "BHP"), ("700 HK", "700.HK", "700"), ("BRK/B UN", "BRK.B", "BRK.B"),
    ],
)
def test_exchange_is_derived_from_the_bloomberg_code(bbg, symbol, ticker):
    line = _composition("IE000BI8OT95", _with_line(bbg=bbg)).lines[0]
    assert line.ticker == ticker
    assert pick_isin(symbol, [IsinCandidate(line.isin, line.ticker, line.exchange)]) == line.isin


@pytest.mark.parametrize("bbg", ["T CN", "XYZ QQ"], ids=["toronto", "code-inconnu"])
def test_a_us_symbol_never_takes_a_line_listed_elsewhere(bbg):
    """Sans place, un symbole américain accepterait un ISIN canadien : la place est toujours transmise."""
    line = _composition("IE000BI8OT95", _with_line(bbg=bbg)).lines[0]
    assert pick_isin(line.ticker, [IsinCandidate(line.isin, line.ticker, line.exchange)]) is None


def test_an_internal_identifier_is_not_an_isin():
    line = _composition("IE000BI8OT95", _with_line(isin="_CURRENCY_EUR", type="CASH")).lines[0]
    assert line.isin is None and line.asset_class == "CASH"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(200, text="<html>maintenance</html>"),
        httpx.Response(200, json={"erreur": "x"}),
        httpx.Response(200, json={"products": [{"productId": "IE000BI8OT95", "composition": None}]}),
        httpx.Response(200, json={"products": [{"productId": "IE000BI8OT95", "composition": {"compositionData": [{}]}}]}),
    ],
    ids=["http-500", "html", "sans-produits", "sans-composition", "ligne-vide"],
)
def test_unusable_answer_is_unavailable(response):
    def handler(request: httpx.Request) -> httpx.Response:
        if "composition" in json.loads(request.content):
            return response
        return _serve(request)

    with pytest.raises(ProviderUnavailable):
        _composition("IE000BI8OT95", handler)
