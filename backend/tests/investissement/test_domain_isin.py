"""Résolution stricte d'un ISIN depuis un ticker : mieux vaut aucun ISIN qu'un ISIN faux."""

import pytest

from app.domain.isin import IsinCandidate, exchange_of, is_valid_isin, isin_from_symbol, pick_isin

AAPL = "US0378331005"
THALES = "FR0000121329"
NOKIA = "FI0009000681"


def test_is_valid_isin_checks_format_and_check_digit():
    assert is_valid_isin("US0378331005")
    assert not is_valid_isin("US0378331006")
    assert not is_valid_isin("us0378331005")
    assert not is_valid_isin("US037833100")
    assert not is_valid_isin("")


def test_isin_from_symbol():
    assert isin_from_symbol("IE0002XZSHO1.SG") == "IE0002XZSHO1"
    assert isin_from_symbol("0P0001HI7F.F") is None
    assert isin_from_symbol("AAPL") is None


@pytest.mark.parametrize(
    ("symbol", "place"),
    [
        ("AAPL", "US"), ("HO.PA", "PAR"), ("ASML.AS", "AMS"), ("X.BR", "BRU"), ("X.LS", "LIS"),
        ("X.MC", "MAD"), ("X.T", "TYO"), ("X.HK", "HKG"), ("X.AX", "ASX"), ("X.ST", "STO"),
        ("X.CO", "CPH"), ("NOKIA.HE", "HEL"), ("X.OL", "OSL"), ("X.VI", "VIE"), ("X.IR", "DUB"),
        ("X.TA", "TLV"), ("X.SI", "SGX"), ("X.DE", "GER"), ("X.F", "GER"), ("X.SG", "GER"),
        ("X.L", "LON"), ("X.MI", "MIL"), ("X.SW", "SWX"), ("X.TO", "TOR"), ("x.pa", "PAR"),
    ],
)
def test_exchange_of(symbol, place):
    assert exchange_of(symbol) == place


def test_exchange_of_unknown_suffix_is_none():
    assert exchange_of("X.ZZ") is None


def test_pick_isin_exact_match():
    assert pick_isin("AAPL", [IsinCandidate(AAPL, "AAPL", "NASDAQ")]) == AAPL


def test_resolve_refuses_cross_exchange_match():
    assert pick_isin("ISRG.PA", [IsinCandidate("US46120E6023", "ISRG", "NASDAQ")]) is None


def test_pick_isin_two_distinct_compatible_isins_is_none():
    cands = [IsinCandidate(AAPL, "AAPL", "NASDAQ"), IsinCandidate("US5949181045", "AAPL", "NASDAQ")]
    assert pick_isin("AAPL", cands) is None


def test_pick_isin_same_isin_listed_twice_is_resolved():
    cands = [IsinCandidate(AAPL, "AAPL", "NASDAQ"), IsinCandidate(AAPL, "AAPL", "Cboe BZX")]
    assert pick_isin("AAPL", cands) == AAPL


def test_pick_isin_ticker_must_match_case_insensitively_without_suffix():
    assert pick_isin("AAPL", [IsinCandidate(AAPL, " aapl ", "NASDAQ")]) == AAPL
    assert pick_isin("AAPL", [IsinCandidate(AAPL, "MSFT", "NASDAQ")]) is None


def test_pick_isin_unknown_suffix_is_none():
    assert pick_isin("HO.ZZ", [IsinCandidate(THALES, "HO", "Nyse Euronext - Euronext Paris")]) is None


def test_pick_isin_paris_with_provider_exchange():
    cand = IsinCandidate(THALES, "HO", "Nyse Euronext - Euronext Paris")
    assert pick_isin("HO.PA", [cand]) == THALES


def test_pick_isin_nordic_helsinki_resolves():
    cand = IsinCandidate(NOKIA, "NOKIA", "Nasdaq Omx Helsinki Ltd.")
    assert pick_isin("NOKIA.HE", [cand]) == NOKIA


def test_pick_isin_us_symbol_refuses_nasdaq_nordic():
    cand = IsinCandidate("SE0000108656", "AAPL", "Nasdaq Omx Nordic")
    assert pick_isin("AAPL", [cand]) is None


def test_pick_isin_us_symbol_refuses_euronext_paris_despite_nyse_in_name():
    cand = IsinCandidate(THALES, "AAPL", "Nyse Euronext - Euronext Paris")
    assert pick_isin("AAPL", [cand]) is None


