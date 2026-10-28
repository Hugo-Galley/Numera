"""Lot 4 de l'audit : champs de transaction persistés (B6), clés étrangères (B7), marchands (B8, U6)."""
from datetime import datetime

import pytest

from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.merchant import Merchant
from app.models.transaction import Transaction


@pytest.fixture
def account(db_session):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    return acc


def _payload(account_id, **over):
    body = {"account_id": account_id, "date": "2026-03-10T10:00:00", "type": "Sortie", "merchant": "KFC", "amount": 10.0}
    body.update(over)
    return body


def _db_tx(db, account, merchant="KFC", **kw):
    when = kw.pop("when", datetime(2026, 3, 10))
    tx = Transaction(
        account_id=account.id, date=when, month_label=month_label_from_date(when), type=kw.pop("type", "Sortie"),
        merchant=merchant, amount=10.0, original_amount=10.0, currency="EUR", running_balance=0.0, **kw,
    )
    db.add(tx)
    return tx


# --- B6 -----------------------------------------------------------------------------------

def test_create_transaction_persists_optional_fields(client, db_session, account):
    merchant = Merchant(name="KFC officiel")
    db_session.add(merchant)
    db_session.commit()
    r = client.post(
        "/transactions",
        json=_payload(account.id, merchant_id=merchant.id, is_recurring=True, custom_icon="Utensils", custom_color="#ff0000"),
    )
    assert r.status_code in (200, 201)
    db_session.expire_all()
    tx = db_session.query(Transaction).one()
    assert tx.merchant_id == merchant.id
    assert tx.is_recurring is True
    assert (tx.custom_icon, tx.custom_color) == ("Utensils", "#ff0000")


def test_bulk_update_sets_merchant_id(client, db_session, account):
    merchant = Merchant(name="KFC officiel")
    db_session.add(merchant)
    t1, t2 = _db_tx(db_session, account), _db_tx(db_session, account)
    db_session.commit()
    r = client.patch("/transactions/bulk", json={"ids": [t1.id, t2.id], "merchant_id": merchant.id})
    assert r.status_code == 204
    db_session.expire_all()
    assert {t.merchant_id for t in db_session.query(Transaction).all()} == {merchant.id}


# --- B7 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("field", ["category_id", "merchant_id"])
def test_create_transaction_unknown_reference_is_4xx(client, db_session, account, field):
    r = client.post("/transactions", json=_payload(account.id, **{field: 99999}))
    assert r.status_code in (404, 422)
    db_session.rollback()
    assert db_session.query(Transaction).count() == 0


@pytest.mark.parametrize("field", ["category_id", "merchant_id"])
def test_bulk_update_unknown_reference_is_4xx(client, db_session, account, field):
    tx = _db_tx(db_session, account)
    db_session.commit()
    r = client.patch("/transactions/bulk", json={"ids": [tx.id], field: 99999})
    assert r.status_code in (404, 422)


@pytest.mark.parametrize("extra", [{"account_id": 99999}, {"category_id": 99999}])
def test_create_goal_unknown_reference_is_4xx(client, db_session, account, extra):
    body = {"name": "Vacances", "target_amount": 1000.0, "account_id": account.id}
    body.update(extra)
    r = client.post("/goals", json=body)
    assert r.status_code in (404, 422), r.text


# --- B8 -----------------------------------------------------------------------------------

def test_merchant_name_must_not_be_empty(client):
    assert client.post("/merchants", json={"name": "   "}).status_code == 422


def test_duplicate_aliases_are_rejected_not_500(client, db_session):
    assert client.post("/merchants", json={"name": "A", "aliases": ["x", "x"]}).status_code in (400, 409, 422)
    assert client.post("/merchants", json={"name": "B", "aliases": ["same"]}).status_code == 201
    assert client.post("/merchants", json={"name": "C", "aliases": ["same"]}).status_code in (400, 409, 422)
    db_session.rollback()
    assert db_session.query(Merchant).filter_by(name="C").count() == 0


def test_rename_merchant_to_existing_name_is_conflict(client):
    client.post("/merchants", json={"name": "Alpha"})
    beta = client.post("/merchants", json={"name": "Beta"}).json()
    r = client.put(f"/merchants/{beta['id']}", json={"name": "Alpha"})
    assert r.status_code in (400, 409, 422)


def test_merchant_list_is_not_silently_truncated(client, db_session):
    db_session.add_all([Merchant(name=f"M{i:03d}") for i in range(120)])
    db_session.commit()
    assert len(client.get("/merchants").json()) == 120


def test_recurring_list_is_not_silently_truncated(client, db_session, account):
    from app.models.recurring_transaction import RecurringTransaction

    db_session.add_all([
        RecurringTransaction(account_id=account.id, name=f"R{i}", type="Sortie", amount=1.0, currency="EUR",
                             frequency="monthly", day_of_month=5, start_date=datetime(2026, 1, 1))
        for i in range(120)
    ])
    db_session.commit()
    assert len(client.get("/recurring-transactions/").json()) == 120


# --- U6 -----------------------------------------------------------------------------------

def test_creating_a_merchant_links_matching_transactions_immediately(client, db_session, account):
    t_match = _db_tx(db_session, account, merchant="CB KFC PARIS")
    t_other = _db_tx(db_session, account, merchant="Autre")
    db_session.commit()
    r = client.post("/merchants", json={"name": "KFC", "aliases": ["CB KFC PARIS"]})
    assert r.status_code == 201
    db_session.expire_all()
    assert db_session.get(Transaction, t_match.id).merchant_id == r.json()["id"]
    assert db_session.get(Transaction, t_other.id).merchant_id is None


def test_adding_an_alias_links_matching_transactions(client, db_session, account):
    merchant_id = client.post("/merchants", json={"name": "KFC"}).json()["id"]
    tx = _db_tx(db_session, account, merchant="KFC 0042")
    db_session.commit()
    assert client.post(f"/merchants/{merchant_id}/aliases", json={"label": "KFC 0042"}).status_code == 200
    db_session.expire_all()
    assert db_session.get(Transaction, tx.id).merchant_id == merchant_id


def test_merchant_suggestions_ignore_internal_flows(client, db_session, account):
    invest = Category(name="Investissement", type="depense")
    db_session.add(invest)
    db_session.commit()
    for _ in range(5):
        _db_tx(db_session, account, merchant="Alimentation PEA", category_id=invest.id)
        _db_tx(db_session, account, merchant="Virement livret", is_transfer=True)
        _db_tx(db_session, account, merchant="Carrefour")
    db_session.commit()
    labels = {s["label"] for s in client.get("/merchants/suggestions/unnormalized").json()}
    assert labels == {"Carrefour"}
