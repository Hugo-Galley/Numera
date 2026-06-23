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

