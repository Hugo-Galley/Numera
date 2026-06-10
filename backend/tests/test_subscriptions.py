import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction

def test_subscriptions_analytics(client: TestClient, db_session: Session):
    # Setup
    account = Account(name="Checking", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    
    # 1. Real Recurring Transaction
    rd = RecurringTransaction(
        account_id=account.id,
        name="Netflix",
        type="Sortie",
        amount=15.99,
        currency="EUR",
        frequency="monthly",
        day_of_month=1,
        start_date=datetime.now() - timedelta(days=60),
        is_active=True
    )
    db_session.add(rd)
    db_session.commit()
    
    # 2. Repeated transactions (Potential subscription)
    # Merchant "Spotify", 9.99, twice
    for i in range(2):
        tx = Transaction(
            account_id=account.id,
            date=datetime.now() - timedelta(days=30 * (i+1)),
            month_label="Test",
            type="Sortie",
            merchant="Spotify",
            amount=9.99,
            original_amount=9.99,
            currency="EUR",
            running_balance=100
        )
        db_session.add(tx)
    
    db_session.commit()
    
    response = client.get("/analytics/subscriptions")
    if response.status_code == 422:
        print(f"DEBUG 422: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    
    # Check Netflix
    netflix = next(s for s in data["subscriptions"] if s["name"] == "Netflix")
    assert netflix["is_recurring_entity"] is True
    assert netflix["monthly_cost"] == 15.99
    
    # Check Spotify (potential)
    spotify = next(s for s in data["subscriptions"] if s["name"] == "Spotify")
    assert spotify["is_recurring_entity"] is False
    assert spotify["status"] == "potential"
    assert spotify["monthly_cost"] == 9.99
    
    # Totals
    # 15.99 + 9.99 = 25.98
    assert data["total_monthly"] == 25.98


def test_ignore_subscription(client: TestClient, db_session: Session):
    # Setup
    account = Account(name="Checking", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    
    # Potential subscription: "Disney+", 8.99, twice
    for i in range(2):
        tx = Transaction(
            account_id=account.id,
            date=datetime.now() - timedelta(days=30 * (i+1)),
            month_label="Test",
            type="Sortie",
            merchant="Disney+",
            amount=8.99,
            original_amount=8.99,
            currency="EUR",
            running_balance=100
        )
        db_session.add(tx)
    db_session.commit()
    
    # Verify it's detected
    response = client.get("/analytics/subscriptions")
    assert any(s["name"] == "Disney+" for s in response.json()["subscriptions"])
    
    # Ignore it
    ignore_response = client.post("/analytics/subscriptions/ignore", json={
        "merchant": "Disney+",
        "amount": 8.99
    })
    assert ignore_response.status_code == 200
    
    # Verify it's gone
    response = client.get("/analytics/subscriptions")
    assert not any(s["name"] == "Disney+" for s in response.json()["subscriptions"])
