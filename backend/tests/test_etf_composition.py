import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import etf_analyzer
from app.core.seeds_etf import seed_etf_profiles
from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding

YAHOO_COMPOSITION = {
    "name": "Amundi MSCI World Swap UCITS ETF",
    "quote_type": "ETF",
    "sectors": {"Technologie": 30.6, "Finance": 16.3, "Santé": 9.3},
    "top_holdings": [{"name": "NVIDIA Corp", "ticker": "NVDA", "weight": 5.79}],
}


@pytest.fixture
def yahoo(monkeypatch):
    calls = []

    async def fake_fetch(symbol):
        calls.append(symbol)
        return YAHOO_COMPOSITION

    monkeypatch.setattr(etf_analyzer, "fetch_yahoo_composition", fake_fetch)
    return calls


def _world(db_session: Session) -> EtfProfile:
    return db_session.query(EtfProfile).filter(EtfProfile.name == "MSCI World").one()


def test_parse_yahoo_top_holdings_maps_sectors_and_weights():
    parsed = etf_analyzer._parse_top_holdings({
        "sectorWeightings": [{"technology": {"raw": 0.3062}}, {"energy": {"raw": 0.0}}, {"realestate": {"raw": 0.0167}}],
        "holdings": [{"symbol": "NVDA", "holdingName": "NVIDIA Corp", "holdingPercent": {"raw": 0.0578801}}],
    })
    assert parsed["sectors"] == {"Technologie": 30.62, "Immobilier": 1.67}
    assert parsed["top_holdings"] == [{"name": "NVIDIA Corp", "ticker": "NVDA", "weight": 5.79}]


def test_refresh_replaces_preset_but_keeps_countries(client: TestClient, db_session: Session, yahoo):
    seed_etf_profiles(db_session)
    world = _world(db_session)
    preset_countries = json.loads(world.countries)

    resp = client.post(f"/etf-profiles/{world.id}/refresh")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sectors"] == YAHOO_COMPOSITION["sectors"]
    assert body["composition_sources"] == {"countries": "preset", "sectors": "yahoo", "top_holdings": "yahoo"}
    assert body["composition_refreshed_at"] is not None

    db_session.refresh(world)
    assert json.loads(world.top_holdings) == YAHOO_COMPOSITION["top_holdings"]
    assert json.loads(world.countries) == preset_countries
    assert yahoo == ["CW8.PA"]


def test_seed_does_not_overwrite_yahoo_or_manual_fields(client: TestClient, db_session: Session, yahoo):
    seed_etf_profiles(db_session)
    world = _world(db_session)
    client.post(f"/etf-profiles/{world.id}/refresh")
    client.put(f"/etf-profiles/{world.id}", json={"countries": {"USA": 70.0, "Autres": 30.0}})

    seed_etf_profiles(db_session)
    db_session.refresh(world)
    assert json.loads(world.sectors) == YAHOO_COMPOSITION["sectors"]
    assert json.loads(world.countries) == {"USA": 70.0, "Autres": 30.0}
    assert json.loads(world.composition_sources)["countries"] == "manual"


def test_refresh_never_overwrites_manual_field(client: TestClient, db_session: Session, yahoo):
    seed_etf_profiles(db_session)
    world = _world(db_session)
    client.put(f"/etf-profiles/{world.id}", json={"sectors": {"Technologie": 100.0}})

    body = client.post(f"/etf-profiles/{world.id}/refresh").json()
    assert body["sectors"] == {"Technologie": 100.0}
    assert body["composition_sources"]["sectors"] == "manual"
    assert body["composition_sources"]["top_holdings"] == "yahoo"


def test_refresh_returns_502_when_yahoo_unreachable(client: TestClient, db_session: Session, monkeypatch):
    async def down(symbol):
        raise etf_analyzer.YahooUnavailable("timeout")

    monkeypatch.setattr(etf_analyzer, "fetch_yahoo_composition", down)
    seed_etf_profiles(db_session)
    world = _world(db_session)
    preset_sectors = world.sectors

    assert client.post(f"/etf-profiles/{world.id}/refresh").status_code == 502
    db_session.refresh(world)
    assert world.sectors == preset_sectors
    assert world.composition_refreshed_at is None


def test_auto_decompose_uses_yahoo_and_leaves_countries_empty(client: TestClient, db_session: Session, yahoo):
    resp = client.post("/etf-profiles/auto-decompose", json={"symbol": "wld.pa"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == YAHOO_COMPOSITION["name"]
    assert body["countries"] == {}
    assert body["sectors"] == YAHOO_COMPOSITION["sectors"]
    assert body["composition_sources"] == {"sectors": "yahoo", "top_holdings": "yahoo"}


def test_refresh_held_only_touches_held_profiles(client: TestClient, db_session: Session, yahoo):
    seed_etf_profiles(db_session)
    world = _world(db_session)
    account = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    db_session.add(PortfolioHolding(
        account_id=account.id, ticker="WLD.PA", asset_name="Amundi MSCI World",
        quantity=5.0, buy_price_avg=30.0, currency="EUR", etf_profile_id=world.id,
    ))
    db_session.commit()

    resp = client.post("/etf-profiles/refresh-held")
    assert resp.status_code == 200
    assert resp.json() == {"refreshed": 1}
    assert yahoo == ["CW8.PA"]


def test_diversity_puts_uncovered_weight_in_non_renseigne(client: TestClient, db_session: Session, monkeypatch):
    from app.controllers.analytics import diversity

    async def fake_quotes(symbols, db=None):
        return {s.upper(): {"price_eur": 100.0, "type": "ETF"} for s in symbols}

    monkeypatch.setattr(diversity, "get_market_quotes", fake_quotes)
    profile = EtfProfile(
        name="Fonds Yahoo", ticker="WLD.PA", aliases="[]", countries="{}",
        sectors=json.dumps({"Technologie": 60.0}), top_holdings="[]",
        composition_sources=json.dumps({"sectors": "yahoo"}),
    )
    account = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add_all([profile, account])
    db_session.commit()
    db_session.add(PortfolioHolding(
        account_id=account.id, ticker="WLD.PA", asset_name="Fonds Yahoo",
        quantity=10.0, buy_price_avg=100.0, currency="EUR", etf_profile_id=profile.id,
    ))
    db_session.commit()

    data = client.get("/analytics/diversity-scanner").json()
    sectors = {s["name"]: s["value_eur"] for s in data["sectors"]}
    countries = {c["name"]: c["value_eur"] for c in data["countries"]}
    assert sectors == {"Technologie": 600.0, "Non renseigné": 400.0}
    assert countries == {"Non renseigné": 1000.0}
    assert data["etf_compositions"][0]["sources"] == {"sectors": "yahoo"}
    assert not any(a["category"] == "sector" and a["item_name"] == "Non renseigné" for a in data["alerts"])
