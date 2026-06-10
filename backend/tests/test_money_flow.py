import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.account import Account

def test_money_flow_endpoint(client: TestClient, db_session: Session):
    # 1. Setup accounts and categories
    acc = Account(name="Test Account", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    
    cat_fixed = Category(name="Loyer", type="Sortie")
    cat_var = Category(name="Courses", type="Sortie")
    cat_sav = Category(name="Epargne", type="Sortie")
    db_session.add_all([cat_fixed, cat_var, cat_sav])
    db_session.commit()
    
    # 2. Add transactions for June 2026
    # Income
    db_session.add(Transaction(
        account_id=acc.id,
        date=datetime(2026, 6, 5),
        month_label="2026-06",
        type="Entree",
        merchant="Salary",
        amount=3000.0,
        currency="EUR",
        original_amount=3000.0,
        running_balance=4000.0
    ))
    
    # Fixed Charge (Recurring)
    db_session.add(Transaction(
        account_id=acc.id,
        date=datetime(2026, 6, 1),
        month_label="2026-06",
        type="Sortie",
        merchant="Landlord",
        category_id=cat_fixed.id,
        amount=1000.0,
        currency="EUR",
        original_amount=1000.0,
        running_balance=3000.0,
        is_recurring=True
    ))
    
    # Variable Expense
    db_session.add(Transaction(
        account_id=acc.id,
        date=datetime(2026, 6, 10),
        month_label="2026-06",
        type="Sortie",
        merchant="Supermarket",
        category_id=cat_var.id,
        amount=200.0,
        currency="EUR",
        original_amount=200.0,
        running_balance=2800.0,
        is_recurring=False
    ))
    
    # Savings
    db_session.add(Transaction(
        account_id=acc.id,
        date=datetime(2026, 6, 20),
        month_label="2026-06",
        type="Sortie",
        merchant="Transfer to Savings",
        category_id=cat_sav.id,
        amount=500.0,
        currency="EUR",
        original_amount=500.0,
        running_balance=2300.0,
        is_recurring=False
    ))
    
    db_session.commit()
    
    # 3. Call the endpoint
    response = client.get("/analytics/money-flow?month=6&year=2026")
    assert response.status_code == 200
    data = response.json()
    
    assert data["income"] == 3000.0
    assert data["fixed_charges"]["amount"] == 1000.0
    assert data["variable_expenses"]["amount"] == 200.0
    assert data["savings"]["amount"] == 500.0
    assert data["investments"]["amount"] == 0.0
    assert data["remainder"]["amount"] == 3000.0 - (1000.0 + 200.0 + 500.0) # 1300.0
    
    assert len(data["top_fixed"]) > 0
    assert data["top_fixed"][0]["name"] == "Landlord (Loyer)"
    assert data["top_variable"][0]["name"] == "Courses"
    assert len(data["top_investments"]) == 0
