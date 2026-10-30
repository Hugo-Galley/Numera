from app.models.account import Account


def test_account_logo_roundtrip_and_validation(client, db_session):
    created = client.post("/accounts", json={"name": "CC", "type": "courant", "logo": "si:boursorama"})
    assert created.status_code == 201
    account_id = created.json()["id"]
    assert db_session.get(Account, account_id).logo == "si:boursorama"

    assert client.patch(f"/accounts/{account_id}", json={"logo": "http://evil/x.png"}).status_code == 422
    assert client.patch(f"/accounts/{account_id}", json={"logo": None}).status_code == 200
    db_session.expire_all()
    assert db_session.get(Account, account_id).logo is None
