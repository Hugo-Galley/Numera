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
