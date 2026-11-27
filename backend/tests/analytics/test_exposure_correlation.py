"""Matrice de corrélation des expositions : par les cours, sinon par la composition (spec sur-exposition § 3)."""
from datetime import date, timedelta

import pytest

from app.domain.etf_composition import EtfConstituentRow
from app.domain.exposure.correlation import composition_vector, correlation_matrix


def _returns(seed: int, weeks: int = 60) -> dict[date, float]:
    start = date(2024, 1, 5)
    return {start + timedelta(weeks=i): ((i * seed) % 7 - 3) / 100 for i in range(weeks)}


def test_pair_with_prices_uses_pearson():
    a = _returns(3)
    matrix = correlation_matrix(["A", "B"], {"A": a, "B": a}, {})

    assert matrix.keys == ("A", "B")
    assert matrix.rho[0][1] == pytest.approx(1.0)
    assert matrix.source[0][1] == "prices"
    assert matrix.rho[0][0] == 1.0


def test_pair_without_prices_falls_back_to_composition():
    vectors = {"A": {"c:USA": 100.0}, "B": {"c:USA": 60.0, "c:JPN": 80.0}}
    matrix = correlation_matrix(["A", "B"], {"B": _returns(3)}, vectors)

    assert matrix.source[0][1] == "composition"
    assert matrix.source[1][0] == "composition"
    assert matrix.rho[0][1] == pytest.approx(0.6)


def test_pair_without_any_data_is_unknown():
    matrix = correlation_matrix(["A", "B"], {}, {"A": {}, "B": {"c:USA": 1.0}})

    assert matrix.source[0][1] == "unknown"
    assert matrix.rho[0][1] is None


def test_direct_stock_vector():
    vector = composition_vector("direct", [], "US0378331005", "AAPL", "USA", "Technologie")

    assert vector == {"isin:US0378331005": 100, "c:USA": 100, "s:Technologie": 100}


def test_direct_stock_vector_without_metadata_uses_ticker():
    assert composition_vector("direct", [], None, "aapl", None, "Non renseigné") == {"isin:AAPL": 100}


def test_crypto_vector():
    assert composition_vector("crypto", [], None, "btc-usd", None, None) == {"crypto:BTC-USD": 100}


def test_fund_vector_from_equity_lines_only():
    lines = [
        EtfConstituentRow("US0378331005", "AAPL", "Apple", 5.0, "USA", "Technologie", "Actions"),
        EtfConstituentRow(None, "MSFT", "Microsoft", 4.0, "USA", "Technologie", "Actions"),
        EtfConstituentRow(None, None, "Cash EUR", 1.0, None, "Liquidités", "Liquidités"),
    ]

    vector = composition_vector("fund", lines, "IE00B4L5Y983", "IWDA.AS", None, None)

    assert vector == {
        "isin:US0378331005": 5.0,
        "isin:MSFT": 4.0,
        "c:USA": 9.0,
        "s:Technologie": 9.0,
    }
