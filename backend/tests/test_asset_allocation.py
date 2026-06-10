from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from datetime import datetime

def test_investments_allocation_advanced(client, db_session):
    # Setup accounts with asset allocation info
    acc1 = Account(
        name="PEA Tech", 
        type="investissement", 
        currency="EUR", 
        active=True,
        asset_class="Actions",
        sector="Technologie",
        geographic_zone="Europe"
    )
    acc2 = Account(
        name="CTO US", 
        type="investissement", 
        currency="EUR", 
        active=True,
        asset_class="Actions",
        sector="Technologie",
        geographic_zone="USA"
    )
    acc3 = Account(
        name="Livret A", 
        type="epargne", # Should be ignored in this specific endpoint
        currency="EUR", 
        active=True
    )
    db_session.add_all([acc1, acc2, acc3])
    db_session.commit()

    # Add snapshots for values
    db_session.add(BalanceSnapshot(account_id=acc1.id, date=datetime.now(), current_value=1000))
    db_session.add(BalanceSnapshot(account_id=acc2.id, date=datetime.now(), current_value=2000))
    db_session.commit()

    response = client.get("/analytics/investments-allocation-advanced")
    assert response.status_code == 200
    data = response.json()

    assert data["total_value_eur"] == 3000
    
    # Asset Class
    assert len(data["by_asset_class"]) == 1
    assert data["by_asset_class"][0]["name"] == "Actions"
    assert data["by_asset_class"][0]["value"] == 3000

    # Sector
    assert len(data["by_sector"]) == 1
    assert data["by_sector"][0]["name"] == "Technologie"

    # Geographic Zone
    zones = {item["name"]: item["value"] for item in data["by_geographic_zone"]}
    assert zones["USA"] == 2000
    assert zones["Europe"] == 1000
