"""Scanner de diversification sur les lignes complètes des ETF, y compris les synthétiques."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.etf_constituent import EtfConstituent
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.models.security import Security


@pytest.fixture(autouse=True)
def quotes(monkeypatch):
    from app.services.investissement.market import quotes as market_quotes

    async def fake_quotes(symbols, db=None):
        return {s.upper(): {"price_eur": 100.0, "type": "ETF" if s.endswith(".PA") else "EQUITY"} for s in symbols}

    monkeypatch.setattr(market_quotes, "get_market_quotes", fake_quotes)


@pytest.fixture(autouse=True)
def no_market_reference(monkeypatch):
    """Sources de composition injoignables : pas de référence de marché (score neutre)."""
    from app.services.investissement import etf_composition

    async def unavailable(*_args, **_kwargs):
        raise etf_composition.CompositionUnavailable("sources en échec")

    monkeypatch.setattr(etf_composition, "_collect", unavailable)


def _account(db: Session) -> Account:
    account = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db.add(account)
    db.commit()
    return account


def _profile(db: Session, name: str, lines: int = 0, **fields) -> EtfProfile:
    profile = EtfProfile(name=name, ticker=f"{name}.PA", aliases="[]", lines_count=lines, **fields)
    db.add(profile)
    db.commit()
    db.add_all(
        EtfConstituent(profile_id=profile.id, isin=f"XX{i:010d}", name=f"Société {i}", weight=100.0 / lines,
                       country="USA" if i % 2 else "JPN", sector="Technologie", asset_class="Equity")
        for i in range(lines)
    )
    db.commit()
    return profile


def _hold(db: Session, account: Account, ticker: str, profile: EtfProfile | None = None, isin: str | None = None) -> None:
    db.add(PortfolioHolding(account_id=account.id, ticker=ticker, asset_name=ticker, quantity=10.0, isin=isin,
                            buy_price_avg=100.0, currency="EUR", etf_profile_id=profile.id if profile else None))
    db.commit()


def test_two_synthetics_have_the_exposure_of_their_index(client: TestClient, db_session: Session):
    account = _account(db_session)
    reference = _profile(db_session, "REF", lines=40, composition_sources=json.dumps({"countries": "ishares"}))
    cw8 = _profile(db_session, "CW8", replication="synthetic", exposure_profile_id=reference.id)
    wpea = _profile(db_session, "WPEA", replication="synthetic", exposure_profile_id=reference.id)
    _hold(db_session, account, "CW8.PA", cw8)
    _hold(db_session, account, "WPEA.PA", wpea)

    data = client.get("/analytics/diversity-scanner").json()

    assert {c["name"]: c["value_eur"] for c in data["countries"]} == {"USA": 1000.0, "JPN": 1000.0}
    assert sorted(c["profile_name"] for c in data["etf_compositions"]) == ["CW8", "WPEA"]
    top = data["top_underlying_companies"]
    assert len(top) == 15
    assert top[0]["total_value_eur"] == 50.0
    # Deux synthétiques du même indice : une seule exposition, donc un seul chemin
    assert [s["source"] for s in top[0]["sources"]] == ["CW8.PA"]
    assert top[0]["sources"][0]["value_eur"] == 50.0
    assert top[0]["has_overlap"] is False


def test_synthetic_without_exposure_is_non_renseigne(client: TestClient, db_session: Session):
    account = _account(db_session)
    _hold(db_session, account, "CW8.PA", _profile(db_session, "CW8", replication="synthetic"))
    data = client.get("/analytics/diversity-scanner").json()
    assert [c["name"] for c in data["countries"]] == ["Non renseigné"]
    assert data["top_underlying_companies"] == []


def test_scanner_query_count_does_not_grow_with_holdings_or_lines(client: TestClient, db_session: Session, measure_queries):
    account = _account(db_session)

    def add_positions(start: int, count: int) -> None:
        for i in range(start, start + count):
            reference = _profile(db_session, f"REF{i}", lines=200)
            synthetic = _profile(db_session, f"SYN{i}", replication="synthetic", exposure_profile_id=reference.id)
            _hold(db_session, account, f"SYN{i}.PA", synthetic)
            _hold(db_session, account, f"PHY{i}.PA", _profile(db_session, f"PHY{i}", lines=200))
            _hold(db_session, account, f"ACT{i}")  # action en direct, sans profil

    def scan():
        return measure_queries(lambda: client.get("/analytics/diversity-scanner"))

    add_positions(0, 1)
    scan()  # premier passage : écritures éventuelles
    small_response, small = scan()
    add_positions(1, 5)
    scan()
    large_response, large = scan()

    assert small_response.status_code == large_response.status_code == 200
    assert large_response.json()["totals"]["etfs_count"] == 12
    assert large == small


APPLE_ISIN = "US0378331005"


def _world_with_apple(db: Session, name: str) -> EtfProfile:
    profile = EtfProfile(name=name, ticker=f"{name}.PA", aliases="[]", lines_count=2, index_name="MSCI World")
    db.add(profile)
    db.commit()
    db.add_all([
        EtfConstituent(profile_id=profile.id, isin=APPLE_ISIN, name="Apple Inc", weight=5.0, country="USA",
                       sector="Technologie", asset_class="Equity"),
        EtfConstituent(profile_id=profile.id, isin="JP0000000001", name="Toyota", weight=95.0, country="JPN",
                       sector="Industrie", asset_class="Equity"),
    ])
    db.commit()
    return profile


def _apple(data: dict) -> dict:
    return next(c for c in data["top_underlying_companies"] if c["name"].startswith("Apple"))


def test_two_world_funds_are_not_an_overlap(client: TestClient, db_session: Session):
    account = _account(db_session)
    other = Account(name="CTO", type="investissement", currency="EUR", active=True)
    db_session.add(other)
    db_session.commit()
    _hold(db_session, account, "WPEA.PA", _world_with_apple(db_session, "WPEA"))
    _hold(db_session, other, "CW8.PA", _world_with_apple(db_session, "CW8"))

    data = client.get("/analytics/diversity-scanner").json()

    assert _apple(data)["has_overlap"] is False
    assert not [a for a in data["alerts"] if a["category"] == "overlap"]
    assert len(data["exposures"]) == 1
    assert len(data["exposures"][0]["supports"]) == 2

    db_session.add(Security(isin=APPLE_ISIN, ticker="AAPL", name="Apple Inc", country="USA", sector="Technologie",
                            source="test"))
    _hold(db_session, account, "AAPL", isin=APPLE_ISIN)
    data = client.get("/analytics/diversity-scanner").json()

    apple = _apple(data)
    assert apple["has_overlap"] is True
    assert {s["source"] for s in apple["sources"]} == {"En direct", "WPEA.PA"}
    assert [a for a in data["alerts"] if a["category"] == "overlap"]
