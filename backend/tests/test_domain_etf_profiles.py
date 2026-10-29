"""Sources de la composition d'un profil ETF (sans base)."""
import json

from app.domain.etf_profiles import apply_composition, load_sources
from app.models.etf_profile import EtfProfile


def test_apply_composition_keeps_manual_fields():
    profile = EtfProfile(sectors='{"Santé": 100.0}', top_holdings="[]",
                         composition_sources=json.dumps({"sectors": "manual"}))
    updated = apply_composition(profile, {"sectors": {"Technologie": 50.0},
                                          "top_holdings": [{"name": "Apple", "ticker": "AAPL", "weight": 5.0}]})
    assert updated == ["top_holdings"]
    assert json.loads(profile.sectors) == {"Santé": 100.0}
    assert load_sources(profile) == {"sectors": "manual", "top_holdings": "yahoo"}
    assert profile.composition_refreshed_at is not None


def test_load_sources_tolerates_garbage():
    assert load_sources(EtfProfile(composition_sources="pas du json")) == {}
    assert load_sources(EtfProfile(composition_sources="[1]")) == {}
