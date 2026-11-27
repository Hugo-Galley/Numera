import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from tests.investissement.etf_profile_samples import add_sample_profiles


def test_etf_profiles_listable(client: TestClient, db_session: Session):
    add_sample_profiles(db_session)

    # Test GET /etf-profiles
    response = client.get("/etf-profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) == 3
    names = [p["name"] for p in profiles]
    assert "MSCI World" in names
    assert "S&P 500" in names
    assert "CAC 40" in names


def test_baseline_holdings_and_diversity_scanner(client: TestClient, db_session: Session):
    add_sample_profiles(db_session)

    # Create test investment account
    account = Account(name="Test PEA", type="investissement", currency="EUR", active=True)
    db_session.add(account)

    # Create safe savings account (Ce qu'on a à côté)
    livret = Account(name="Livret A", type="epargne", currency="EUR", active=True)
    db_session.add(livret)
    db_session.commit()
    db_session.refresh(account)
    db_session.refresh(livret)

    # Add 10,000 EUR to Livret A
    from app.models.balance_snapshot import BalanceSnapshot
    db_session.add(BalanceSnapshot(account_id=livret.id, date=datetime.now(), current_value=10000.0))
    db_session.commit()

    # Get MSCI World & S&P 500 profiles
    world_profile = db_session.query(EtfProfile).filter(EtfProfile.name == "MSCI World").first()
    sp500_profile = db_session.query(EtfProfile).filter(EtfProfile.name == "S&P 500").first()
    # Composition telle qu'un émetteur l'aurait écrite
    for profile in (world_profile, sp500_profile):
        profile.top_holdings = json.dumps([{"name": "Apple Inc", "ticker": "AAPL", "weight": 6.0}])
        profile.composition_sources = json.dumps({"top_holdings": "ishares"})
    db_session.commit()

    # Set Point Zéro / Baseline: 10 parts of CW8, 20 parts of ESE, and 5 direct Apple shares
    baseline_payload = {
        "account_id": account.id,
        "holdings": [
            {
                "ticker": "CW8.PA",
                "asset_name": "Amundi MSCI World",
                "quantity": 10.0,
                "buy_price_avg": 500.0,
                "currency": "EUR",
                "etf_profile_id": world_profile.id,
            },
            {
                "ticker": "ESE.PA",
                "asset_name": "BNP Easy S&P 500",
                "quantity": 20.0,
                "buy_price_avg": 30.0,
                "currency": "EUR",
                "etf_profile_id": sp500_profile.id,
            },
            {
                "ticker": "AAPL",
                "asset_name": "Apple Inc.",
                "quantity": 5.0,
                "buy_price_avg": 200.0,
                "currency": "USD",
                "etf_profile_id": None,
            },
        ],
    }

    resp = client.post("/holdings/baseline", json=baseline_payload)
    assert resp.status_code == 200
    saved_holdings = resp.json()
    assert len(saved_holdings) == 3

    # Query Diversity Scanner
    scan_resp = client.get(f"/analytics/diversity-scanner?account_id={account.id}")
    assert scan_resp.status_code == 200
    data = scan_resp.json()

    assert "score" in data
    assert "totals" in data
    assert data["totals"]["holdings_count"] == 3
    assert data["totals"]["epargne_eur"] >= 10000.0
    # Répartition de la valeur des positions : Apple en direct, CW8 et ESE décomposés
    totals = data["totals"]
    assert totals["direct_eur"] > 0
    assert totals["etf_eur"] > 0
    assert round(totals["direct_eur"] + totals["etf_eur"], 2) == totals["stocks_eur"]

    # Verify look-through company aggregation (Apple should be present with both direct and indirect exposure)
    top_comps = data["top_underlying_companies"]
    assert len(top_comps) > 0
    apple_entry = next((c for c in top_comps if "apple" in c["name"].lower()), None)
    assert apple_entry is not None
    # Apple has direct value + indirect value from both CW8 and ESE!
    assert apple_entry["direct_value_eur"] > 0
    assert apple_entry["indirect_value_eur"] > 0
    assert apple_entry["has_overlap"] is True
    assert len(apple_entry["sources"]) >= 2

    # Check alert detection
    alerts = data["alerts"]
    assert isinstance(alerts, list)
    assert alerts
    assert {a["category"] for a in alerts} <= {"overweight", "overlap", "redundant_pick", "correlated_block"}


def test_investment_transaction_auto_increments_holding(client: TestClient, db_session: Session):
    account = Account(name="Test CTO", type="investissement", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    # Post an investment transaction with quantity and ticker (buy 4 shares of MC.PA)
    tx_payload = {
        "account_id": account.id,
        "date": datetime.now().isoformat(),
        "type": "versement",
        "amount": 1600.0,
        "currency": "EUR",
        "ticker": "MC.PA",
        "quantity": 4.0,
        "unit_price": 400.0,
        "note": "Achat LVMH",
    }
    tx_resp = client.post("/investment-transactions", json=tx_payload)
    assert tx_resp.status_code == 201

    # Check that PortfolioHolding was created with quantity 4
    holding = db_session.query(PortfolioHolding).filter(
        PortfolioHolding.account_id == account.id,
        PortfolioHolding.ticker == "MC.PA"
    ).first()
    assert holding is not None
    assert holding.quantity == 4.0

    # Buy 2 more shares
    tx_payload2 = {
        "account_id": account.id,
        "date": datetime.now().isoformat(),
        "type": "versement",
        "amount": 800.0,
        "currency": "EUR",
        "ticker": "MC.PA",
        "quantity": 2.0,
        "unit_price": 400.0,
        "note": "Achat LVMH suite",
    }
    tx_resp2 = client.post("/investment-transactions", json=tx_payload2)
    assert tx_resp2.status_code == 201

    # Holding quantity should now be 6.0
    db_session.refresh(holding)
    assert holding.quantity == 6.0


def test_market_search_and_validate(client: TestClient, db_session: Session):
    add_sample_profiles(db_session)

    # 1. Search with 'q'
    resp_q = client.get("/market/search?q=CW8")
    assert resp_q.status_code == 200
    results_q = resp_q.json()
    assert isinstance(results_q, list)
    assert len(results_q) > 0
    assert any("CW8" in r.get("symbol", "").upper() for r in results_q)

    # 2. Search with 'query'
    resp_query = client.get("/market/search?query=FR0010315770")
    assert resp_query.status_code == 200
    results_query = resp_query.json()
    assert isinstance(results_query, list)
    assert len(results_query) > 0

    # 3. Validate existing ticker
    val_resp = client.get("/market/validate?symbol_or_isin=CW8.PA")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True
    assert val_data["symbol"] == "CW8.PA"

    # 4. Validate empty / invalid
    invalid_resp = client.get("/market/validate?symbol_or_isin=NONEXISTENT_XYZ_12345")
    assert invalid_resp.status_code == 200
    invalid_data = invalid_resp.json()
    assert invalid_data["valid"] is False


def test_une_action_rattachee_a_un_profil_n_est_pas_un_etf(client: TestClient, db_session: Session, monkeypatch):
    from app.services.analytics import diversity
    add_sample_profiles(db_session)
    account = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    profile = db_session.query(EtfProfile).first()
    holding = PortfolioHolding(account_id=account.id, ticker="CSCO", asset_name="Cisco Systems", quantity=1.0,
                               buy_price_avg=50.0, currency="USD", etf_profile_id=profile.id)
    db_session.add(holding)
    db_session.commit()

    import asyncio
    quotes = {"CSCO": {"type": "EQUITY", "price_eur": 50.0}}
    valued, _ = asyncio.run(diversity._value_holdings(db_session, [holding], quotes, {"USD": 1.0}))
    assert valued[0]["is_etf"] is False
    assert holding.etf_profile_id == profile.id  # rattachement laissé intact


def test_etf_sans_type_connu_reste_etf_et_decompose(client: TestClient, db_session: Session):
    """Yahoo indisponible : le type est inconnu, mais le ticker correspond exactement à un profil."""
    import asyncio

    from app.services.analytics import diversity
    add_sample_profiles(db_session)
    account = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    holding = PortfolioHolding(account_id=account.id, ticker="ESE.PA", asset_name="BNP Easy S&P 500", quantity=1.0,
                               buy_price_avg=30.0, currency="EUR")
    db_session.add(holding)
    db_session.commit()
    valued, _ = asyncio.run(diversity._value_holdings(db_session, [holding], {}, {"EUR": 1.0}))
    assert valued[0]["is_etf"] is True
    assert valued[0]["etf_profile_id"] is not None


def _holding(db: Session, account: Account, ticker: str, value: float, name: str | None = None) -> None:
    db.add(PortfolioHolding(account_id=account.id, ticker=ticker, asset_name=name or ticker, quantity=1.0,
                            buy_price_avg=value, currency="EUR"))
    db.commit()


def _investment_account(db: Session, name: str = "CTO") -> Account:
    account = Account(name=name, type="investissement", currency="EUR", active=True)
    db.add(account)
    db.commit()
    return account


@pytest.fixture(autouse=True)
def _no_reference(monkeypatch) -> None:
    """Émetteurs et Yahoo injoignables : la référence de marché ne peut pas être créée (une référence déjà en base
    et à jour reste utilisée)."""
    from app.services.investissement import etf_composition

    async def unavailable(*_args, **_kwargs):
        raise etf_composition.CompositionUnavailable("sources en échec")

    monkeypatch.setattr(etf_composition, "_collect", unavailable)


def test_scanner_without_market_reference(client: TestClient, db_session: Session, monkeypatch):
    _holding(db_session, _investment_account(db_session), "AAPL", 500.0, "Apple Inc.")

    response = client.get("/analytics/diversity-scanner")

    assert response.status_code == 200
    data = response.json()
    assert data["market"] is None
    assert data["score"] == 50.0
    assert data["score_label"] == "Référence de marché indisponible : score neutre"
    assert all(c["market_pct"] is None for c in data["countries"] + data["sectors"])
    assert not [a for a in data["alerts"] if a["category"] == "overweight"]


def test_scanner_empty_and_single_line(client: TestClient, db_session: Session, monkeypatch):
    account = _investment_account(db_session)

    empty = client.get("/analytics/diversity-scanner").json()

    assert empty["concentration"]["effective_bets"] == 0.0
    assert empty["concentration"]["exposures_count"] == 0
    assert empty["concentration"]["blocks"] == []
    assert empty["exposures"] == []
    assert empty["coverage"] == {"with_prices_pct": 0.0, "composition_pct": 0.0}

    _holding(db_session, account, "AAPL", 500.0, "Apple Inc.")
    single = client.get(f"/analytics/diversity-scanner?account_id={account.id}").json()

    assert single["concentration"]["effective_bets"] == 1.0
    assert single["concentration"]["exposures_count"] == 1
    assert single["concentration"]["blocks"] == []
    assert single["exposures"][0]["weight_pct"] == 100.0
    assert [p["name"] for p in single["stock_picking"]] == ["Apple Inc."]


def test_same_crypto_two_accounts_single_exposure(client: TestClient, db_session: Session, monkeypatch):
    from app.services.investissement.market import quotes as market_quotes

    async def crypto_quotes(symbols, db=None):
        return {s.upper(): {"price_eur": 1.0, "type": "CRYPTOCURRENCY"} for s in symbols}

    monkeypatch.setattr(market_quotes, "get_market_quotes", crypto_quotes)
    first, second = _investment_account(db_session, "Ledger"), _investment_account(db_session, "Exchange")
    db_session.add_all([
        PortfolioHolding(account_id=first.id, ticker="BTC-USD", asset_name="Bitcoin USD", quantity=207.04,
                         buy_price_avg=1.0, currency="EUR"),
        PortfolioHolding(account_id=second.id, ticker="BTC-USD", asset_name="Bitcoin USD", quantity=460.56,
                         buy_price_avg=1.0, currency="EUR"),
    ])
    db_session.commit()

    data = client.get("/analytics/diversity-scanner").json()

    assert len(data["exposures"]) == 1
    btc = data["exposures"][0]
    assert btc["name"] == "Bitcoin USD"
    assert btc["kind"] == "crypto"
    assert btc["value_eur"] == 667.6
    assert [(s["account_name"], s["value_eur"]) for s in btc["supports"]] == [("Exchange", 460.56), ("Ledger", 207.04)]
    assert data["concentration"]["effective_bets"] == 1.0
    assert data["stock_picking"] == []


def test_scanner_against_a_market_reference(client: TestClient, db_session: Session):
    from app.core.time import utcnow_naive

    db_session.add(EtfProfile(name="iShares MSCI ACWI", ticker="SSAC.L", isin="IE00B6R52259", aliases="[]",
                              composition_refreshed_at=utcnow_naive(),
                              countries=json.dumps({"USA": 64.0, "JPN": 36.0}),
                              sectors=json.dumps({"Technologie": 25.0, "Industrie": 75.0}),
                              top_holdings=json.dumps([{"name": "Apple Inc", "ticker": "AAPL", "isin": "US0378331005",
                                                         "weight": 4.0}])))
    db_session.commit()
    account = _investment_account(db_session)
    _holding(db_session, account, "AAPL", 500.0, "Apple Inc")
    from app.models.security import Security
    db_session.add(Security(isin="US0378331005", ticker="AAPL", name="Apple Inc", country="USA",
                            sector="Technologie", source="test"))
    db_session.query(PortfolioHolding).update({"isin": "US0378331005"})
    db_session.commit()

    data = client.get("/analytics/diversity-scanner").json()

    market = data["market"]
    assert market["name"] == "iShares MSCI ACWI"
    assert market["ticker"] == "SSAC.L"
    assert market["countries"]["active_share_pct"] == 36.0
    assert {c["name"]: c["market_pct"] for c in data["countries"]} == {"USA": 64.0}
    assert {s["name"]: s["market_pct"] for s in data["sectors"]} == {"Technologie": 25.0}
    # Pays 36, secteurs 75, sociétés 0 (la part connue du marché n'est qu'Apple) : 100 − 37
    assert data["score"] == 63.0
    overweight = {(a["dimension"], a["item_name"]) for a in data["alerts"] if a["category"] == "overweight"}
    assert ("sectors", "Technologie") in overweight
    assert ("countries", "USA") in overweight  # 100 % contre 64 % : plus de 1,5 fois le marché et +36 points


def test_scanner_with_unknown_composition_is_neutral(client: TestClient, db_session: Session):
    """Référence connue, mais aucune ligne comparable (fonds sans composition) : pas de « 100 / excellent »."""
    from app.core.time import utcnow_naive

    db_session.add(EtfProfile(name="iShares MSCI ACWI", ticker="SSAC.L", isin="IE00B6R52259", aliases="[]",
                              composition_refreshed_at=utcnow_naive(), countries=json.dumps({"USA": 64.0}),
                              sectors=json.dumps({"Technologie": 25.0})))
    fund = EtfProfile(name="Fonds opaque", ticker="OPQ.PA", aliases="[]")
    db_session.add(fund)
    db_session.commit()
    account = _investment_account(db_session)
    db_session.add(PortfolioHolding(account_id=account.id, ticker="OPQ.PA", asset_name="Fonds opaque", quantity=1.0,
                                    buy_price_avg=1000.0, currency="EUR", etf_profile_id=fund.id))
    db_session.commit()

    data = client.get("/analytics/diversity-scanner").json()

    assert data["market"]["countries"]["covered_pct"] == 0.0
    assert data["score"] == 50.0
    assert data["score_label"] == "Composition inconnue : score neutre"
