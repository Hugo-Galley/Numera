"""Calculs purs du scanner de diversification."""
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


def test_direct_and_etf_apple_with_same_isin_are_one_company(monkeypatch):
    import json
    from types import SimpleNamespace

    from app.domain.diversity import look_through
    etf = SimpleNamespace(id=1, name="ETF", countries="{}", sectors="{}", composition_refreshed_at=None, sources="{}",
                          top_holdings=json.dumps([{"name": "Apple Inc.", "ticker": "AAPL", "isin": "US0378331005", "weight": 10.0}]))
    monkeypatch.setattr("app.domain.diversity.load_sources", lambda p: {})
    holdings = [_vh("ETF1", "Mon ETF", 1000.0, quote_type="ETF"), _vh("AAPL", "Apple", 200.0, isin="US0378331005")]
    out = look_through(holdings, lambda vh: etf if vh["ticker"] == "ETF1" else None, {})
    assert list(out.companies) == ["ISIN:US0378331005"]
    comp = out.companies["ISIN:US0378331005"]
    assert comp["direct_value_eur"] == 200.0 and comp["indirect_value_eur"] == 100.0
