import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.merchant import Merchant, MerchantAlias
from app.models.transaction import Transaction
from datetime import datetime

def test_create_merchant(client: TestClient):
    response = client.post(
        "/merchants/",
        json={"name": "Starbucks", "aliases": ["STARBUCKS COFFEE", "SBUX 1234"]}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Starbucks"
    assert len(data["aliases"]) == 2
    assert any(a["label"] == "STARBUCKS COFFEE" for a in data["aliases"])

def test_auto_normalize(client: TestClient, db_session: Session):
    # 1. Create a merchant with an alias
    response = client.post(
        "/merchants/",
        json={"name": "Amazon", "aliases": ["AMZN Digital", "AMAZON.FR"]}
    )
    merchant_id = response.json()["id"]

    # 2. Create some accounts and transactions
    from app.models.account import Account
    account = Account(name="Bank", type="courant", currency="EUR")
    db_session.add(account)
    db_session.flush()

    t1 = Transaction(
        account_id=account.id,
        date=datetime.now(),
        month_label="2026-06",
        type="Sortie",
        merchant="AMZN Digital",
        amount=-10.0,
        original_amount=-10.0,
        running_balance=100.0
    )
    t2 = Transaction(
        account_id=account.id,
        date=datetime.now(),
        month_label="2026-06",
        type="Sortie",
        merchant="Other Shop",
        amount=-20.0,
        original_amount=-20.0,
        running_balance=80.0
    )
    db_session.add_all([t1, t2])
    db_session.commit()

    # 3. Run auto-normalize
    response = client.post("/merchants/auto-normalize")
    assert response.status_code == 200
    assert response.json()["normalized_count"] == 1

    # 4. Verify transaction is normalized
    db_session.refresh(t1)
    db_session.refresh(t2)
    assert t1.merchant_id == merchant_id
    assert t2.merchant_id is None

def test_suggestions(client: TestClient, db_session: Session):
    from app.models.account import Account
    account = Account(name="Bank", type="courant", currency="EUR")
    db_session.add(account)
    db_session.flush()

    # Create 6 transactions for the same unnormalized merchant
    for _ in range(6):
        t = Transaction(
            account_id=account.id,
            date=datetime.now(),
            month_label="2026-06",
            type="Sortie",
            merchant="POPULAR SHOP",
            amount=-10.0,
            original_amount=-10.0,
            running_balance=100.0
        )
        db_session.add(t)
    db_session.commit()

    response = client.get("/merchants/suggestions/unnormalized?min_count=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["label"] == "POPULAR SHOP"
    assert data[0]["count"] == 6
