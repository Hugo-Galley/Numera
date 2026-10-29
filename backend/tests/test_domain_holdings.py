"""Règles pures des positions (sans base)."""
from app.domain.holdings import CostEstimate, is_trade, normalize_ticker


def test_is_trade():
    assert is_trade("achat", "CW8.PA", 2)
    assert not is_trade("achat", "CW8.PA", None)
    assert not is_trade("achat", None, 2)
    assert not is_trade("dividende", "CW8.PA", 2)


def test_normalize_ticker():
    assert normalize_ticker(" cw8.pa ") == "CW8.PA"


def test_cost_estimate_coverage():
    estimate = CostEstimate(ticker="X", asset_name="X", quantity=10, currency="EUR", current_cost=None, estimate=None,
                            buys=1, bought_quantity=6, sold_quantity=1, first_buy=None)
    assert estimate.coverage == 0.5
    estimate.method = "amounts"
    assert estimate.coverage is None
