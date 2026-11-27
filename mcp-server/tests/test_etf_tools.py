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


def _line(i):
    return {"name": f"Société {i}", "ticker": f"T{i}", "isin": None, "weight": round(10 - i / 10, 2),
            "country": "USA", "sector": "Technologie", "asset_class": "Equity"}


SHEET = {
    "profile": CW8, "exposure_profile_id": 7, "exposure_profile_name": "iShares Core MSCI World UCITS ETF",
    "provider": "ishares", "composition_as_of": "2026-11-25", "coverage_pct": 99.8, "lines_count": 61,
    "has_full_list": True, "held_value_eur": 1234.5, "countries": [], "sectors": [],
    "lines": [{**_line(0), "name": "Apple", "ticker": "AAPL", "isin": "US0378331005", "exposure_eur": 123.45}]
    + [_line(i) for i in range(1, 61)],
    "top_holdings": [],
}
PARTIAL = {**SHEET, "profile": YAHOO, "exposure_profile_id": None, "exposure_profile_name": None, "provider": "yahoo",
           "composition_as_of": None, "lines_count": 0, "has_full_list": False, "lines": [],
           "top_holdings": [{"name": "APPLE INC", "ticker": "AAPL", "weight": 4.9}]}

# Top 10 saisi à la main : une entrée sans nom, une sans poids
INCOMPLETE = {**PARTIAL, "top_holdings": [{"ticker": "NVDA", "weight": 3.0}, {"name": "Sans poids"}]}


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
               "/etf-profiles/9": YAHOO, "/etf-profiles/3/constituents": SHEET,
               "/etf-profiles/9/constituents": PARTIAL, "/etf-profiles/11/constituents": INCOMPLETE}

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


def test_constituents_show_identity_source_and_first_lines(backend, etf):
    text = etf.get_etf_constituents(3)
    for expected in ("Amundi MSCI World Swap", "LU1681043599", "iShares", "composition au 2026-11-25", "99.8 %",
                     "MSCI World via iShares Core MSCI World UCITS ETF", "1,234.50 €", "61 lignes au total", "Apple"):
        assert expected in text, expected
    assert "Société 49" in text and "Société 50" not in text  # 50 premières par défaut
    assert backend == ["GET /etf-profiles/3/constituents"]  # lecture seule


@pytest.mark.parametrize("search", ["appl", "aapl", "us0378331005"])
def test_constituents_search_by_name_ticker_or_isin(backend, etf, search):
    text = etf.get_etf_constituents(3, search=search)
    assert "Apple" in text and "Société 1 " not in text
    assert "1 ligne trouvée" in text and "61 lignes au total" in text


def test_constituents_limit_applies(backend, etf):
    text = etf.get_etf_constituents(3, limit=2)
    assert "Société 1" in text and "Société 2" not in text


def test_constituents_without_full_list_say_so(backend, etf):
    text = etf.get_etf_constituents(9)
    assert "liste complète indisponible" in text
    assert "APPLE INC" in text and "date non publiée" in text


def test_constituents_show_the_exposure_computed_by_the_backend(backend, etf):
    text = etf.get_etf_constituents(3, search="apple")
    assert "exposition" in text and "123.45 €" in text


def test_constituents_with_an_incomplete_top_10_still_answer(backend, etf):
    text = etf.get_etf_constituents(11)
    assert not text.startswith("❌"), text
    assert "NVDA" in text and "Sans poids" in text


SCANNER = {
    "score": 62.4, "score_label": "Bonne diversification globale",
    "totals": {"stocks_eur": 1000.0, "epargne_eur": 0.0, "courant_eur": 0.0, "fonds_euros_eur": 0.0,
               "wealth_eur": 1000.0, "holdings_count": 3, "etfs_count": 1},
    "top_underlying_companies": [], "countries": [], "sectors": [], "alerts": [],
    "exposures": [
        {"id": "exp:CW8.PA", "name": "Amundi MSCI World", "kind": "fund", "value_eur": 800.0, "weight_pct": 80.0,
         "supports": [{"account_id": 1, "account_name": "PEA", "ticker": "CW8.PA", "value_eur": 500.0},
                      {"account_id": 2, "account_name": "CTO", "ticker": "IWDA.AS", "value_eur": 300.0}]},
    ],
    "concentration": {"effective_bets": 3.2, "exposures_count": 11,
                      "blocks": [{"members": ["Bitcoin USD", "Ethereum USD"], "weight_pct": 7.0, "mean_rho": 0.86}],
                      "pairs_by_source": {"prices": 40, "composition": 10, "unknown": 5}},
    "market": {"name": "iShares MSCI ACWI", "ticker": "SSAC.L",
               "countries": {"active_share_pct": 12.0, "covered_pct": 90.0, "rows": []},
               "sectors": {"active_share_pct": 18.0, "covered_pct": 95.0,
                           "rows": [{"name": "Technologie", "portfolio_pct": 38.0, "market_pct": 25.0,
                                     "market_pct_is_upper_bound": False, "gap_pts": 13.0}]},
               "companies": {"active_share_pct": 60.0, "covered_pct": 70.0, "rows": []}},
    "stock_picking": [{"key": "exp:AAPL", "name": "Apple", "ticker": "AAPL", "value_eur": 100.0,
                       "indirect_value_eur": 40.0, "indirect_pct": 40.0, "correlation_with_core": 0.9,
                       "source": "prices", "redundant": True}],
    "coverage": {"with_prices_pct": 85.0, "composition_pct": 95.0},
}


def test_diversity_shows_independent_bets_and_market_reference(etf):
    text = etf._format_diversity(SCANNER)

    assert "3.2 paris indépendants sur 11 lignes" in text
    assert "iShares MSCI ACWI (SSAC.L)" in text
    assert "Bitcoin USD + Ethereum USD" in text
    assert "Technologie : 38.0% contre 25.0% (+13.0 pts)" in text
    assert "Apple" in text and "redondant" in text
    assert "PEA" in text and "CTO" in text


def test_diversity_without_market_reference_says_so(etf):
    text = etf._format_diversity({**SCANNER, "market": None})

    assert "Référence de marché indisponible" in text
