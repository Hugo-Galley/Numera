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


def test_transactions_pagination_skip_limit(client: TestClient, db_session: Session):
    account = Account(name="PaginationTest", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()

    # Create 5 transactions
    for i in range(5):
        tx = Transaction(
            account_id=account.id,
            date=datetime(2026, 1, i + 1),
            type="Sortie",
            merchant=f"Shop_{i}",
            amount=10 + i,
            original_amount=10 + i,
            currency="EUR",
            running_balance=100 - i,
            month_label="Janvier",
        )
        db_session.add(tx)
    db_session.commit()

    # Limit 2, Skip 0 -> First 2
    r_page1 = client.get("/transactions", params={"account_id": account.id, "limit": 2, "skip": 0})
    assert r_page1.status_code == 200
    p1_items = r_page1.json()
    assert len(p1_items) == 2

    # Limit 2, Skip 2 -> Next 2
    r_page2 = client.get("/transactions", params={"account_id": account.id, "limit": 2, "skip": 2})
    assert r_page2.status_code == 200
    p2_items = r_page2.json()
    assert len(p2_items) == 2

    # Check distinct items
    p1_ids = [t["id"] for t in p1_items]
    p2_ids = [t["id"] for t in p2_items]
    assert len(set(p1_ids).intersection(set(p2_ids))) == 0

    # Limit 2, Skip 4 -> Last 1
    r_page3 = client.get("/transactions", params={"account_id": account.id, "limit": 2, "skip": 4})
    assert r_page3.status_code == 200
    p3_items = r_page3.json()
    assert len(p3_items) == 1


def test_account_history_beyond_default_limit_is_reachable_page_by_page(client: TestClient, db_session: Session):
    """La page d'un compte s'arrêtait aux 100 lignes par défaut : les pages de 200 doivent tout couvrir."""
    account = Account(name="Long", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    # 250 lignes sur 10 jours : beaucoup d'égalités de date, l'ordre doit rester stable entre deux pages
    db_session.add_all([
        Transaction(
            account_id=account.id, date=datetime(2026, 1, 1) + timedelta(days=i % 10), type="Sortie",
            merchant=f"Shop_{i}", amount=1, original_amount=1, currency="EUR", running_balance=0, month_label="Janvier",
        )
        for i in range(250)
    ])
    db_session.commit()

    assert len(client.get("/transactions", params={"account_id": account.id}).json()) == 100

    page1 = client.get("/transactions", params={"account_id": account.id, "skip": 0, "limit": 200}).json()
    page2 = client.get("/transactions", params={"account_id": account.id, "skip": 200, "limit": 200}).json()
    assert len(page1) == 200
    assert len(page2) == 50
    assert len({tx["id"] for tx in page1 + page2}) == 250


def test_drilldown_filters_match_analytics_scope(client, db_session):
    from datetime import datetime as dt

    from app.core.finance import month_label_from_date
    from app.models.account import Account
    from app.models.merchant import Merchant
    from app.models.transaction import Transaction

    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    carrefour = Merchant(name="Carrefour")
    db_session.add_all([courant, pea, carrefour])
    db_session.commit()

    def tx(account, merchant, merchant_id=None):
        d = dt(2025, 10, 5)
        t = Transaction(
            account_id=account.id, date=d, month_label=month_label_from_date(d), type="Sortie", merchant=merchant,
            merchant_id=merchant_id, amount=10.0, original_amount=10.0, currency="EUR", running_balance=0.0,
        )
        db_session.add(t)
        db_session.commit()
        return t

    a = tx(courant, "CARREFOUR MARKET 123", carrefour.id)
    tx(pea, "FRAIS")
    params = {"month": 10, "year": 2025, "period": True, "budget_scope": True}

    ids = [t["id"] for t in client.get("/transactions", params={**params, "uncategorized": True}).json()]
    assert ids == [a.id]  # le PEA est hors périmètre budget
    ids = [t["id"] for t in client.get("/transactions", params={**params, "merchant_name": "Carrefour"}).json()]
    assert ids == [a.id]
