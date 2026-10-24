"""Lot 1 de l'audit (R1, R6, R7, B1, B3, B7, B12) : entrées invalides rejetées sans rien écrire."""
import pytest
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction


@pytest.fixture
def account(db_session: Session) -> Account:
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    return acc


def _tx(account_id: int, **over) -> dict:
    body = {
        "account_id": account_id,
        "date": "2026-03-10T10:00:00",
        "type": "Sortie",
        "merchant": "Test",
        "amount": 10.0,
    }
    body.update(over)
    return body


@pytest.mark.parametrize("amount", ["Infinity", "NaN", "1e308", "-5"])
def test_create_transaction_rejects_bad_amount(client, db_session, account, amount):
    # littéral JSON écrit à la main : `json=` refuserait Infinity/NaN
    body = (
        '{"account_id": %d, "date": "2026-03-10T10:00:00", "type": "Sortie", '
        '"merchant": "Test", "amount": %s}' % (account.id, amount)
    )
    r = client.post("/transactions", content=body, headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert db_session.query(Transaction).count() == 0


def test_update_transaction_rejects_negative_amount(client, db_session, account):
    r = client.post("/transactions", json=_tx(account.id))
    assert r.status_code in (200, 201)
    tx_id = r.json()["id"]
    r = client.patch(f"/transactions/{tx_id}", json={"amount": -50})
    assert r.status_code == 422
    db_session.expire_all()
    assert db_session.get(Transaction, tx_id).amount == 10.0
    assert client.get(f"/transactions?account_id={account.id}").status_code == 200


def test_update_transaction_rejects_empty_merchant(client, account):
    tx_id = client.post("/transactions", json=_tx(account.id)).json()["id"]
    assert client.patch(f"/transactions/{tx_id}", json={"merchant": ""}).status_code == 422


def test_transaction_date_out_of_range_rejected(client, db_session, account):
    r = client.post("/transactions", json=_tx(account.id, date="9999-12-31T00:00:00"))
    assert r.status_code == 422
    assert db_session.query(Transaction).count() == 0


def test_unknown_foreign_key_returns_422_not_500(client, db_session, account):
    r = client.post("/transactions", json=_tx(account.id, category_id=99999))
    assert r.status_code in (404, 422)
    db_session.rollback()  # la session de test est partagée avec l'application
    assert db_session.query(Transaction).count() == 0


def test_huge_path_id_returns_404_or_422(client):
    r = client.get("/accounts/9999999999999999999999")
    assert r.status_code in (404, 422)


def _rec(account_id: int, **over) -> dict:
    body = {
        "account_id": account_id,
        "name": "Netflix",
        "type": "Sortie",
        "amount": 12.0,
        "frequency": "monthly",
        "day_of_month": 5,
        "start_date": "2026-01-01T00:00:00",
    }
    body.update(over)
    return body


@pytest.mark.parametrize(
    "over",
    [
        {"frequency": "fortnightly"},
        {"type": "Foo"},
        {"day_of_month": 99},
        {"amount": 0},
        {"end_date": "2025-01-01T00:00:00"},
        {"excluded_months": [13, 0]},
    ],
)
def test_recurring_rejects_invalid_fields(client, db_session, account, over):
    r = client.post("/recurring-transactions/", json=_rec(account.id, **over))
    assert r.status_code == 422
    assert db_session.query(RecurringTransaction).count() == 0


def test_recurring_unknown_account_is_not_a_500(client):
    r = client.post("/recurring-transactions/", json=_rec(99999))
    assert r.status_code in (404, 422)


def test_recurring_valid_still_accepted(client, account):
    r = client.post("/recurring-transactions/", json=_rec(account.id, frequency="yearly"))
    assert r.status_code in (200, 201)


@pytest.mark.parametrize("bad", ["inf", "nan", "1e308", "1e15"])
def test_import_csv_rejects_non_finite_or_huge_amounts(client, db_session, account, bad):
    csv_content = "\n".join(
        [
            "Date;Mois;Type;Commercant;Categorie;Montant",
            f"03/01/2026 00:00;Janvier;Sortie;KFC;Nourriture;{bad}",
            "04/01/2026 00:00;Janvier;Sortie;Boulangerie;Nourriture;2,50",
        ]
    )
    files = {"file": ("import.csv", csv_content.encode("utf-8"), "text/csv")}
    r = client.post("/import/commit", data={"account_id": str(account.id), "create_missing_categories": "true"}, files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["imported"] == 1
    assert body["errors"] == 1
    db_session.expire_all()
    amounts = [t.amount for t in db_session.query(Transaction).all()]
    assert amounts == [2.5]
    assert client.get("/accounts").status_code == 200
