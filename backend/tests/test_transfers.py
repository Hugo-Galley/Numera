from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transaction import Transaction
from app.core.finance import month_label_from_date

def test_transfer_detection_and_linking(client: TestClient, db_session: Session):
    # 1. Create two accounts
    acc1 = Account(name="Checking", type="courant", currency="EUR", active=True)
    acc2 = Account(name="Savings", type="epargne", currency="EUR", active=True)
    db_session.add_all([acc1, acc2])
    db_session.commit()

    # 2. Create two transactions that look like a transfer
    date = datetime(2026, 6, 1, 12, 0)
    tx_out = Transaction(
        account_id=acc1.id,
        date=date,
        month_label=month_label_from_date(date),
        type="Sortie",
        merchant="Transfer to Savings",
        amount=500.0,
        original_amount=500.0,
        currency="EUR",
        running_balance=-500.0
    )
    tx_in = Transaction(
        account_id=acc2.id,
        date=date + timedelta(hours=2),
        month_label=month_label_from_date(date),
        type="Entree",
        merchant="Transfer from Checking",
        amount=500.0,
        original_amount=500.0,
        currency="EUR",
        running_balance=500.0
    )
    db_session.add_all([tx_out, tx_in])
    db_session.commit()

    # 3. Detect potential transfers
    response = client.get("/transactions/potential-transfers")
    assert response.status_code == 200
    pairs = response.json()
    assert len(pairs) >= 1
    
    # Check if our pair is found
    found = False
    for pair in pairs:
        if pair["sortie"]["id"] == tx_out.id and pair["entree"]["id"] == tx_in.id:
            found = True
            break
    assert found

    # 4. Link them
    response = client.post(f"/transactions/{tx_out.id}/link/{tx_in.id}")
    assert response.status_code == 200
    
    db_session.refresh(tx_out)
    db_session.refresh(tx_in)
    assert tx_out.is_transfer is True
    assert tx_out.linked_transaction_id == tx_in.id
    assert tx_in.is_transfer is True
    assert tx_in.linked_transaction_id == tx_out.id

    # 5. Verify analytics exclude them
    # First check without transfers (they should be 0 if excluded)
    response = client.get("/analytics/budget", params={"month": 6, "year": 2026})
    assert response.status_code == 200
    data = response.json()
    assert data["depenses_totales"] == 0.0
    assert data["revenus_totaux"] == 0.0

    # 6. Unlink them
    response = client.post(f"/transactions/{tx_out.id}/unlink")
    assert response.status_code == 200
    
    # 7. Verify analytics INCLUDE them again
    response = client.get("/analytics/budget", params={"month": 6, "year": 2026})
    assert response.status_code == 200
    data = response.json()
    assert data["depenses_totales"] == 500.0
    assert data["revenus_totaux"] == 500.0

def test_investment_transfer_and_ignore(client: TestClient, db_session: Session):
    from app.models.investment_transaction import InvestmentTransaction

    # 1. Create accounts
    acc_check = Account(name="Checking", type="courant", currency="EUR", active=True)
    acc_inv = Account(name="Broker", type="investissement", currency="EUR", active=True)
    db_session.add_all([acc_check, acc_inv])
    db_session.commit()

    # 2. Create transactions
    date = datetime(2026, 6, 10, 12, 0)
    tx_out = Transaction(
        account_id=acc_check.id,
        date=date,
        month_label=month_label_from_date(date),
        type="Sortie",
        merchant="Transfer to Broker",
        amount=1000.0,
        original_amount=1000.0,
        currency="EUR",
        running_balance=-1000.0
    )
    itx_in = InvestmentTransaction(
        account_id=acc_inv.id,
        date=date + timedelta(days=1),
        type="versement",
        amount=1000.0,
        original_amount=1000.0,
        currency="EUR"
    )
    db_session.add_all([tx_out, itx_in])
    db_session.commit()

    # 3. Detect
    response = client.get("/transactions/potential-transfers")
    assert response.status_code == 200
    pairs = response.json()
    assert any(p["type"] == "investment" and p["sortie"]["id"] == tx_out.id for p in pairs)

    # 4. Ignore
    response = client.post(f"/transactions/{tx_out.id}/ignore")
    assert response.status_code == 204

    # 5. Detect again (should be empty)
    response = client.get("/transactions/potential-transfers")
    assert response.status_code == 200
    pairs = response.json()
    assert not any(p["sortie"]["id"] == tx_out.id for p in pairs)