@pytest.mark.parametrize(
    ("symbol", "exchange"),
    [
        ("AAPL", "New York Stock Exchange Inc."), ("AAPL", "Nasdaq"), ("AAPL", "Cboe BZX"),
        ("X.T", "Tokyo Stock Exchange"), ("X.TO", "Toronto Stock Exchange"), ("X.L", "London Stock Exchange"),
        ("X.DE", "Xetra"), ("X.DE", "Deutsche Boerse Xetra"), ("X.AX", "Asx - All Markets"),
        ("X.SW", "SIX Swiss Exchange"), ("X.CO", "Omx Nordic Exchange Copenhagen A/S"),
        ("X.AS", "Euronext Amsterdam"), ("X.MI", "Borsa Italiana"),
        ("X.HK", "Hong Kong Exchanges And Clearing Ltd"), ("X.MC", "Bolsa De Madrid"),
        ("X.SI", "Singapore Exchange"), ("X.TA", "Tel Aviv Stock Exchange"),
        ("X.BR", "Nyse Euronext - Euronext Brussels"), ("X.OL", "Oslo Bors Asa"),
        ("X.VI", "Wiener Boerse Ag"), ("X.IR", "Irish Stock Exchange - All Market"),
        ("X.LS", "Nyse Euronext - Euronext Lisbon"),
    ],
)
def test_pick_isin_provider_exchange_names(symbol, exchange):
    # ISIN d'un pays quelconque (JE...) : seule la place du fournisseur doit décider.
    isin = "GB0002634946"
    assert pick_isin(symbol, [IsinCandidate(isin, "X" if symbol.startswith("X") else "AAPL", exchange)]) == isin


def test_pick_isin_without_provider_exchange_falls_back_on_isin_country():
    assert pick_isin("HO.PA", [IsinCandidate(THALES, "HO", None)]) == THALES
    assert pick_isin("HO.PA", [IsinCandidate(AAPL, "HO", None)]) is None
    assert pick_isin("AAPL", [IsinCandidate("CA0679011084", "AAPL", None)]) == "CA0679011084"


def test_pick_isin_unknown_venue_is_refused_even_with_us_isin():
    assert pick_isin("AAPL", [IsinCandidate(AAPL, "AAPL", "Some Venue")]) is None


def test_pick_isin_ignores_invalid_isin():
    assert pick_isin("AAPL", [IsinCandidate("US0378331006", "AAPL", "NASDAQ")]) is None


def test_exchange_alone_decides_when_provider_exchange_given():
    assert pick_isin("T", [IsinCandidate("CA87971M1032", "T", "Toronto Stock Exchange")]) is None


@pytest.mark.parametrize("exchange", ["Nasdaq Stockholm", "Nasdaq Dubai", "Cboe Europe", "Nasdaq Omx Baltic", "Nyse Arca Europe"])
def test_us_place_is_a_whitelist(exchange):
    assert pick_isin("AAPL", [IsinCandidate(AAPL, "AAPL", exchange)]) is None


@pytest.mark.parametrize("exchange", ["NASDAQ", "Nasdaq Stock Market", "Nasdaq Global Select", "New York Stock Exchange Inc.", "NYSE Arca", "Cboe BZX"])
def test_us_place_whitelist_accepts(exchange):
    assert pick_isin("AAPL", [IsinCandidate(AAPL, "AAPL", exchange)]) == AAPL


def test_share_class_tickers_are_not_truncated():
    assert pick_isin("BRK.B", [IsinCandidate("US0846707026", "BRK", "New York Stock Exchange Inc.")]) is None
    assert pick_isin("BRK.B", [IsinCandidate("US0846707026", "BRK.B", "New York Stock Exchange Inc.")]) == "US0846707026"
    assert pick_isin("RDS.A.L", [IsinCandidate("GB00B03MLX29", "RDS", "London Stock Exchange")]) is None
    assert pick_isin("RDS.A.L", [IsinCandidate("GB00B03MLX29", "RDS.A", "London Stock Exchange")]) == "GB00B03MLX29"


def test_nordic_city_in_exchange_decides():
    assert pick_isin("X.HE", [IsinCandidate("DK0010244425", "X", "Omx Nordic Exchange Copenhagen A/S")]) is None
    assert pick_isin("X.CO", [IsinCandidate("DK0010244425", "X", "Omx Nordic Exchange Copenhagen A/S")]) == "DK0010244425"


def test_generic_nordic_exchange_uses_isin_country():
    assert pick_isin("NOKIA.HE", [IsinCandidate(NOKIA, "NOKIA", "Nasdaq Omx Nordic")]) == NOKIA
    assert pick_isin("X.HE", [IsinCandidate("SE0000108656", "X", "Nasdaq Omx Nordic")]) is None


def test_isin_with_trailing_newline_is_invalid_and_empty_ticker_is_none():
    assert not is_valid_isin("US0378331005\n")
    assert pick_isin(".PA", [IsinCandidate(THALES, "", "Nyse Euronext - Euronext Paris")]) is None
    assert pick_isin("", [IsinCandidate(AAPL, "", "NASDAQ")]) is None
