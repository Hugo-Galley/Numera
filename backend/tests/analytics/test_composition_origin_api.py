"""Origine, fraîcheur et couverture des compositions servies par l'API, et positions sans ISIN."""
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding

WORLD = "IE00B4L5Y983"
CW8 = "LU1681043599"


def _profile(db: Session, name: str, ticker: str, isin: str, **fields: object) -> EtfProfile:
    profile = EtfProfile(name=name, ticker=ticker, isin=isin, aliases=f'["{ticker}"]', **fields)
    db.add(profile)
    db.commit()
    return profile


def _profiles(db: Session) -> tuple[EtfProfile, EtfProfile]:
    """Un ETF physique iShares et un synthétique Amundi du même indice, tels que l'actualisation les écrit."""
    reference = _profile(
        db, "iShares Core MSCI World", "IWDA.L", WORLD, provider="ishares", replication="physical",
        index_name="MSCI World", composition_as_of=date(2026, 11, 25), coverage_pct=99.8, lines_count=1273,
        countries='{"USA": 70.0}', composition_sources='{"countries": "ishares"}',
    )
    synthetic = _profile(
        db, "Amundi MSCI World Swap", "CW8.PA", CW8, provider="amundi", replication="synthetic",
        index_name="MSCI World", exposure_profile_id=reference.id, composition_as_of=date(2026, 11, 25),
        coverage_pct=99.8, lines_count=0,
    )
    return reference, synthetic


def _hold(db: Session, *positions: tuple[str, str | None, int | None]) -> None:
    account = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db.add(account)
    db.commit()
    db.add_all([
        PortfolioHolding(account_id=account.id, ticker=ticker, isin=isin, asset_name=ticker, quantity=1.0,
                         buy_price_avg=100.0, currency="EUR", etf_profile_id=profile_id)
        for ticker, isin, profile_id in positions
    ])
    db.commit()


def test_etf_profiles_expose_composition_origin(client: TestClient, db_session: Session):
    reference, synthetic = _profiles(db_session)

    by_id = {p["id"]: p for p in client.get("/etf-profiles").json()}

    physical = by_id[reference.id]
    assert physical["provider"] == "ishares"
    assert physical["replication"] == "physical"
    assert physical["index_name"] == "MSCI World"
    assert physical["exposure_profile_id"] is None
    assert physical["exposure_profile_name"] is None
    assert physical["composition_as_of"] == "2026-11-25"
    assert physical["coverage_pct"] == 99.8
    assert physical["lines_count"] == 1273
    swap = by_id[synthetic.id]
    assert swap["replication"] == "synthetic"
    assert swap["exposure_profile_id"] == reference.id
    assert swap["exposure_profile_name"] == "iShares Core MSCI World"
    assert swap["lines_count"] == 0

    assert client.get(f"/etf-profiles/{synthetic.id}").json() == swap


def test_scanner_describes_the_data_behind_each_composition(client: TestClient, db_session: Session):
    reference, synthetic = _profiles(db_session)
    _hold(db_session, ("IWDA.L", WORLD, reference.id), ("CW8.PA", CW8, synthetic.id))

    response = client.get("/analytics/diversity-scanner")

    assert response.status_code == 200
    by_id = {c["profile_id"]: c for c in response.json()["etf_compositions"]}
    physical = by_id[reference.id]
    assert (physical["provider"], physical["composition_as_of"]) == ("ishares", "2026-11-25")
    assert (physical["lines_count"], physical["coverage_pct"]) == (1273, 99.8)
    assert physical["exposure_profile_name"] is None
    # Synthétique : réplication et indice du fonds détenu, données (source, date, lignes) de la référence
    swap = by_id[synthetic.id]
    assert (swap["replication"], swap["index_name"]) == ("synthetic", "MSCI World")
    assert swap["exposure_profile_id"] == reference.id
    assert swap["exposure_profile_name"] == "iShares Core MSCI World"
    assert (swap["provider"], swap["composition_as_of"]) == ("ishares", "2026-11-25")
    assert (swap["lines_count"], swap["coverage_pct"]) == (1273, 99.8)


def test_scanner_synthetic_without_known_index(client: TestClient, db_session: Session):
    unknown = _profile(db_session, "ETF Swap", "SWP.PA", CW8, provider="amundi", replication="synthetic",
                       coverage_pct=0.0, lines_count=0)
    _hold(db_session, ("SWP.PA", CW8, unknown.id))

    [composition] = client.get("/analytics/diversity-scanner").json()["etf_compositions"]

    assert composition["replication"] == "synthetic"
    assert composition["exposure_profile_id"] is None
    assert composition["exposure_profile_name"] is None
    assert (composition["lines_count"], composition["coverage_pct"], composition["composition_as_of"]) == (0, 0.0, None)


def test_holdings_flag_missing_isin_except_for_crypto(client: TestClient, db_session: Session):
    _hold(db_session, ("AI.PA", "FR0000120073", None), ("HO.PA", None, None), ("MC.PA", "  ", None),
          ("BTC-EUR", None, None))

    holdings = client.get("/holdings").json()

    assert {h["ticker"]: h["isin_missing"] for h in holdings} == {
        "AI.PA": False, "HO.PA": True, "MC.PA": True, "BTC-EUR": False,
    }
