"""Un seul commit, après le recalcul des soldes : une erreur pendant le recalcul n'écrit rien."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.transaction import Transaction
from app.services.budget import transaction_writes


def _fresh(db_session):
    return sessionmaker(bind=db_session.get_bind())()


def _server_error(method, url, **kwargs):
    """Requête dont l'erreur serveur devient un 500 (les overrides de la fixture `client` restent actifs)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        return c.request(method, url, **kwargs).status_code


def _boom(*_args, **_kwargs):
    raise RuntimeError("recalcul impossible")


@pytest.fixture()
def account_id(client):
    resp = client.post("/accounts/", json={"name": "Courant", "type": "courant", "currency": "EUR"})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


def _create(client, account_id, amount=10.0, merchant="Boulangerie"):
    resp = client.post("/transactions/", json={
        "account_id": account_id, "date": datetime(2026, 1, 5).isoformat(), "type": "Sortie",
        "merchant": merchant, "amount": amount,
    })
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


def test_create_error_during_recalculation_commits_nothing(client, db_session, account_id, monkeypatch):
    monkeypatch.setattr(transaction_writes, "recalculate_running_balances", _boom)
    assert _server_error("POST", "/transactions/", json={
            "account_id": account_id, "date": datetime(2026, 1, 5).isoformat(), "type": "Sortie",
            "merchant": "X", "amount": 5.0,
        }) == 500
    assert _fresh(db_session).query(Transaction).count() == 0


def test_update_error_during_recalculation_keeps_committed_values(client, db_session, account_id, monkeypatch):
    tx_id = _create(client, account_id)
    monkeypatch.setattr(transaction_writes, "recalculate_running_balances", _boom)
    assert _server_error("PATCH", f"/transactions/{tx_id}", json={"amount": 99.0}) == 500
    assert _fresh(db_session).get(Transaction, tx_id).amount == 10.0


def test_delete_error_during_recalculation_keeps_the_transaction(client, db_session, account_id, monkeypatch):
    tx_id = _create(client, account_id)
    monkeypatch.setattr(transaction_writes, "recalculate_running_balances", _boom)
    assert _server_error("DELETE", f"/transactions/{tx_id}") == 500
    assert _fresh(db_session).get(Transaction, tx_id) is not None


def test_bulk_update_error_during_recalculation_keeps_committed_values(client, db_session, account_id, monkeypatch):
    tx_id = _create(client, account_id)
    monkeypatch.setattr(transaction_writes, "recalculate_running_balances", _boom)
    assert _server_error("PATCH", "/transactions/bulk", json={"ids": [tx_id], "merchant": "Autre"}) == 500
    assert _fresh(db_session).get(Transaction, tx_id).merchant == "Boulangerie"


def test_bulk_delete_error_during_recalculation_keeps_the_transactions(client, db_session, account_id, monkeypatch):
    tx_id = _create(client, account_id)
    monkeypatch.setattr(transaction_writes, "recalculate_running_balances", _boom)
    assert _server_error("POST", "/transactions/bulk-delete", json={"ids": [tx_id]}) == 500
    assert _fresh(db_session).get(Transaction, tx_id) is not None
