from app.models.account import Account


def test_unknown_account_type_is_rejected_on_create_and_update(client, db_session):
    """Un compte « bank » finissait classé INVESTISSEMENT sur le tableau de bord."""
    assert client.post("/accounts", json={"name": "Carte", "type": "bank", "currency": "EUR"}).status_code == 422

    account_id = client.post("/accounts", json={"name": "Carte", "type": "courant", "currency": "EUR"}).json()["id"]
    assert client.patch(f"/accounts/{account_id}", json={"type": "bank"}).status_code == 422
    assert client.patch(f"/accounts/{account_id}", json={"type": "assurance_vie"}).status_code == 200


def test_legacy_account_with_unknown_type_still_lists(client, db_session):
    db_session.add(Account(name="Ancien", type="bank", currency="EUR", active=True))
    db_session.commit()

    response = client.get("/accounts")
    assert response.status_code == 200
    assert any(a["type"] == "bank" for a in response.json())
