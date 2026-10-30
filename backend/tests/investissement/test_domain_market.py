"""Règles pures des cotations et de la correspondance des profils ETF (sans base)."""
from app.domain.etf_profiles import match_profile, profile_matches_query
from app.domain.market import extract_asset_clean_name, guess_quote_currency, normalize_price
from app.models.etf_profile import EtfProfile


def test_guess_quote_currency():
    assert guess_quote_currency("IE0002XZSHO1.SG") == "EUR"
    assert guess_quote_currency("BTC-EUR") == "EUR"
    assert guess_quote_currency("VUSA.L") == "GBP"
    assert guess_quote_currency("AAPL") == "USD"


def test_normalize_price_pence():
    assert normalize_price(1234.0, "GBp") == (12.34, "GBP")
    assert normalize_price(10, "") == (10.0, "EUR")


def test_extract_asset_clean_name():
    assert extract_asset_clean_name("Achat Apple") == "Apple"
    assert extract_asset_clean_name("Dividende de LVMH (acompte)") == "LVMH"
    assert extract_asset_clean_name("x") is None


def test_match_profile_by_alias_and_name():
    world = EtfProfile(id=1, ticker="CW8.PA", name="Amundi MSCI World", isin="LU1681043599", aliases='["WPEA"]')
    sp = EtfProfile(id=2, ticker="ESE.PA", name="BNP Paribas Easy S&P 500", isin=None, aliases="[]")
    profiles = [world, sp]
    assert match_profile(profiles, "WPEA.PA") is world
    assert match_profile(profiles, "ZZZ", isin="lu1681043599") is world
    assert match_profile(profiles, "ZZZ", name="BNP Paribas Easy S&P 500 UCITS") is sp
    assert match_profile(profiles, "ZZZ", name="") is None
    assert profile_matches_query(world, "wpea") and not profile_matches_query(sp, "wpea")
