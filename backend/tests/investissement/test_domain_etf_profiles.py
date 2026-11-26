"""Sources de la composition d'un profil ETF (sans base)."""
import json

from app.domain.etf_profiles import apply_composition, load_sources, match_profile
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


def _profile(**kw):
    return EtfProfile(**{"name": "Profil", "ticker": "AAA", "aliases": "[]", **kw})


def test_truncated_symbol_does_not_match():
    p = _profile(ticker="CSCO.TO", aliases=json.dumps(["CSCO.TO"]))
    assert match_profile([p], "CSCO") is None


def test_isin_match_wins():
    p = _profile(isin="LU1681043599")
    assert match_profile([p], "XXX", isin="lu1681043599") is p


def test_alias_exact_match():
    p = _profile(aliases=json.dumps(["CW8"]))
    assert match_profile([p], "CW8") is p
    assert match_profile([p], "cw8") is p
    assert match_profile([p], "CW8.PA") is None
    q = _profile(aliases=json.dumps(["CW8", "CW8.PA"]))
    assert match_profile([q], "CW8.PA") is q


def test_name_is_never_used():
    p = _profile(name="MSCI World")
    assert match_profile([p], "ZZZ", name="Amundi MSCI World Swap") is None
