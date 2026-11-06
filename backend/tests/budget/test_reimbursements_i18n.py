"""Refus et erreurs des remboursements dans la langue de l'interface (Accept-Language)."""
from datetime import datetime

import pytest

from app.core.i18n import set_language
from tests.budget.test_reimbursements import make_account, tx

EN = {"Accept-Language": "en"}


@pytest.fixture(autouse=True)
def _reset_language():
    set_language("fr")
    yield
    set_language("fr")


@pytest.fixture()
def accounts(db_session):
    main = make_account(db_session)
    sortie = tx(db_session, main, "Sortie", 90.0, datetime(2026, 9, 28), "RESTO")
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3), "VIR DENIS")
    return sortie, entree


def _claim(client, tx_id, amount, headers=None):
    return client.post(
        "/reimbursements/claims",
        json={"transaction_id": tx_id, "debtor": "Denis", "expected_amount": amount},
        headers=headers or {},
    )


def test_refusals_in_english(client, accounts):
    sortie, entree = accounts
    assert _claim(client, entree.id, 5, EN).json()["detail"] == "A claim can only be placed on an expense (Sortie)"
    assert _claim(client, sortie.id, 100, EN).json()["detail"] == "The total of the claims exceeds the expense amount"


def test_refusals_stay_french_without_header(client, accounts):
    _, entree = accounts
    assert _claim(client, entree.id, 5).json()["detail"] == "Une créance ne peut porter que sur une dépense (Sortie)"


def test_not_found_in_english(client):
    res = client.get("/reimbursements/claims/9999/candidates", headers=EN)
    assert res.status_code == 404 and res.json()["detail"] == "Claim not found"


def test_allocation_refusals_in_english(client, accounts):
    sortie, entree = accounts
    claim_id = _claim(client, sortie.id, 20).json()["id"]
    res = client.post(f"/reimbursements/claims/{claim_id}/allocations", json={"entree_id": sortie.id}, headers=EN)
    assert res.json()["detail"] == "Only an income (Entree) can repay a claim"
    res = client.post(
        f"/reimbursements/claims/{claim_id}/allocations", json={"entree_id": entree.id, "amount": 25}, headers=EN
    )
    assert res.json()["detail"] == "The amount exceeds the remaining balance of the claim"
