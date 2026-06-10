import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.account import Account
from app.models.tag import Tag
from app.models.transaction import Transaction

def test_create_and_list_tags(client: TestClient):
    # Create tag
    response = client.post(
        "/tags",
        json={"name": "Vacances", "color": "#FF0000"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Vacances"
    assert data["color"] == "#FF0000"
    tag_id = data["id"]

    # List tags
    response = client.get("/tags")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(t["id"] == tag_id for t in data)

def test_transaction_with_tags(client: TestClient, db_session: Session):
    # Create account
    account = Account(name="Test Account", type="Courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()

    # Create tag
    response = client.post(
        "/tags",
        json={"name": "Projet Perso", "color": "#00FF00"}
    )
    tag_id = response.json()["id"]

    # Create transaction with tag
    tx_data = {
        "account_id": account.id,
        "date": datetime.now().isoformat(),
        "type": "Sortie",
        "merchant": "Amazon",
        "amount": 50.0,
        "tag_ids": [tag_id]
    }
    response = client.post("/transactions", json=tx_data)
    assert response.status_code == 201
    data = response.json()
    assert len(data["tags"]) == 1
    assert data["tags"][0]["id"] == tag_id

    tx_id = data["id"]

    # Update transaction tags
    response = client.patch(
        f"/transactions/{tx_id}",
        json={"tag_ids": []}
    )
    assert response.status_code == 200
    assert len(response.json()["tags"]) == 0

    # Bulk update tags
    tx_data2 = tx_data.copy()
    tx_data2["merchant"] = "eBay"
    response = client.post("/transactions", json=tx_data2)
    tx_id2 = response.json()["id"]

    bulk_data = {
        "ids": [tx_id, tx_id2],
        "tag_ids": [tag_id]
    }
    response = client.patch("/transactions/bulk", json=bulk_data)
    assert response.status_code == 204

    # Verify bulk update
    response = client.get(f"/transactions?search=Amazon")
    txs = response.json()
    assert any(tx["id"] == tx_id and len(tx["tags"]) == 1 for tx in txs)

def test_filter_transactions_by_tag(client: TestClient, db_session: Session):
    # Create account
    account = Account(name="Filter Account", type="Courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()

    # Create two tags
    tag1_id = client.post("/tags", json={"name": "Tag 1"}).json()["id"]
    tag2_id = client.post("/tags", json={"name": "Tag 2"}).json()["id"]

    # Create transactions
    client.post("/transactions", json={
        "account_id": account.id, "date": datetime.now().isoformat(),
        "type": "Sortie", "merchant": "M1", "amount": 10.0, "tag_ids": [tag1_id]
    })

    client.post("/transactions", json={
        "account_id": account.id, "date": datetime.now().isoformat(),
        "type": "Sortie", "merchant": "M2", "amount": 20.0, "tag_ids": [tag2_id]
    })

    # Filter by tag1
    response = client.get(f"/transactions?tag_ids={tag1_id}")
    data = response.json()
    assert len(data) == 1
    assert data[0]["merchant"] == "M1"

    # Filter by tag2
    response = client.get(f"/transactions?tag_ids={tag2_id}")
    data = response.json()
    assert len(data) == 1
    assert data[0]["merchant"] == "M2"
