from app.models.account import Account


def test_create_assurance_vie_account(client, db_session):
    payload = {
        "name": "Mon Assurance Vie",
        "type": "assurance_vie",
        "currency": "EUR",
        "fonds_euros_pct": 60.0,
        "fonds_investis_pct": 40.0
    }
    response = client.post("/accounts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Mon Assurance Vie"
    assert data["type"] == "assurance_vie"
    assert data["fonds_euros_pct"] == 60.0
    assert data["fonds_investis_pct"] == 40.0

    # Verify db storage
    db_acc = db_session.query(Account).filter(Account.id == data["id"]).first()
    assert db_acc is not None
    assert db_acc.type == "assurance_vie"
    assert db_acc.fonds_euros_pct == 60.0
    assert db_acc.fonds_investis_pct == 40.0


def test_update_assurance_vie_account(client, db_session):
    # Setup account
    acc = Account(
        name="AV Fortuneo",
        type="assurance_vie",
        currency="EUR",
        active=True,
        fonds_euros_pct=80.0,
        fonds_investis_pct=20.0
    )
    db_session.add(acc)
    db_session.commit()

    # Update splits
    payload = {
        "fonds_euros_pct": 50.0,
        "fonds_investis_pct": 50.0
    }
    response = client.patch(f"/accounts/{acc.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["fonds_euros_pct"] == 50.0
    assert data["fonds_investis_pct"] == 50.0

    # Verify db update
    db_session.refresh(acc)
    assert acc.fonds_euros_pct == 50.0
    assert acc.fonds_investis_pct == 50.0


def test_assurance_vie_snapshots_and_analytics(client, db_session):
    # 1. Create assurance_vie account
    acc = Account(
        name="AV Fortuneo Snap",
        type="assurance_vie",
        currency="EUR",
        active=True,
        fonds_euros_pct=70.0,
        fonds_investis_pct=30.0
    )
    db_session.add(acc)
    db_session.commit()

    # 2. Add balance snapshot for the account
    snap_payload = {
        "account_id": acc.id,
        "date": "2026-06-01T00:00:00",
        "current_value": 10000.0,
        "note": "Initial snap",
        "is_zero_point": True
    }
    snap_response = client.post("/balance-snapshots", json=snap_payload)
    assert snap_response.status_code == 201
    snap_data = snap_response.json()
    assert snap_data["current_value"] == 10000.0
    assert snap_data["is_zero_point"] is True

    # 3. Request investment analytics for the account
    analytics_response = client.get(f"/analytics/investments/{acc.id}")
    assert analytics_response.status_code == 200
    analytics_data = analytics_response.json()
    print("ANALYTICS DATA IS:", analytics_data)
    assert analytics_data["totals"]["net_invested"] == 10000.0  # fallback is zero-point current_value

    # 4. Request performance history for the account
    perf_response = client.get(f"/analytics/investments/{acc.id}/performance-history")
    assert perf_response.status_code == 200



def test_assurance_vie_counts_bank_transfers_alongside_versements(client, db_session):
    """Versements saisis + virements bancaires (Entree) : les deux font le capital investi, partout."""
    from datetime import datetime

    from app.models.balance_snapshot import BalanceSnapshot
    from app.models.investment_transaction import InvestmentTransaction
    from app.models.transaction import Transaction

    acc = Account(name="Linxea", type="assurance_vie", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    db_session.add_all([
        InvestmentTransaction(account_id=acc.id, date=datetime(2026, 7, 1), type="versement", amount=500.0, currency="EUR", original_amount=500.0),
        InvestmentTransaction(account_id=acc.id, date=datetime(2026, 9, 2), type="versement", amount=5437.66, currency="EUR", original_amount=5437.66),
        *[
            Transaction(account_id=acc.id, date=d, month_label="m", type="Entree", merchant="Virement depuis Principale",
                        amount=100.0, running_balance=0.0, currency="EUR", original_amount=100.0, is_transfer=True)
            for d in (datetime(2026, 8, 30), datetime(2026, 9, 11), datetime(2026, 10, 10))
        ],
        # Entree non reconnue comme virement : ignorée dès qu'il y a des versements saisis
        Transaction(account_id=acc.id, date=datetime(2026, 9, 15), month_label="m", type="Entree", merchant="Divers",
                    amount=50.0, running_balance=0.0, currency="EUR", original_amount=50.0),
        BalanceSnapshot(account_id=acc.id, date=datetime(2026, 9, 30), current_value=6231.21),
        BalanceSnapshot(account_id=acc.id, date=datetime(2026, 10, 16), current_value=6300.0),
    ])
    db_session.commit()

    totals = client.get(f"/analytics/investments/{acc.id}").json()["totals"]
    assert totals["net_invested"] == 6237.66
    assert totals["gain_eur"] == 62.34

    overview = next(i for i in client.get("/analytics/investments").json()["items"] if i["account_id"] == acc.id)
    assert overview["net_invested"] == 6237.66

    history = client.get(f"/analytics/investments/{acc.id}/performance-history").json()["items"]
    assert [p["net_invested"] for p in history] == [6137.66, 6237.66]
    assert history[-1]["gain_eur"] == totals["gain_eur"]
