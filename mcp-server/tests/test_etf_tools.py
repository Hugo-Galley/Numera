"""Outils ETF : un synthétique montre son exposition (via l'ETF de référence), sa réplication, sa date et sa couverture."""
import os

os.environ.setdefault("MCP_API_TOKEN", "nmr_test")

import httpx
import pytest

CW8 = {
    "id": 3, "name": "Amundi MSCI World Swap", "ticker": "CW8.PA", "isin": "LU1681043599", "is_system": True,
    "countries": {}, "sectors": {}, "top_holdings": [], "composition_sources": {},
    "composition_refreshed_at": "2026-11-27T06:00:00", "provider": "amundi", "replication": "synthetic",
    "index_name": "MSCI World", "exposure_profile_id": 7, "exposure_profile_name": "iShares Core MSCI World UCITS ETF",
    "composition_as_of": "2026-11-25", "coverage_pct": 99.8, "lines_count": 0,
}
WORLD = {
    "id": 7, "name": "iShares Core MSCI World UCITS ETF", "ticker": "IE00B4L5Y983", "isin": "IE00B4L5Y983",
    "is_system": False, "countries": {"USA": 71.2, "JPN": 5.4}, "sectors": {"Technologie": 26.1},
    "top_holdings": [{"name": "APPLE INC", "ticker": "AAPL", "weight": 4.9}],
    "composition_sources": {"countries": "ishares", "sectors": "ishares", "top_holdings": "ishares"},
    "composition_refreshed_at": "2026-11-27T06:00:00", "provider": "ishares", "replication": "physical",
    "index_name": "MSCI World", "exposure_profile_id": None, "exposure_profile_name": None,
    "composition_as_of": "2026-11-25", "coverage_pct": 99.8, "lines_count": 1273,
}
YAHOO = {**WORLD, "id": 9, "name": "Fonds Yahoo", "provider": "yahoo", "composition_as_of": None, "coverage_pct": 60.0,
         "lines_count": 0, "replication": "unknown", "index_name": None}


@pytest.fixture()
def etf():
    """Import tardif : `test_http` configure le transport avant le premier import de `numera_mcp`."""
    from numera_mcp.tools import etf as module
    return module


@pytest.fixture()
def backend(monkeypatch):
    from numera_mcp import api_client

    seen: list[str] = []
    by_path = {"/etf-profiles": [CW8, WORLD, YAHOO], "/etf-profiles/3": CW8, "/etf-profiles/7": WORLD,
               "/etf-profiles/9": YAHOO}

    def serve(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.method} {request.url.path}")
        return httpx.Response(200, json=by_path[request.url.path])

    monkeypatch.setattr(api_client.api, "_client", httpx.Client(transport=httpx.MockTransport(serve)))
    monkeypatch.setattr(api_client.api, "_static_token", "nmr_test")  # quel que soit le transport importé en premier
    return seen


def test_synthetic_shows_its_exposure_through_the_reference(backend, etf):
    text = etf.get_etf_profile(3)
    assert "synthétique" in text
    assert "MSCI World" in text
    assert "iShares Core MSCI World UCITS ETF" in text
    assert "USA : 71.2%" in text  # chiffres de la référence
    assert "APPLE INC" in text
    assert "2026-11-25" in text
    assert "99.8 %" in text
    assert backend == ["GET /etf-profiles/3", "GET /etf-profiles/7"]  # lecture seule


def test_physical_profile_shows_lines_date_and_coverage(backend, etf):
    text = etf.get_etf_profile(7)
    assert "physique" in text
    assert "1273 lignes" in text
    assert "composition au 2026-11-25" in text
    assert backend == ["GET /etf-profiles/7"]


def test_undated_source_is_not_given_a_date(backend, etf):
    text = etf.get_etf_profile(9)
    assert "Yahoo Finance" in text
    assert "composition au" not in text
    assert "date non publiée" in text


def test_list_shows_replication_exposure_and_coverage(backend, etf):
    text = etf.list_etf_profiles()
    header, _, cw8, *_ = text.split("\n\n", 1)[1].splitlines()
    assert "exposition_via" in header
    assert "synthétique" in cw8 and "iShares Core MSCI World UCITS ETF" in cw8
    assert "2026-11-25" in cw8 and "99.8 %" in cw8
