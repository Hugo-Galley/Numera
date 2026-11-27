"""Alertes du scanner de diversification, toutes relatives au marché (spec sur-exposition § 5, 6)."""
import inspect

import pytest

from app.core.i18n import set_language
from app.domain.exposure import alerts
from app.domain.exposure.alerts import market_alerts
from app.domain.exposure.concentration import Block
from app.domain.exposure.identity import ExposureGroup, Holding, Kind
from app.domain.exposure.market_gap import DimensionGap, GapRow


@pytest.fixture(autouse=True)
def _french():
    set_language("fr")
    yield
    set_language("fr")


def _group(key: str, name: str, kind: Kind) -> ExposureGroup:
    holding = Holding(id=1, account_id=1, ticker=key, isin=None, name=name, value_eur=100.0, kind=kind,
                      profile_id=None, exposure_profile_id=None, index_name=None)
    return ExposureGroup(key=key, name=name, kind=kind, value_eur=100.0, holdings=(holding,))


GROUPS = {
    "exp:WLD": _group("exp:WLD", "MSCI World", "fund"),
    "exp:AAPL": _group("exp:AAPL", "Apple", "direct"),
    "exp:BTC-USD": _group("exp:BTC-USD", "Bitcoin USD", "crypto"),
    "exp:ETH-USD": _group("exp:ETH-USD", "Ethereum USD", "crypto"),
}


def _gap(*rows: GapRow) -> DimensionGap:
    return DimensionGap(active_share_pct=10.0, covered_pct=100.0, rows=rows)


def test_no_country_or_sector_name_in_the_alerts_module():
    source = inspect.getsource(alerts)
    for name in ("USA", "États-Unis", "France", "FRA", "Technologie"):
        assert name not in source


def test_overweight_sector_is_one_alert_with_its_dimension():
    gaps = {
        "sectors": _gap(GapRow("Technologie", 38.0, 25.0, False, 13.0), GapRow("Santé", 6.0, 4.5, False, 1.5)),
        "countries": _gap(),
        "companies": _gap(),
    }

    out = market_alerts(gaps, [], GROUPS, [], [])

    assert len(out) == 1
    assert out[0]["category"] == "overweight"
    assert out[0]["dimension"] == "sectors"
    assert out[0]["type"] == "warning"
    assert out[0]["item_name"] == "Technologie"
    assert out[0]["value_pct"] == 38.0
    assert "25" in out[0]["message"]


def test_upper_bound_is_said_in_the_message():
    gaps = {"companies": _gap(GapRow("Apple", 9.0, 0.8, True, 8.2))}

    message = market_alerts(gaps, [], GROUPS, [], [])[0]["message"]

    assert "au plus" in message
    set_language("en")
    assert "at most" in market_alerts(gaps, [], GROUPS, [], [])[0]["message"]


def test_block_with_a_fund_is_not_a_correlated_block_alert():
    blocks = [Block(("exp:WLD", "exp:AAPL"), 80.0, 0.9)]

    assert [a for a in market_alerts(None, blocks, GROUPS, [], []) if a["category"] == "correlated_block"] == []


def test_direct_block_alerts_only_above_its_market_weight():
    """Apple + Microsoft pèsent 7,5 % du marché : un bloc à 10 % est normal, à 15 % il est sur-pondéré."""
    groups = {**GROUPS, "exp:MSFT": _group("exp:MSFT", "Microsoft", "direct")}
    market_weights = {"exp:AAPL": 4.0, "exp:MSFT": 3.5}

    def blocks(weight: float) -> list[dict]:
        out = market_alerts(None, [Block(("exp:AAPL", "exp:MSFT"), weight, 0.85)], groups, [], [],
                            market_weights=market_weights)
        return [a for a in out if a["category"] == "correlated_block"]

    assert blocks(10.0) == []
    assert len(blocks(15.0)) == 1


def test_crypto_block_alerts_even_with_market_weights():
    out = market_alerts(None, [Block(("exp:BTC-USD", "exp:ETH-USD"), 7.0, 0.86)], GROUPS, [], [],
                        market_weights={"exp:AAPL": 4.0})

    assert [a["category"] for a in out] == ["correlated_block"]


def test_not_comparable_dimension_gives_no_overweight():
    gaps = {"countries": DimensionGap(100.0, 100.0, (GapRow("USA", 100.0, 0.0, False, 100.0),), comparable=False)}

    assert market_alerts(gaps, [], GROUPS, [], []) == []


def test_crypto_block_is_a_correlated_block_alert():
    blocks = [Block(("exp:BTC-USD", "exp:ETH-USD"), 7.0, 0.86)]

    out = market_alerts(None, blocks, GROUPS, [], [])

    assert len(out) == 1
    assert out[0]["category"] == "correlated_block"
    assert out[0]["type"] == "warning"
    assert "Bitcoin USD" in out[0]["message"] and "Ethereum USD" in out[0]["message"]
    assert out[0]["value_pct"] == 7.0


def test_redundant_pick_and_overlap():
    picks = [
        {"name": "Apple", "indirect_value_eur": 295.0, "indirect_pct": 82.9, "correlation_with_core": 0.9,
         "redundant": True},
        {"name": "Nvidia", "indirect_value_eur": 0.0, "indirect_pct": 0.0, "correlation_with_core": 0.7,
         "redundant": False},
    ]

    out = market_alerts(None, [], GROUPS, picks, ["Apple"])

    assert [a["category"] for a in out] == ["redundant_pick", "overlap"]
    assert out[0]["item_name"] == "Apple"
    assert out[1]["type"] == "info"
    assert "Apple" in out[1]["message"]


def test_no_market_and_nothing_to_say_is_no_alert():
    assert market_alerts(None, [], GROUPS, [], []) == []
