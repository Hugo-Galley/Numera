import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.integrations import yahoo_finance
from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.services.investissement.etf_profiles import seed_etf_profiles

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

    monkeypatch.setattr(yahoo_finance, "fetch_composition", fake_fetch)
    return calls


def _world(db_session: Session) -> EtfProfile:
    return db_session.query(EtfProfile).filter(EtfProfile.name == "MSCI World").one()


def test_parse_yahoo_top_holdings_maps_sectors_and_weights():
    parsed = yahoo_finance.parse_top_holdings({
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
        raise yahoo_finance.YahooUnavailable("timeout")

    monkeypatch.setattr(yahoo_finance, "fetch_composition", down)
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
    from app.services.investissement.market import quotes as market_quotes

    async def fake_quotes(symbols, db=None):
        return {s.upper(): {"price_eur": 100.0, "type": "ETF"} for s in symbols}

    monkeypatch.setattr(market_quotes, "get_market_quotes", fake_quotes)
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


def test_auto_created_profile_has_no_truncated_alias(client: TestClient, db_session: Session, yahoo):
    resp = client.post("/etf-profiles/auto-decompose", json={"symbol": "csco.to", "isin": "us17275r1023"})
    assert resp.status_code == 200
    profile = db_session.query(EtfProfile).filter(EtfProfile.ticker == "CSCO.TO").one()
    assert json.loads(profile.aliases) == ["CSCO.TO", "US17275R1023"]


def _yahoo_transport(monkeypatch, summary: dict, status: int = 200):
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "fc.yahoo.com":
            return httpx.Response(404)
        if request.url.path.endswith("getcrumb"):
            return httpx.Response(200, text="crumb")
        return httpx.Response(status, json=summary)

    monkeypatch.setattr(yahoo_finance, "client", lambda timeout: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    monkeypatch.setitem(yahoo_finance._yahoo_auth, "crumb", None)


@pytest.mark.anyio
async def test_fetch_asset_profile_normalizes_country_and_sector(monkeypatch):
    summary = {"quoteSummary": {"result": [{"assetProfile": {"country": "United States", "sector": "Technology"}}]}}
    _yahoo_transport(monkeypatch, summary)
    assert await yahoo_finance.fetch_asset_profile("aapl") == {"country": "USA", "sector": "Technologie"}


@pytest.mark.anyio
async def test_fetch_asset_profile_unknown_values_and_unknown_symbol(monkeypatch):
    summary = {"quoteSummary": {"result": [{"assetProfile": {"country": "Atlantis", "sector": "Magie"}}]}}
    _yahoo_transport(monkeypatch, summary)
    assert await yahoo_finance.fetch_asset_profile("XYZ") == {"country": None, "sector": "Non renseigné"}
    _yahoo_transport(monkeypatch, {}, status=404)
    assert await yahoo_finance.fetch_asset_profile("XYZ") is None


@pytest.mark.anyio
async def test_fetch_asset_profile_raises_when_yahoo_down(monkeypatch):
    _yahoo_transport(monkeypatch, {}, status=500)
    with pytest.raises(yahoo_finance.YahooUnavailable):
        await yahoo_finance.fetch_asset_profile("AAPL")


def _direct_stock_setup(db_session: Session, monkeypatch, *, isin: str | None, ticker: str = "AAPL"):
    from app.services.investissement.market import quotes as market_quotes

    async def fake_quotes(symbols, db=None):
        return {s.upper(): {"price_eur": 100.0, "type": "EQUITY"} for s in symbols}

    monkeypatch.setattr(market_quotes, "get_market_quotes", fake_quotes)
    account = Account(name="CTO", type="investissement", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    db_session.add(PortfolioHolding(account_id=account.id, ticker=ticker, asset_name="Apple Inc", isin=isin,
                                    quantity=10.0, buy_price_avg=100.0, currency="EUR"))
    db_session.commit()


def test_scanner_enriches_direct_stock_once_from_yahoo(client: TestClient, db_session: Session, monkeypatch):
    from app.models.security import Security
    _direct_stock_setup(db_session, monkeypatch, isin="US0378331005")
    calls = []

    async def fake_profile(symbol):
        calls.append(symbol)
        return {"country": "USA", "sector": "Technologie"}

    monkeypatch.setattr(yahoo_finance, "fetch_asset_profile", fake_profile)
    for _ in range(2):
        data = client.get("/analytics/diversity-scanner").json()
    assert calls == ["AAPL"]
    assert {c["name"] for c in data["countries"]} == {"USA"}
    assert {s["name"] for s in data["sectors"]} == {"Technologie"}
    sec = db_session.get(Security, "US0378331005")
    assert (sec.source, sec.country, sec.sector, sec.ticker) == ("yahoo", "USA", "Technologie", "AAPL")
    assert data["top_underlying_companies"][0]["name"] == "Apple Inc"


def test_scanner_survives_yahoo_outage_for_direct_stock(client: TestClient, db_session: Session, monkeypatch):
    _direct_stock_setup(db_session, monkeypatch, isin="US0378331005")

    async def down(symbol):
        raise yahoo_finance.YahooUnavailable("hors ligne")

    monkeypatch.setattr(yahoo_finance, "fetch_asset_profile", down)
    data = client.get("/analytics/diversity-scanner").json()
    assert [c["name"] for c in data["countries"]] == ["Non renseigné"]
    assert [s["name"] for s in data["sectors"]] == ["Non renseigné"]


def test_scanner_never_calls_yahoo_without_isin(client: TestClient, db_session: Session, monkeypatch):
    from app.models.security import Security
    _direct_stock_setup(db_session, monkeypatch, isin=None)
    db_session.add(Security(isin="US0378331005", ticker="AAPL", name="Apple", country="USA", sector="Technologie",
                           exchange="NASDAQ", source="ishares"))
    db_session.commit()

    async def boom(symbol):
        raise AssertionError("pas d'appel Yahoo sans ISIN")

    monkeypatch.setattr(yahoo_finance, "fetch_asset_profile", boom)
    data = client.get("/analytics/diversity-scanner").json()
    assert [c["name"] for c in data["countries"]] == ["USA"]  # un seul titre porte ce ticker


def test_scanner_ignores_ambiguous_ticker_without_isin(client: TestClient, db_session: Session, monkeypatch):
    from app.models.security import Security
    _direct_stock_setup(db_session, monkeypatch, isin=None)
    db_session.add_all([
        Security(isin="US0378331005", ticker="AAPL", name="Apple", country="USA", sector="Technologie", exchange="NASDAQ", source="ishares"),
        Security(isin="US5949181045", ticker="AAPL", name="Autre", country="FRA", sector="Finance", exchange="NASDAQ", source="ishares"),
    ])
    db_session.commit()
    data = client.get("/analytics/diversity-scanner").json()
    assert [c["name"] for c in data["countries"]] == ["Non renseigné"]


def test_scanner_counts_crypto_in_its_own_sector(client: TestClient, db_session: Session, monkeypatch):
    from app.services.investissement.market import quotes as market_quotes

    async def fake_quotes(symbols, db=None):
        return {s.upper(): {"price_eur": 50.0, "type": "CRYPTOCURRENCY"} for s in symbols}

    monkeypatch.setattr(market_quotes, "get_market_quotes", fake_quotes)
    account = Account(name="CTO", type="investissement", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    db_session.add(PortfolioHolding(account_id=account.id, ticker="BTC-USD", asset_name="Bitcoin USD",
                                    quantity=2.0, buy_price_avg=50.0, currency="EUR"))
    db_session.commit()
    data = client.get("/analytics/diversity-scanner").json()
    assert data["totals"]["stocks_eur"] == 100.0
    assert [(s["name"], s["value_eur"]) for s in data["sectors"]] == [("Crypto-actifs", 100.0)]
    assert data["countries"] == []
    assert data["top_underlying_companies"] == []


def test_scanner_does_not_borrow_us_row_for_foreign_listing_without_isin(client: TestClient, db_session: Session, monkeypatch):
    from app.models.security import Security
    _direct_stock_setup(db_session, monkeypatch, isin=None, ticker="ISRG.PA")
    db_session.add(Security(isin="US46120E6023", ticker="ISRG", name="Intuitive Surgical", country="USA",
                            sector="Santé", exchange="NASDAQ", source="ishares"))
    db_session.commit()
    data = client.get("/analytics/diversity-scanner").json()
    assert [c["name"] for c in data["countries"]] == ["Non renseigné"]


def test_scanner_remembers_symbol_unknown_to_yahoo(client: TestClient, db_session: Session, monkeypatch):
    from datetime import timedelta

    from app.core.time import utcnow_naive
    from app.models.security import Security
    _direct_stock_setup(db_session, monkeypatch, isin="US0378331005")
    calls = []

    async def unknown(symbol):
        calls.append(symbol)

    monkeypatch.setattr(yahoo_finance, "fetch_asset_profile", unknown)
    client.get("/analytics/diversity-scanner")
    client.get("/analytics/diversity-scanner")
    assert calls == ["AAPL"]
    marker = db_session.get(Security, "US0378331005")
    assert (marker.source, marker.country, marker.sector) == ("yahoo", None, None)
    marker.updated_at = utcnow_naive() - timedelta(days=8)
    db_session.commit()
    client.get("/analytics/diversity-scanner")
    assert calls == ["AAPL", "AAPL"]
