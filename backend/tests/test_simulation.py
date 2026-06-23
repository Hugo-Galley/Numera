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


def test_wealth_simulation_advanced(client, db_session):
    import json
    events = [
        {"year": 1, "amount": -500, "label": "Achat Vélo"},
        {"year": 2, "amount": 2000, "label": "Héritage"}
    ]
    response = client.get(
        "/analytics/wealth-simulation",
        params={
            "initial_capital": 5000,
            "monthly_contribution": 200,
            "annual_return_pct": 8,
            "years": 3,
            "volatility_pct": 10,
            "inflation_rate_pct": 2.5,
            "contribution_indexation_pct": 3.0,
            "tax_rate_pct": 30.0,
            "tax_deferred": True,
            "events": json.dumps(events)
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_final_real" in data
    assert "pessimistic_final" in data
    assert "median_final" in data
    assert "optimistic_final" in data
    
    # Check that events were captured in items
    items = data["items"]
    assert len(items) == 4 # Year 0, 1, 2, 3
    assert "Achat Vélo" in items[1]["event_applied"]
    assert "Héritage" in items[2]["event_applied"]
    assert items[3]["event_applied"] is None
