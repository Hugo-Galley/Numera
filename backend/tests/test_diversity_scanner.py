import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.portfolio_holding import PortfolioHolding
from app.models.etf_profile import EtfProfile
from app.core.seeds_etf import seed_etf_profiles


def test_etf_profiles_seeded_and_listable(client: TestClient, db_session: Session):
    seed_etf_profiles(db_session)
    
    # Test GET /etf-profiles
    response = client.get("/etf-profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) >= 6
    names = [p["name"] for p in profiles]
    assert "MSCI World" in names
    assert "S&P 500" in names
    assert "CAC 40" in names


def test_baseline_holdings_and_diversity_scanner(client: TestClient, db_session: Session):
    seed_etf_profiles(db_session)
    
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
    assert any(a["category"] in ("company", "overlap", "country", "sector") for a in alerts)


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
