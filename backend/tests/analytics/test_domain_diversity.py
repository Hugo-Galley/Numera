"""Calculs purs du scanner de diversification."""
import pytest

from app.domain.diversity import UNKNOWN_LABEL, hhi_score, normalize_company_key, score_label, spread_weights


def test_hhi_score_single_asset_is_low():
    assert hhi_score([100.0]) == 10.0


def test_hhi_score_empty_is_50():
    assert hhi_score([]) == 50.0
    assert hhi_score([0.0, 0.0]) == 50.0


def test_spread_weights_uncovered_goes_to_unknown():
    target: dict[str, float] = {}
    spread_weights(target, '{"Technologie": 60}', 1000.0)
    assert target == {"Technologie": 600.0, UNKNOWN_LABEL: 400.0}
    spread_weights(target, "pas du json", 100.0)
    assert target[UNKNOWN_LABEL] == 500.0


def test_normalize_company_key_strips_suffix():
    assert normalize_company_key(None, "Apple Inc") == "NAME:apple"
    assert normalize_company_key("AAPL.MX", None) == "TICKER:AAPL"
    assert normalize_company_key(None, None) == "RAW:unknown"


def test_score_label_thresholds():
    assert [score_label(s) for s in (30, 50, 70, 90)] == [
        "Concentration critique", "Concentration modérée", "Bonne diversification globale", "Excellente diversification"]


def _vh(ticker, name, value, isin=None, quote_type="EQUITY"):
    return {"ticker": ticker, "name": name, "value_eur": value, "isin": isin, "quote_type": quote_type}


def _security(isin, country, sector):
    from app.models.security import Security
    return Security(isin=isin, ticker="X", name="X", country=country, sector=sector, source="yahoo")


def test_direct_stock_takes_country_and_sector_from_securities():
    from app.domain.diversity import look_through
    apple = _vh("AAPL", "Apple Inc", 1000.0, isin="US0378331005")
    out = look_through([apple], lambda vh: None, {"US0378331005": _security("US0378331005", "USA", "Technologie")})
    assert out.countries == {"USA": 1000.0}
    assert out.sectors == {"Technologie": 1000.0}


def test_direct_stock_without_security_is_non_renseigne():
    from app.domain.diversity import look_through
    out = look_through([_vh("ZZZ", "Inconnue", 500.0)], lambda vh: None, {})
    assert out.countries == {UNKNOWN_LABEL: 500.0}
    assert out.sectors == {UNKNOWN_LABEL: 500.0}


def test_direct_stock_security_with_missing_fields_is_non_renseigne():
    from app.domain.diversity import look_through
    out = look_through([_vh("ZZZ", "Inconnue", 500.0, isin="FR0000000001")], lambda vh: None,
                       {"FR0000000001": _security("FR0000000001", None, None)})
    assert out.countries == {UNKNOWN_LABEL: 500.0}
    assert out.sectors == {UNKNOWN_LABEL: 500.0}


def test_crypto_is_a_separate_sector_without_country_or_company():
    from app.domain.diversity import CRYPTO_LABEL, look_through
    out = look_through([_vh("BTC-USD", "Bitcoin USD", 700.0, quote_type="CRYPTOCURRENCY")], lambda vh: None, {})
    assert CRYPTO_LABEL == "Crypto-actifs"
    assert out.sectors == {CRYPTO_LABEL: 700.0}
    assert out.countries == {}
    assert out.companies == {}


def test_company_key_prefers_isin():
    assert normalize_company_key("AAPL", "Apple Inc", "US0378331005") == "ISIN:US0378331005"
    assert normalize_company_key("AAPL", "Apple Inc") == "TICKER:AAPL"


def test_direct_and_etf_apple_with_same_isin_are_one_company():
    import json

    from app.domain.diversity import look_through
    etf = _etf(top=json.dumps([{"name": "Apple Inc.", "ticker": "AAPL", "isin": "US0378331005", "weight": 10.0}]))
    holdings = [_vh("ETF1", "Mon ETF", 1000.0, quote_type="ETF"), _vh("AAPL", "Apple", 200.0, isin="US0378331005")]
    out = look_through(holdings, lambda vh: etf if vh["ticker"] == "ETF1" else None, {})
    assert list(out.companies) == ["ISIN:US0378331005"]
    comp = out.companies["ISIN:US0378331005"]
    assert comp["direct_value_eur"] == 200.0 and comp["indirect_value_eur"] == 100.0


def _etf(profile_id=1, name="ETF", countries="{}", sectors="{}", top="[]", sources="{}"):
    from app.models.etf_profile import EtfProfile
    return EtfProfile(id=profile_id, name=name, ticker=name, aliases="[]", countries=countries, sectors=sectors,
                      top_holdings=top, composition_sources=sources)


def _line(name, weight, isin=None, country="USA", sector="Technologie", asset_class="Equity", ticker=None):
    from app.domain.etf_composition import EtfConstituentRow
    return EtfConstituentRow(isin, ticker, name, weight, country, sector, asset_class)


def _world_lines():
    """Les 28 lignes réelles du jeu de test iShares MSCI World."""
    import asyncio

    import httpx

    from app.integrations.etf_providers.base import ProviderFund
    from app.integrations.etf_providers.ishares import IShares
    from tests.investissement.etf_provider_helpers import fixture_bytes, mock_factory

    provider = IShares(client_factory=mock_factory(
        lambda _: httpx.Response(200, content=fixture_bytes("ishares_holdings_251882.json"))))
    fund = ProviderFund("ishares", "251882", "IE00B4L5Y983", "World", None, "physical", "MSCI World")
    return asyncio.run(provider.fetch(fund)).lines


