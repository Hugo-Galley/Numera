"""justETF (repli) : agrégats pays, secteurs et dix premières lignes lus dans la page d'un fonds."""
import asyncio
from datetime import date

import httpx
import pytest
from freezegun import freeze_time

from app.integrations.etf_providers.base import ProviderFund, ProviderUnavailable
from app.integrations.etf_providers.justetf import JustEtf
from tests.investissement.etf_provider_helpers import fixture_bytes, mock_factory

ISIN = "IE000BI8OT95"


def _serve(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=fixture_bytes("justetf_IE000BI8OT95.html"))


def _lookup(isin=ISIN, handler=_serve, seen=None):
    return asyncio.run(JustEtf(client_factory=mock_factory(handler, seen)).lookup(isin))


def _fetch(handler=_serve):
    fund = ProviderFund("justetf", ISIN, ISIN, "F", None, "unknown", None)
    return asyncio.run(JustEtf(client_factory=mock_factory(handler)).fetch(fund))


def test_lookup_reads_name_and_index():
    seen: list[httpx.Request] = []
    fund = _lookup(seen=seen)
    assert (fund.provider, fund.ref, fund.isin, fund.name, fund.replication, fund.index_name) == (
        "justetf", ISIN, ISIN, "Amundi Core MSCI World UCITS ETF Acc", "unknown", "MSCI World")
    assert seen[0].url.params["isin"] == ISIN


def test_lookup_of_a_page_without_composition_returns_none():
    assert _lookup(handler=lambda _request: httpx.Response(200, text="<html><body>Recherche ETF</body></html>")) is None


def test_lookup_never_sends_anything_but_an_isin():
    seen: list[httpx.Request] = []
    assert _lookup("mon portefeuille", seen=seen) is None
    assert seen == []


def test_isin_is_never_guessed_from_a_ticker():
    assert asyncio.run(JustEtf(client_factory=mock_factory(_serve)).find_isin_by_ticker("MWRD.PA")) is None


@freeze_time("2026-11-27 08:00:00")
def test_fetch_returns_aggregates_without_lines():
    composition = _fetch()
    assert composition.lines == []
    assert composition.as_of == date(2026, 9, 23)  # date publiée (« État : 23/09/2026 »), pas celle de la lecture
    assert composition.countries == {"USA": 71.05, "JPN": 5.79, "GBR": 3.62, "CAN": 3.31}
    assert composition.sectors == {"Technologie": 37.47, "Finance": 17.4, "Industrie": 9.42, "Santé": 8.96}
    assert len(composition.top_holdings) == 10
    assert composition.top_holdings[0] == {"name": "NVIDIA Corp.", "ticker": None, "isin": "US67066G1040", "weight": 5.69}


def test_page_without_published_date_has_no_date():
    page = fixture_bytes("justetf_IE000BI8OT95.html").decode().replace("État : 23/09/2026", "")
    assert _fetch(lambda _request: httpx.Response(200, text=page)).as_of is None


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503),
        httpx.Response(404),
        httpx.Response(200, text="<html>maintenance</html>"),
        httpx.Response(200, text='<tr data-testid="etf-holdings_countries_row"><td>France</td></tr>'),
    ],
    ids=["http-503", "http-404", "sans-tableau", "tableau-modifie"],
)
def test_unusable_page_is_unavailable(response):
    with pytest.raises(ProviderUnavailable):
        _fetch(lambda _request: response)


# Balisage réel de l'en-tête (page de FR0011550185, 27/11/2026) ; le jeu réduit ne le contient pas
_REPLICATION = ('<div class="vallabel" data-testid="etf-profile-header_replication-label">Réplication </div>\n'
                '<div class="val bold" data-testid="etf-profile-header_replication-value">{}</div>')


@pytest.mark.parametrize(
    ("published", "expected"),
    [("Synthétique", "synthetic"), ("Physique", "physical"), ("Autre chose", "unknown")],
)
def test_lookup_reads_the_published_replication(published, expected):
    page = _REPLICATION.format(published) + fixture_bytes("justetf_IE000BI8OT95.html").decode()
    provider = JustEtf(client_factory=mock_factory(lambda _request: httpx.Response(200, text=page)))
    assert asyncio.run(provider.lookup("IE000BI8OT95")).replication == expected
