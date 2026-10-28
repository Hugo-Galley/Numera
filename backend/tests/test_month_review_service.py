"""Revue de mois : clôturer = marquer, jamais verrouiller (règle métier 10) ; rapprochement."""
from datetime import date


def _setup(client):
    account_id = client.post("/accounts", json={"name": "Courant", "type": "courant", "currency": "EUR"}).json()["id"]
    tx = client.post("/transactions", json={"account_id": account_id, "date": "2026-09-10T00:00:00", "type": "Sortie",
                                           "merchant": "Carrefour", "amount": 30.0, "currency": "EUR"}).json()
    return account_id, tx["id"]


def test_closed_month_stays_editable(client):
    _, tx_id = _setup(client)
    closed = client.post("/month-review/close", json={"year": 2026, "month": 9, "highlight": "  "}).json()
    assert closed["closed"] is True and closed["modified_since_close"] is False
    assert closed["closure"]["highlight"] is None
    assert client.patch(f"/transactions/{tx_id}", json={"amount": 45.0}).status_code == 200
    review = client.get("/month-review", params={"year": 2026, "month": 9}).json()
    assert review["modified_since_close"] is True
    assert [c["month"] for c in client.get("/month-review/closures").json()] == [9]
    assert client.delete("/month-review", params={"year": 2026, "month": 9}).status_code == 204
    assert client.get("/month-review", params={"year": 2026, "month": 9}).json()["closed"] is False


def test_reconcile_points_to_exact_amount_line(client):
    account_id, _ = _setup(client)
    result = client.post(f"/accounts/{account_id}/reconcile", json={"date": "2026-09-30", "bank_balance": 0.0}).json()
    assert result["gap"] == 30.0 and not result["matches"]
    assert result["hints"][0]["kind"] == "extra_or_missing"
