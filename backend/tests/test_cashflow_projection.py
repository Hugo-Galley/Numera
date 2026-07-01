import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.core.finance import month_label_from_date

def test_cashflow_projection(client: TestClient, db_session: Session):
    # Setup: Account with balance
    account = Account(name="Checking", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    
    now = datetime.now()
    tx = Transaction(
        account_id=account.id,
        date=now - timedelta(days=1),
        month_label=month_label_from_date(now - timedelta(days=1)),
        type="Solde Initial",
        merchant="Initial",
        amount=1000,
        original_amount=1000,
        currency="EUR",
        running_balance=1000
    )
    db_session.add(tx)
    
    # Setup: Recurring transaction
    rd = RecurringTransaction(
        account_id=account.id,
        name="Salary",
        type="Entree",
        amount=2000,
        currency="EUR",
        frequency="monthly",
        day_of_month=(now + timedelta(days=2)).day,
        start_date=now - timedelta(days=32),
        is_active=True,
        auto_generate=False
    )
    rd2 = RecurringTransaction(
        account_id=account.id,
        name="Rent",
        type="Sortie",
        amount=800,
        currency="EUR",
        frequency="monthly",
        day_of_month=(now + timedelta(days=5)).day,
        start_date=now - timedelta(days=32),
        is_active=True,
        auto_generate=False
    )
    db_session.add_all([rd, rd2])
    db_session.commit()
    
    response = client.get("/analytics/cashflow-projection", params={"days": 30})
    assert response.status_code == 200
    data = response.json()
    
    assert data["current_balance"] == 1000.0
    # One salary + one rent expected in next 30 days
    # (Simplified since dates might shift month boundaries, but usually 1 occurrence each)
    assert len(data["events"]) >= 2
    
    # Check projected balance
    # 1000 + 2000 - 800 = 2200
    assert data["projected_balance"] >= 2200.0
    assert data["days"] == 30
    assert len(data["points"]) == 31 # today + 30 days
