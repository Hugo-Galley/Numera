"""Préréglages des profils ETF système (`domain/etf_presets.json`) : des identifiants, jamais de composition."""
import json

from sqlalchemy.orm import Session

from app.domain.etf_presets import SYSTEM_ETF_PRESETS
from app.models.etf_profile import EtfProfile
from app.services.investissement.etf_profiles import seed_etf_profiles


def test_presets_shape():
    assert len(SYSTEM_ETF_PRESETS) == 10
    assert len({p["name"] for p in SYSTEM_ETF_PRESETS}) == 10


def test_presets_have_no_composition():
    for preset in SYSTEM_ETF_PRESETS:
        assert set(preset) == {"name", "ticker", "isin", "aliases"}


def test_seeded_system_profiles_have_no_composition(db_session: Session):
    seed_etf_profiles(db_session)
    profiles = db_session.query(EtfProfile).all()
    assert len(profiles) == 10
    for profile in profiles:
        assert (profile.countries, profile.sectors, profile.top_holdings, profile.composition_sources) == (
            "{}", "{}", "[]", "{}")
        assert profile.is_system and profile.isin and profile.composition_refreshed_at is None


def test_seeding_again_updates_identifiers_and_leaves_compositions_alone(db_session: Session):
    seed_etf_profiles(db_session)
    world = db_session.query(EtfProfile).filter(EtfProfile.name == "MSCI World").one()
    world.sectors = json.dumps({"Finance": 100.0})
    world.composition_sources = json.dumps({"sectors": "yahoo"})
    world.aliases = "[]"
    db_session.commit()

    seed_etf_profiles(db_session)

    db_session.refresh(world)
    assert (json.loads(world.sectors), json.loads(world.composition_sources)) == ({"Finance": 100.0}, {"sectors": "yahoo"})
    assert "CW8.PA" in json.loads(world.aliases)
    assert db_session.query(EtfProfile).count() == 10
