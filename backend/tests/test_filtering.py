import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction

def test_multicriteria_filtering(client: TestClient, db_session: Session):
    # Setup
    account = Account(name="Checking", type="courant", currency="EUR", active=True)
    cat1 = Category(name="Food", type="depense")
    cat2 = Category(name="Transport", type="depense")
    db_session.add_all([account, cat1, cat2])
    db_session.commit()
    
    # Transactions
    t1 = Transaction(
        account_id=account.id, date=datetime(2026, 1, 1), type="Sortie",
        merchant="McDonalds", category_id=cat1.id, amount=10, 
        original_amount=10, currency="EUR", running_balance=0, month_label="Janvier"
    )
    t2 = Transaction(
        account_id=account.id, date=datetime(2026, 1, 2), type="Sortie",
        merchant="Uber", category_id=cat2.id, amount=25, 
        original_amount=25, currency="EUR", running_balance=0, month_label="Janvier"
    )
    t3 = Transaction(
        account_id=account.id, date=datetime(2026, 2, 1), type="Entree",
        merchant="Salary", category_id=None, amount=2000, 
        original_amount=2000, currency="EUR", running_balance=0, month_label="Fevrier"
    )
    db_session.add_all([t1, t2, t3])
    db_session.commit()
    
    # 1. Filter by category
    response = client.get("/transactions", params={"category_id": cat1.id})
    assert len(response.json()) == 1
    assert response.json()[0]["merchant"] == "McDonalds"
    
    # 2. Filter by type
    response = client.get("/transactions", params={"type": "Entree"})
    assert len(response.json()) == 1
    assert response.json()[0]["merchant"] == "Salary"
    
    # 3. Filter by amount range
    response = client.get("/transactions", params={"min_amount": 20, "max_amount": 30})
    assert len(response.json()) == 1
    assert response.json()[0]["merchant"] == "Uber"
    
    # 4. Filter by merchant name
    response = client.get("/transactions", params={"merchant": "McD"})
    assert len(response.json()) == 1
    
    # 5. Filter by date range
    response = client.get("/transactions", params={"start_date": "2026-02-01T00:00:00"})
    assert len(response.json()) == 1
    assert response.json()[0]["merchant"] == "Salary"
