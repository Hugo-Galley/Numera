"""Référence de marché du scanner de diversification : réglage `market_reference_ticker`, sinon l'ETF physique ACWI."""
import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time import utcnow_naive
from app.db.system_settings import get_setting
from app.models.etf_profile import EtfProfile
from app.services.investissement import etf_composition, market_reference
from tests.investissement.etf_profile_samples import add_sample_profiles

ACWI_ISIN = "IE00B6R52259"
ROUTE = "/analytics/diversity-scanner/market-reference"


def _reference(db: Session) -> EtfProfile | None:
    return asyncio.run(market_reference.market_reference(db))


def test_default_reference_is_existing_acwi_profile(db_session: Session, monkeypatch):
    async def no_collect(*_args, **_kwargs):
        raise AssertionError("profil à jour : aucune source interrogée")

    monkeypatch.setattr(etf_composition, "_collect", no_collect)
    acwi = EtfProfile(name="iShares MSCI ACWI", ticker="SSAC.L", isin=ACWI_ISIN, aliases="[]",
                      composition_refreshed_at=utcnow_naive())
    db_session.add(acwi)
    db_session.commit()

    found = _reference(db_session)

    assert found is not None
    assert found.id == acwi.id


def test_setting_overrides_default(client: TestClient, db_session: Session):
    add_sample_profiles(db_session)

    response = client.put(ROUTE, json={"ticker": "CW8.PA"})

    assert response.status_code == 200
    assert response.json() == {"ticker": "CW8.PA"}
    assert get_setting(db_session, market_reference.SETTING_KEY) == "CW8.PA"
    found = _reference(db_session)
    assert found is not None
    assert found.name == "MSCI World"


def test_unreachable_sources_return_none_without_writing(db_session: Session, monkeypatch):
    async def unavailable(*_args, **_kwargs):
        raise etf_composition.CompositionUnavailable("sources en échec")

    monkeypatch.setattr(etf_composition, "_collect", unavailable)

    assert _reference(db_session) is None
    assert db_session.query(EtfProfile).count() == 0


def test_empty_ticker_resets(client: TestClient, db_session: Session):
    client.put(ROUTE, json={"ticker": "CW8.PA"})

    response = client.put(ROUTE, json={"ticker": ""})

    assert response.status_code == 200
    assert response.json() == {"ticker": None}
    assert not get_setting(db_session, market_reference.SETTING_KEY)


def test_stale_reference_kept_when_sources_unreachable(db_session: Session, monkeypatch):
    async def unavailable(*_args, **_kwargs):
        raise etf_composition.CompositionUnavailable("sources en échec")

    monkeypatch.setattr(etf_composition, "_collect", unavailable)
    acwi = EtfProfile(name="iShares MSCI ACWI", ticker="SSAC.L", isin=ACWI_ISIN, aliases="[]")
    db_session.add(acwi)
    db_session.commit()

    found = _reference(db_session)

    assert found is not None
    assert found.id == acwi.id
    assert found.composition_refreshed_at is None
