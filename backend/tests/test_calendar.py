import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction

def test_calendar_analytics(client: TestClient, db_session: Session):
    # 1. Setup: Create account and category
    account = Account(name="Test Account", type="courant", currency="EUR")
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    
    category = Category(name="Test Category", type="depense")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    
    # 2. Add a starting transaction
    now = datetime.now()
    # Let's test for next month to ensure projection works
    if now.month == 12:
        test_month = 1
        test_year = now.year + 1
    else:
        test_month = now.month + 1
        test_year = now.year

    # Start balance at beginning of test month
    start_tx = Transaction(
        account_id=account.id,
        date=datetime(test_year, test_month, 1) - timedelta(days=1),
        month_label="Previous",
        type="Solde Initial",
        merchant="Initial",
        amount=1000.0,
        currency="EUR",
        original_amount=1000.0,
        running_balance=1000.0,
        category_id=category.id
    )
    db_session.add(start_tx)
    
    # 3. Add a recurring transaction for test month
    recur = RecurringTransaction(
        account_id=account.id,
        name="Rent",
        type="Sortie",
        amount=500.0,
        currency="EUR",
        category_id=category.id,
        frequency="monthly",
        start_date=datetime(test_year, test_month, 5),
        is_active=True
    )
    db_session.add(recur)
    db_session.commit()
    
    # 4. Fetch calendar for test month
    response = client.get(
        f"/analytics/calendar?month={test_month}&year={test_year}&account_id={account.id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["month"] == test_month
    assert data["year"] == test_year
    
    events = data["events"]
    # Should only have projected Rent
    assert len(events) == 1
    assert events[0]["name"] == "Rent"
    assert events[0]["is_projected"] == True
    
    # Check daily balance at the end of month
    # Start: 1000, Proj Rent: -500 => End: 500
    last_balance = data["daily_balances"][-1]["balance"]
    assert last_balance == 500.0

def test_calendar_analytics_global(client: TestClient, db_session: Session):
    # 1. Setup: Create 2 accounts in different currencies
    acc1 = Account(name="EUR Acc", type="courant", currency="EUR")
    acc2 = Account(name="USD Acc", type="courant", currency="USD")
    db_session.add_all([acc1, acc2])
    db_session.commit()
    
    # 2. Starting balances (last month)
    now = datetime.now()
    if now.month == 12:
        test_month, test_year = 1, now.year + 1
    else:
        test_month, test_year = now.month + 1, now.year
    
    last_month_end = datetime(test_year, test_month, 1) - timedelta(days=1)
    
    db_session.add(Transaction(
        account_id=acc1.id, date=last_month_end, month_label="Prev",
        type="Solde Initial", merchant="Init", amount=1000.0, running_balance=1000.0, currency="EUR",
        original_amount=1000.0
    ))
    db_session.add(Transaction(
        account_id=acc2.id, date=last_month_end, month_label="Prev",
        type="Solde Initial", merchant="Init", amount=1080.0, running_balance=1080.0, currency="USD",
        original_amount=1080.0
    ))
    db_session.commit()
    
    # 3. Fetch global calendar
    # Note: USD 1080 should be approx EUR 1000 (depending on mock rates)
    # In currency.py fallback: {"EUR": 1.0, "USD": 1.08}
    # So 1080 USD / 1.08 = 1000 EUR. Total start = 2000 EUR.
    response = client.get(f"/analytics/calendar?month={test_month}&year={test_year}")
    assert response.status_code == 200
    data = response.json()
    
    # Start of month balance should be around 2000 (1000 EUR + 1080 USD)
    # 1080 USD is approx 1000 EUR depending on the rate used.
    # We just want to ensure it's not 0 and roughly correct.
    assert 1800.0 < data["daily_balances"][0]["balance"] < 2200.0
