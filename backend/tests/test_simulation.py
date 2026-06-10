import pytest

def test_wealth_simulation_basic(client, db_session):
    # 10000€, 0 contribution, 10% interest, 1 year
    response = client.get(
        "/analytics/wealth-simulation",
        params={
            "initial_capital": 10000,
            "monthly_contribution": 0,
            "annual_return_pct": 10,
            "years": 1
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_contributions"] == 0
    # 10% of 10000 is 1000
    assert data["total_final"] == 11000
    assert data["total_interest"] == 1000
    assert len(data["items"]) == 2 # Year 0 and Year 1

def test_wealth_simulation_with_contributions(client, db_session):
    # 0€ initial, 100€ monthly, 0% interest, 1 year
    response = client.get(
        "/analytics/wealth-simulation",
        params={
            "initial_capital": 0,
            "monthly_contribution": 100,
            "annual_return_pct": 0,
            "years": 1
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_contributions"] == 1200
    assert data["total_final"] == 1200
    assert data["total_interest"] == 0

def test_wealth_simulation_compounded(client, db_session):
    # 1000€ initial, 100€ monthly, 10% interest, 2 years
    response = client.get(
        "/analytics/wealth-simulation",
        params={
            "initial_capital": 1000,
            "monthly_contribution": 100,
            "annual_return_pct": 10,
            "years": 2
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_contributions"] == 2400
    assert data["total_final"] > 3400 # 1000 + 2400 + interest
    assert data["total_interest"] > 0
