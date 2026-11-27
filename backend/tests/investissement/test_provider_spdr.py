"""SPDR (State Street) : catalogue des fonds et composition quotidienne au format xlsx."""
import asyncio
import io
import zipfile
from datetime import date

import httpx
import pytest

from app.domain.etf_normalize import is_equity_line
from app.integrations.etf_providers.base import ProviderFund, ProviderUnavailable
from app.integrations.etf_providers.spdr import Spdr
from app.integrations.xlsx import read_rows
from tests.investissement.etf_provider_helpers import fixture_bytes, mock_factory

ACWI = "IE00B44Z5B48"
_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'


def _xlsx(sheet: str, prolog: str = "") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", f"{prolog}<worksheet {_NS}><sheetData>{sheet}</sheetData></worksheet>")
    return buffer.getvalue()


def _serve(request: httpx.Request) -> httpx.Response:
    if "fundfinder" in str(request.url):
        return httpx.Response(200, content=fixture_bytes("spdr_catalog.json"))
    assert request.url.path.endswith(".xlsx")
    return httpx.Response(200, content=fixture_bytes("spdr_spyy.xlsx"))


def _provider(handler=_serve, seen=None) -> Spdr:
    return Spdr(client_factory=mock_factory(handler, seen))


def _fetch(handler=_serve, seen=None):
    provider = _provider(handler, seen)

    async def run():
        return await provider.fetch(await provider.lookup(ACWI))

    return asyncio.run(run())


def test_read_rows_keeps_the_sheet_line_numbers():
    rows = read_rows(fixture_bytes("spdr_spyy.xlsx"))
    assert rows[3] == ["Holdings As Of:", "25-Nov-2026"]
    assert rows[4] == []
    assert rows[6][:3] == ["US0378331005", "2046251", "Apple Inc."]


def test_read_rows_places_cells_by_their_reference():
    rows = read_rows(_xlsx('<row r="2"><c r="C2" t="inlineStr"><is><t>x</t></is></c><c r="D2"><v>1.5</v></c></row>'))
    assert rows == [[], ["", "", "x", "1.5"]]


@pytest.mark.parametrize(
    "data",
    [
        b"<html>maintenance</html>",
        _xlsx("<row>", prolog=""),
        _xlsx("", prolog='<!DOCTYPE x [<!ENTITY a "aaaa">]>'),
        _xlsx('<row r="999999999"/>'),
    ],
    ids=["pas-un-zip", "xml-casse", "entites", "ligne-hors-limite"],
)
def test_read_rows_rejects_unusable_files(data):
    with pytest.raises(ValueError):
        read_rows(data)


def test_lookup_reads_the_catalog():
    fund = asyncio.run(_provider().lookup(ACWI))
    assert (fund.provider, fund.isin, fund.ticker, fund.replication) == ("spdr", ACWI, "ACWE", "physical")
    assert "MSCI All Country World" in fund.name
    assert fund.index_name == "MSCI ACWI"
    assert fund.ref.startswith("https://www.ssga.com/library-content/") and fund.ref.endswith(".xlsx")


def test_lookup_of_an_unknown_isin_returns_none():
    assert asyncio.run(_provider().lookup("FR0000000000")) is None


def test_catalog_is_downloaded_once():
    seen: list[httpx.Request] = []
    provider = _provider(seen=seen)

    async def twice():
        await provider.lookup(ACWI)
        await provider.lookup("IE00BFY0GT14")

    asyncio.run(twice())
    assert len(seen) == 1


def test_isin_is_never_guessed_from_a_ticker():
    assert asyncio.run(_provider().find_isin_by_ticker("SPPW.DE")) is None


def test_fetch_returns_every_weighted_line():
    composition = _fetch()
    assert composition.as_of == date(2026, 11, 25)
    apple = composition.lines[0]
    assert (apple.isin, apple.name, apple.weight, apple.country, apple.sector, apple.asset_class) == (
        "US0378331005", "Apple Inc.", 5.503913, "USA", "Technologie", "Equity")
    assert len(composition.lines) == 2209
    assert sum(line.weight for line in composition.lines) == pytest.approx(100, abs=0.01)
    assert all(line.weight != 0 for line in composition.lines)
    assert not any("Marketing communication" in line.name for line in composition.lines)


def _row(number: int, *values: str) -> str:
    cells = "".join(f'<c r="{chr(65 + i)}{number}" t="inlineStr"><is><t>{v}</t></is></c>' for i, v in enumerate(values))
    return f'<row r="{number}">{cells}</row>'


def test_lines_without_isin_nor_sector_are_not_equities():
    """Le fichier réel du jeu de test donne « - » comme poids aux devises (écartées) ; une devise pondérée reste hors actions."""
    sheet = (_row(1, "Holdings As Of:", "25-Nov-2026")
             + _row(2, "ISIN", "Security Name", "Percent of Fund", "Trade Country Name", "Sector Classification")
             + _row(3, "Unassigned", "U.S. Dollar", "0.4", "United States", "Unassigned")
             + _row(4, "Unassigned", "mini MSCI EAFE", "-", "United States", "Unassigned"))

    def handler(request: httpx.Request) -> httpx.Response:
        return _serve(request) if "fundfinder" in str(request.url) else httpx.Response(200, content=_xlsx(sheet))

    lines = _fetch(handler).lines
    assert [(line.name, line.isin, line.weight) for line in lines] == [("U.S. Dollar", None, 0.4)]
    assert not is_equity_line(lines[0].asset_class, None)


@pytest.mark.parametrize(
    "ref",
    ["http://www.ssga.com/x.xlsx", "https://exemple.invalid/x.xlsx", "https://www.ssga.com.exemple.invalid/x.xlsx"],
)
def test_fetch_only_calls_the_issuer_site(ref):
    seen: list[httpx.Request] = []
    fund = ProviderFund("spdr", ref, ACWI, "F", None, "physical", None)
    with pytest.raises(ProviderUnavailable):
        asyncio.run(_provider(seen=seen).fetch(fund))
    assert seen == []


@pytest.mark.parametrize(
    "content",
    [b"<html>maintenance</html>", _xlsx(""),
     _xlsx('<row r="1"><c r="A1" t="inlineStr"><is><t>Holdings As Of:</t></is></c><c r="B1" t="inlineStr"><is><t>25-Nov-2026</t></is></c></row>')],
    ids=["html", "feuille-vide", "sans-tableau"],
)
def test_unusable_file_is_unavailable(content):
    def handler(request: httpx.Request) -> httpx.Response:
        if "fundfinder" in str(request.url):
            return _serve(request)
        return httpx.Response(200, content=content)

    with pytest.raises(ProviderUnavailable):
        _fetch(handler)


@pytest.mark.parametrize(
    "response",
    [httpx.Response(503), httpx.Response(200, text="<html/>"), httpx.Response(200, json={"data": {}})],
    ids=["http-503", "html", "sans-fonds"],
)
def test_unusable_catalog_is_unavailable(response):
    with pytest.raises(ProviderUnavailable):
        asyncio.run(_provider(lambda _request: response).lookup(ACWI))