def _one_etf(profile, lines, value=1000.0, source=None):
    from app.domain.diversity import Exposure, look_through
    return look_through([_vh("ETF1", "Mon ETF", value, quote_type="ETF")], lambda vh: profile, {},
                        lambda p: Exposure(source or p, lines))


def test_every_line_of_the_etf_is_looked_through():
    from app.domain.diversity import CASH_LABEL
    from app.domain.etf_normalize import is_equity_line

    lines = _world_lines()
    out = _one_etf(_etf(), lines)

    apple = out.companies["ISIN:US0378331005"]
    assert apple["indirect_value_eur"] == pytest.approx(1000.0 * 6.13244 / 100)
    assert apple["sources"] == [{"source": "ETF1", "pct_in_source": 6.13, "value_eur": 61.32}]
    equities = [x for x in lines if is_equity_line(x.asset_class, None)]
    cash = sum(x.weight for x in lines if not is_equity_line(x.asset_class, None))
    assert len(out.companies) == len({x.isin for x in equities}) > 10
    assert out.countries["USA"] == pytest.approx(10 * sum(x.weight for x in equities if x.country == "USA"))
    assert out.sectors["Technologie"] == pytest.approx(10 * sum(x.weight for x in equities if x.sector == "Technologie"))
    assert CASH_LABEL == "Liquidités et dérivés"
    if cash > 0:
        assert out.countries[CASH_LABEL] == out.sectors[CASH_LABEL] == pytest.approx(10 * cash)
    for spread in (out.countries, out.sectors):
        assert sum(spread.values()) == pytest.approx(1000.0, abs=5.0)  # la part non couverte est « Non renseigné »


def test_cash_and_derivatives_have_no_country_sector_or_company():
    from app.domain.diversity import CASH_LABEL
    out = _one_etf(_etf(), [
        _line("Apple", 90.0, "US0378331005"),
        _line("USD CASH", 3.0, asset_class="Cash"),
        _line("S&P FUT", -1.0, asset_class="Futures"),
    ])
    assert out.countries == {"USA": 900.0, CASH_LABEL: pytest.approx(20.0), UNKNOWN_LABEL: pytest.approx(80.0)}
    assert out.sectors == {"Technologie": 900.0, CASH_LABEL: pytest.approx(20.0), UNKNOWN_LABEL: pytest.approx(80.0)}
    assert list(out.companies) == ["ISIN:US0378331005"]


def test_negative_cash_is_not_shown_and_unknown_country_stays_unknown():
    out = _one_etf(_etf(), [
        _line("Apple", 99.8, "US0378331005", country=None, sector=UNKNOWN_LABEL),
        _line("FX", -0.5, asset_class="FX"),
    ])
    assert out.countries == out.sectors == {UNKNOWN_LABEL: pytest.approx(1000.0)}


def test_two_lines_of_a_company_in_one_etf_are_one_source():
    out = _one_etf(_etf(), [_line("Apple", 4.0, "US0378331005"), _line("Apple", 1.0, "US0378331005")])
    (company,) = out.companies.values()
    assert company["sources"] == [{"source": "ETF1", "pct_in_source": 5.0, "value_eur": 50.0}]


def test_manual_fields_win_over_the_lines():
    profile = _etf(countries='{"FRA": 100.0}', sources='{"countries": "manual"}',
                   top='[{"name": "Saisie", "weight": 50.0}]')
    out = _one_etf(profile, [_line("Apple", 100.0, "US0378331005")])
    assert out.countries == {"FRA": 1000.0}
    assert out.sectors == {"Technologie": 1000.0}
    assert list(out.companies) == ["ISIN:US0378331005"]  # le top saisi n'est pas marqué manuel : les lignes comptent


def test_synthetic_is_decomposed_through_its_exposure_profile_but_keeps_its_name():
    synthetic = _etf(1, "CW8")
    reference = _etf(2, "MSCI World", sources='{"countries": "ishares"}')
    out = _one_etf(synthetic, [_line("Apple", 100.0, "US0378331005")], source=reference)
    assert out.countries == {"USA": 1000.0}
    assert out.etfs[0]["profile_name"] == "CW8"
    assert out.compositions[1]["profile_name"] == "CW8"
    assert out.compositions[1]["sources"] == {"countries": "ishares"}


def test_without_lines_the_aggregates_of_the_exposure_profile_are_used():
    reference = _etf(2, "Ref", countries='{"JPN": 100.0}')
    out = _one_etf(_etf(1, "Synth", sectors='{"Finance": 100.0}', sources='{"sectors": "manual"}'), [], source=reference)
    assert out.countries == {"JPN": 1000.0}
    assert out.sectors == {"Finance": 1000.0}


def test_direct_stock_found_by_ticker_merges_with_the_etf_line():
    from app.domain.diversity import Exposure, look_through
    etf = _etf()
    holdings = [_vh("ETF1", "Mon ETF", 1000.0, quote_type="ETF"), _vh("AAPL", "Apple", 200.0)]
    out = look_through(holdings, lambda vh: etf if vh["ticker"] == "ETF1" else None,
                       {"AAPL": _security("US0378331005", "USA", "Technologie")},
                       lambda p: Exposure(p, [_line("APPLE INC", 10.0, "US0378331005")]))
    (company,) = out.companies.values()
    assert (company["direct_value_eur"], company["indirect_value_eur"]) == (200.0, 100.0)
