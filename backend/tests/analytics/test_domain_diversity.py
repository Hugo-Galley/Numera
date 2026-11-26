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


def test_look_through_splits_value_between_direct_lines_and_etfs():
    """La valeur des positions se répartit entre lignes détenues en direct et ETF décomposés."""
    from app.domain.diversity import look_through
    from app.models.etf_profile import EtfProfile

    world = EtfProfile(id=1, name="MSCI World", countries="{}", sectors="{}", top_holdings="[]")
    holdings = [
        {"ticker": "CW8.PA", "name": "Amundi MSCI World", "value_eur": 800.0, "etf_profile_id": 1},
        {"ticker": "TTE.PA", "name": "TotalEnergies", "value_eur": 150.0, "etf_profile_id": None},
        {"ticker": "BLK", "name": "BlackRock", "value_eur": 50.0, "etf_profile_id": None},
        {"ticker": "SOLD", "name": "Ligne vendue", "value_eur": 0.0, "etf_profile_id": None},
    ]
    out = look_through(holdings, lambda vh: world if vh["etf_profile_id"] == 1 else None)

    assert out.direct_value_eur == 200.0
    assert out.etf_value_eur == 800.0
