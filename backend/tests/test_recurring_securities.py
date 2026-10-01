import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.portfolio_holding import PortfolioHolding
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.core.recurring import generate_recurring_transactions


def test_recurring_transaction_with_securities_api(client: TestClient, db_session: Session):
    # Setup investment account
    account = Account(name="PEA Fortuneo", type="investissement", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()

    # 1. Create recurring transaction with securities (DCA ETF)
    payload = {
        "account_id": account.id,
        "name": "DCA Amundi MSCI World",
        "type": "versement",
        "amount": 500.0,
        "currency": "EUR",
        "frequency": "monthly",
        "day_of_month": 5,
        "start_date": (datetime.now() - timedelta(days=60)).isoformat(),
        "is_active": True,
        "auto_generate": True,
        "ticker": "CW8.PA",
        "isin": "FR0010315770",
        "quantity": 1.0,
        "unit_price": 500.0,
        "asset_class": "Actions",
        "sector": "Monde",
        "geographic_zone": "FRA",
    }
    res = client.post("/recurring-transactions/", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ticker"] == "CW8.PA"
    assert data["isin"] == "FR0010315770"
    assert data["quantity"] == 1.0
    assert data["unit_price"] == 500.0

    rec_id = data["id"]

    # 2. Get list of recurring transactions
    list_res = client.get("/recurring-transactions/")
    assert list_res.status_code == 200
    items = list_res.json()
    matched = next((item for item in items if item["id"] == rec_id), None)
    assert matched is not None
    assert matched["ticker"] == "CW8.PA"

    # 3. Update recurring transaction
    update_res = client.patch(f"/recurring-transactions/{rec_id}", json={"quantity": 2.0, "amount": 1000.0})
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["quantity"] == 2.0
    assert updated_data["amount"] == 1000.0


@pytest.mark.anyio
async def test_recurring_generation_creates_investment_tx_and_holding(db_session: Session):
    account = Account(name="CTO Trade Republic", type="investissement", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()

    # Recurring rule started 45 days ago, so at least 1 monthly occurrence is due
    past_date = datetime.now() - timedelta(days=45)
    rd = RecurringTransaction(
        account_id=account.id,
        name="DCA Apple",
        type="versement",
        amount=360.0,
        currency="EUR",
        frequency="monthly",
        day_of_month=past_date.day,
        start_date=past_date,
        is_active=True,
        auto_generate=True,
        ticker="AAPL",
        quantity=2.0,
        unit_price=180.0,
    )
    db_session.add(rd)
    db_session.commit()

    # Run generation
    count = await generate_recurring_transactions(db_session)
    assert count >= 1

    # Verify investment transaction was created
    inv_tx = db_session.query(InvestmentTransaction).filter(
        InvestmentTransaction.recurring_transaction_id == rd.id
    ).first()
    assert inv_tx is not None
    assert inv_tx.ticker == "AAPL"
    assert inv_tx.quantity == 2.0
    assert inv_tx.unit_price == 180.0

    # Verify portfolio holding was automatically updated/created
    holding = db_session.query(PortfolioHolding).filter(
        PortfolioHolding.account_id == account.id,
        PortfolioHolding.ticker == "AAPL"
    ).first()
    assert holding is not None
    assert holding.quantity == 2.0
    assert holding.buy_price_avg == 180.0
