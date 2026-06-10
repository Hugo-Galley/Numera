import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.core.finance import month_label_from_date

def test_bulk_update_transactions(client: TestClient, db_session: Session):
    # Setup: Account, Category, Transactions
    account = Account(name="Test Account", type="courant", currency="EUR", active=True)
    cat1 = Category(name="Cat 1", type="depense")
    cat2 = Category(name="Cat 2", type="depense")
    db_session.add_all([account, cat1, cat2])
    db_session.commit()
    
    date1 = datetime(2026, 6, 1)
    date2 = datetime(2026, 6, 2)
    tx1 = Transaction(
        account_id=account.id,
        date=date1,
        month_label=month_label_from_date(date1),
        type="Sortie",
        merchant="M1",
        amount=10,
        original_amount=10,
        currency="EUR",
        category_id=cat1.id,
        running_balance=0.0
    )
    tx2 = Transaction(
        account_id=account.id,
        date=date2,
        month_label=month_label_from_date(date2),
        type="Sortie",
        merchant="M2",
        amount=20,
        original_amount=20,
        currency="EUR",
        category_id=cat1.id,
        running_balance=0.0
    )
    db_session.add_all([tx1, tx2])
    db_session.commit()
    
    # Bulk update: change category and merchant for both
    payload = {
        "ids": [tx1.id, tx2.id],
        "category_id": cat2.id,
        "merchant": "New Merchant",
        "is_recurring": True
    }
    response = client.patch("/transactions/bulk", json=payload)
    if response.status_code == 422:
        print(f"Bulk update 422 error: {response.json()}")
    assert response.status_code == 204
    
    db_session.refresh(tx1)
    db_session.refresh(tx2)
    
    assert tx1.category_id == cat2.id
    assert tx1.merchant == "New Merchant"
    assert tx1.is_recurring is True
    assert tx2.category_id == cat2.id
    assert tx2.merchant == "New Merchant"
    assert tx2.is_recurring is True

def test_budget_alerts(client: TestClient, db_session: Session):
    # Setup category with limit
    cat = Category(name="Food", type="depense", monthly_limit=100.0)
    account = Account(name="Wallet", type="courant", currency="EUR", active=True)
    db_session.add_all([cat, account])
    db_session.commit()
    
    # Add transaction exceeding limit
    client.post(
        "/transactions",
        json={
            "account_id": account.id,
            "date": datetime.now().isoformat(),
            "type": "Sortie",
            "merchant": "Expensive Restaurant",
            "category_id": cat.id,
            "amount": 120.0
        }
    )
    
    response = client.get("/analytics/budget-alerts", params={"year": datetime.now().year, "month": datetime.now().month})
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) > 0
    food_alert = next(a for a in alerts if a["category_name"] == "Food")
    assert food_alert["monthly_spent"] == 120.0
    assert food_alert["monthly_limit"] == 100.0
    assert food_alert["monthly_ratio"] > 1.0

def test_intelligent_insights(client: TestClient, db_session: Session):
    # Insights usually compare months. Let's add data for current and last month.
    account = Account(name="Checking", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    
    today = date.today()
    last_month = today.replace(day=1) - timedelta(days=1)
    
    # Last month: 1000 spending
    dt_last = datetime.combine(last_month, datetime.min.time())
    db_session.add(Transaction(
        account_id=account.id, date=dt_last,
        month_label=month_label_from_date(dt_last),
        type="Sortie", merchant="Rent", amount=1000,
        original_amount=1000, currency="EUR", running_balance=0
    ))
    
    # This month: 2000 spending (huge increase)
    dt_now = datetime.now()
    db_session.add(Transaction(
        account_id=account.id, date=dt_now,
        month_label=month_label_from_date(dt_now),
        type="Sortie", merchant="Luxury", amount=2000,
        original_amount=2000, currency="EUR", running_balance=0
    ))
    db_session.commit()
    
    response = client.get("/analytics/insights", params={"year": today.year, "month": today.month})
    if response.status_code == 422:
        print(f"Insights 422 error: {response.json()}")
    assert response.status_code == 200
    insights = response.json()
    assert "health_score" in insights
    assert "insights" in insights
    # Should probably have an insight about spending increase
    # (Actual content depends on logic in analytics.py)
