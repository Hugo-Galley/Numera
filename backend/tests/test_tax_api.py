"""Fiscalité : enveloppes, plafonds, dates clés, récap annuel du CTO."""
from datetime import date

import pytest


def _account(client, name="PEA", type_="investissement", **extra) -> dict:
    resp = client.post("/accounts", json={"name": name, "type": type_, "currency": "EUR", "color": None, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_account_keeps_tax_wrapper_and_opening_date(client):
    created = _account(client, tax_wrapper="pea", opened_at="2019-03-15")
    assert created["tax_wrapper"] == "pea"
    assert created["opened_at"] == "2019-03-15"

    resp = client.patch(f"/accounts/{created['id']}", json={"tax_wrapper": "cto", "opened_at": "2020-01-02"})
    assert resp.status_code == 200
    assert resp.json()["tax_wrapper"] == "cto"
    assert resp.json()["opened_at"] == "2020-01-02"

    cleared = client.patch(f"/accounts/{created['id']}", json={"tax_wrapper": None})
    assert cleared.json()["tax_wrapper"] is None
    assert cleared.json()["opened_at"] == "2020-01-02"


def test_account_rejects_unknown_wrapper(client):
    resp = client.post("/accounts", json={"name": "X", "type": "investissement", "currency": "EUR", "tax_wrapper": "lep"})
    assert resp.status_code == 422
