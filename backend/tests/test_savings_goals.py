import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction

def test_savings_goals_crud(client: TestClient):
    # Create
    response = client.post(
        "/goals",
        json={
            "name": "Vacances",
            "target_amount": 2000,
            "keyword": "vacances",
            "icon": "plane",
            "color": "blue",
            "deadline": str(date.today() + timedelta(days=365))
        }
    )
    assert response.status_code == 200
    goal_id = response.json()["id"]
    assert response.json()["name"] == "Vacances"

    # Update
    response = client.patch(
        f"/goals/{goal_id}",
        json={"target_amount": 2500}
    )
    assert response.status_code == 200
    assert response.json()["target_amount"] == 2500

    # List/Read
    response = client.get("/goals")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # Delete
    response = client.delete(f"/goals/{goal_id}")
    assert response.status_code == 200
    
    response = client.get("/goals")
    # Verify it's gone from list (might have other goals if DB is not clean, but here db_session should be fresh)
    assert all(g["id"] != goal_id for g in response.json())

def test_savings_goal_progress(client: TestClient, db_session: Session):
    # Setup: Account, Category, Transactions
    account = Account(name="Epargne", type="epargne", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    
    # Create goal
    response = client.post(
        "/goals",
        json={
            "name": "Nouveau PC",
            "target_amount": 1000,
            "keyword": "PC",
            "account_id": account.id
        }
    )
    goal_id = response.json()["id"]
    
    # Add transaction matching keyword
    client.post(
        "/transactions",
        json={
            "account_id": account.id,
            "date": "2026-06-05T10:00:00",
            "type": "Entree",
            "merchant": "Vente PC",
            "amount": 400,
            "note": "Economie pour le PC"
        }
    )
    
    # Add transaction NOT matching
    client.post(
        "/transactions",
        json={
            "account_id": account.id,
            "date": "2026-06-05T11:00:00",
            "type": "Sortie",
            "merchant": "KFC",
            "amount": 20,
            "note": "Lunch"
        }
    )
    
    # Check progress
    response = client.get("/goals")
    assert response.status_code == 200
    goal_progress = next(g for g in response.json() if g["id"] == goal_id)
    
    assert goal_progress["current_amount"] == 400.0
    assert goal_progress["percentage"] == 40.0
    assert goal_progress["status"] == "on_track"

def test_savings_goal_with_deadline(client: TestClient):
    # Goal with deadline behind
    deadline = date.today() - timedelta(days=1)
    response = client.post(
        "/goals",
        json={
            "name": "Goal Expired",
            "target_amount": 1000,
            "keyword": "expired",
            "deadline": str(deadline)
        }
    )
    goal_id = response.json()["id"]
    
    response = client.get("/goals")
    goal_progress = next(g for g in response.json() if g["id"] == goal_id)
    assert goal_progress["status"] == "behind"
