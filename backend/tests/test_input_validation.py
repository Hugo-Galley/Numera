"""Lot 1 de l'audit (R1, R6, R7, B1, B3, B7, B12) : entrées invalides rejetées sans rien écrire."""
from datetime import datetime

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


# --- R6 / R7 : paramètres invalides → 4xx, jamais 500 ---------------------------------------

def test_budget_unknown_account_is_404(client):
    assert client.get("/analytics/budget?account_id=9999&month=3&year=2026").status_code == 404
    assert client.get("/analytics/monthly-report?account_id=9999&month=3&year=2026").status_code == 404


@pytest.mark.parametrize("month", [0, 13])
def test_budget_alerts_rejects_invalid_month(client, month):
    assert client.get(f"/analytics/budget-alerts?year=2026&month={month}").status_code == 422


def test_import_binary_file_is_422(client, account):
    files = {"file": ("x.csv", b"\x00\x01\x02Date;Type\x00\xff\xfe", "text/csv")}
    r = client.post("/import/preview", data={"account_id": str(account.id)}, files=files)
    assert r.status_code == 422
    r = client.post("/import/commit", data={"account_id": str(account.id)}, files=files)
    assert r.status_code == 422


def test_import_oversize_file_is_413(client, account):
    big = b"Date;Type;Commercant;Categorie;Montant\n" + b"a" * (10 * 1024 * 1024 + 1)
    files = {"file": ("big.csv", big, "text/csv")}
    r = client.post("/import/preview", data={"account_id": str(account.id)}, files=files)
    assert r.status_code == 413


@pytest.mark.parametrize("size", ["-1", "0", "100000"])
def test_import_preview_sample_size_bounded(client, account, size):
    csv_bytes = b"Date;Mois;Type;Commercant;Categorie;Montant\n03/01/2026 00:00;Janvier;Sortie;KFC;Nourriture;5,00\n"
    files = {"file": ("x.csv", csv_bytes, "text/csv")}
    ok = client.post("/import/preview", data={"account_id": str(account.id), "sample_size": "20"}, files=files)
    assert ok.status_code == 200  # garde-fou : le fichier est valide, seule la taille d'échantillon change
    r = client.post("/import/preview", data={"account_id": str(account.id), "sample_size": size}, files=files)
    assert r.status_code == 422


def test_passkey_state_without_challenge_is_400(client):
    import jwt
    from app.core.config import settings

    state = jwt.encode({"purpose": "login"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    r = client.post("/auth/passkey/login/verify", json={"state": state, "credential": {}})
    assert r.status_code in (400, 422)


@pytest.mark.parametrize(
    "path,body",
    [("/accounts", {"name": None}), ("/categories", {"name": None})],
)
def test_patch_null_on_required_column_is_not_500(client, db_session, account, path, body):
    # Création d'une catégorie pour cibler un id valide
    cat = client.post("/categories", json={"name": "Test", "type": "Sortie"})
    target = account.id if path == "/accounts" else cat.json().get("id", 1)
    r = client.patch(f"{path}/{target}", json=body)
    assert r.status_code in (200, 400, 422)
    db_session.rollback()


# --- B15 : fuseaux ------------------------------------------------------------------------

def test_date_with_offset_is_converted_to_naive_utc(client, db_session, account):
    # 23:30 à UTC−5 le 28/02 = 04:30 UTC le 01/03 : le mois change, l'offset ne doit pas être ignoré
    r = client.post("/transactions", json=_tx(account.id, date="2026-02-28T23:30:00-05:00"))
    assert r.status_code in (200, 201)
    db_session.expire_all()
    tx = db_session.query(Transaction).one()
    assert tx.date == datetime(2026, 3, 1, 4, 30)


def test_naive_date_is_kept_as_is(client, db_session, account):
    client.post("/transactions", json=_tx(account.id, date="2026-02-28T23:30:00"))
    db_session.expire_all()
    assert db_session.query(Transaction).one().date == datetime(2026, 2, 28, 23, 30)


def test_update_date_with_offset_is_converted(client, db_session, account):
    tx_id = client.post("/transactions", json=_tx(account.id)).json()["id"]
    assert client.patch(f"/transactions/{tx_id}", json={"date": "2026-03-10T10:00:00+02:00"}).status_code == 200
    db_session.expire_all()
    assert db_session.get(Transaction, tx_id).date == datetime(2026, 3, 10, 8, 0)
