from datetime import datetime, timedelta
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction

def test_anomaly_detection_category_increase(client, db_session):
    # Setup account and category
    acc = Account(name="Test Acc", type="courant", currency="EUR", active=True)
    cat = Category(name="Loisirs", type="depense")
    db_session.add_all([acc, cat])
    db_session.commit()

    # Create history for last 3 months (Avg = 50€)
    # May 2026 is current month (from system prompt date: Thursday 28 May 2026)
    # History: Feb, March, April
    history_dates = [
        datetime(2026, 2, 10),
        datetime(2026, 3, 10),
        datetime(2026, 4, 10),
    ]
    for d in history_dates:
        tx = Transaction(
            account_id=acc.id,
            date=d,
            month_label=d.strftime("%b %Y"),
            type="Sortie",
            merchant="Cinema",
            category_id=cat.id,
            amount=50.0,
            original_amount=50.0,
            currency="EUR",
            running_balance=1000.0
        )
        db_session.add(tx)
    
    # Current month: Huge expense (150€ > 2 * 50€)
    current_date = datetime(2026, 5, 15)
    current_tx = Transaction(
        account_id=acc.id,
        date=current_date,
        month_label="May 2026",
        type="Sortie",
        merchant="Parc Attraction",
        category_id=cat.id,
        amount=150.0,
        original_amount=150.0,
        currency="EUR",
        running_balance=850.0
    )
    db_session.add(current_tx)
    db_session.commit()

    # Call insights API
    response = client.get("/analytics/insights", params={"month": 5, "year": 2026})
    assert response.status_code == 200
    data = response.json()
    
    # Check for anomaly
    anomalies = [i for i in data["insights"] if i["type"] == "anomaly" and "Alerte catégorie" in i["title"]]
    assert len(anomalies) > 0
    assert "Loisirs" in anomalies[0]["description"]
    assert "150" in anomalies[0]["description"]
    assert "50" in anomalies[0]["description"]

def test_no_anomaly_when_under_threshold(client, db_session):
    # Setup account and category
    acc = Account(name="Test Acc 2", type="courant", currency="EUR", active=True)
    cat = Category(name="Courses", type="depense")
    db_session.add_all([acc, cat])
    db_session.commit()

    # History (Avg = 100€)
    for d in [datetime(2026, 2, 1), datetime(2026, 3, 1), datetime(2026, 4, 1)]:
        db_session.add(Transaction(
            account_id=acc.id, date=d, month_label=d.strftime("%b %Y"),
            type="Sortie", merchant="SuperU", category_id=cat.id,
            amount=100.0, original_amount=100.0, currency="EUR", running_balance=1000.0
        ))
    
    # Current month: Normal expense (120€ < 2 * 100€)
    db_session.add(Transaction(
        account_id=acc.id, date=datetime(2026, 5, 5), month_label="May 2026",
        type="Sortie", merchant="SuperU", category_id=cat.id,
        amount=120.0, original_amount=120.0, currency="EUR", running_balance=880.0
    ))
    db_session.commit()

    response = client.get("/analytics/insights", params={"month": 5, "year": 2026})
    data = response.json()
    
    anomalies = [i for i in data["insights"] if i["type"] == "anomaly" and "Alerte catégorie" in i["title"]]
    assert len(anomalies) == 0
