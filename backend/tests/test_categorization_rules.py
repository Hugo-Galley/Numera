import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.account import Account
from app.models.category import Category
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction

def test_categorization_rule_import(client: TestClient, db_session: Session):
    # Setup
    account = Account(name="Checking", type="courant", currency="EUR", active=True)
    cat = Category(name="Food", type="depense")
    db_session.add_all([account, cat])
    db_session.commit()
    
    # Create rule: Merchant "KFC" -> Category "Food"
    rule = CategorizationRule(
        pattern="KFC",
        category_id=cat.id,
        merchant_name="KFC RESTAURANT",
        priority=10
    )
    db_session.add(rule)
    db_session.commit()
    
    # Import CSV
    csv_content = "\n".join([
        "Date,Mois,Type,Commercant,Categorie,Montant,Solde Compte,Note",
        "01/01/2026 12:00,Janvier,Sortie,KFC,Food,25.00,975.00,Lunch",
        "02/01/2026 12:00,Janvier,Sortie,Other,,10.00,965.00,Stuff",
    ])
    files = {"file": ("import.csv", csv_content.encode("utf-8"), "text/csv")}
    data = {"account_id": account.id, "create_missing_categories": False}
    
    response = client.post("/import/commit", data=data, files=files)
    if response.status_code == 422:
        print(f"DEBUG 422: {response.json()}")
    assert response.status_code == 200
    
    # Check transactions
    txs = db_session.query(Transaction).all()
    kfc_tx = next(tx for tx in txs if "KFC" in tx.merchant)
    assert kfc_tx.category_id == cat.id
    assert kfc_tx.merchant == "KFC RESTAURANT" # Normalized name from rule
    
    other_tx = next(tx for tx in txs if "Other" in tx.merchant)
    assert other_tx.category_id is None

def test_apply_rules_to_existing(client: TestClient, db_session: Session):
    # Setup
    account = Account(name="Checking", type="courant", currency="EUR", active=True)
    cat = Category(name="Transport", type="depense")
    db_session.add_all([account, cat])
    db_session.commit()
    
    tx = Transaction(
        account_id=account.id,
        date=datetime.now(),
        month_label="Juin",
        type="Sortie",
        merchant="Uber",
        amount=15,
        original_amount=15,
        currency="EUR",
        category_id=None,
        running_balance=100
    )
    db_session.add(tx)
    db_session.commit()
    
    # Create rule
    rule = CategorizationRule(pattern="Uber", category_id=cat.id)
    db_session.add(rule)
    db_session.commit()
    
    # Check if we can query it directly
    rules = db_session.query(CategorizationRule).all()
    print(f"DEBUG: Found {len(rules)} rules in db_session")
    
    # Apply rules
    response = client.post("/categorization-rules/apply-all")
    assert response.status_code == 200
    assert response.json()["modified_count"] == 1
    
    db_session.refresh(tx)
    assert tx.category_id == cat.id
