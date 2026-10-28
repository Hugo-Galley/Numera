"""Audit B2 : règles de catégorisation validées et apply-all sans effets destructeurs."""
from datetime import datetime

import pytest

from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.categorization_rule import CategorizationRule
from app.models.category import Category
from app.models.transaction import Transaction


def _tx(db, account, tx_type, merchant, amount=10.0, **kw):
    when = kw.pop("when", datetime(2026, 3, 10))
    tx = Transaction(
        account_id=account.id, date=when, month_label=month_label_from_date(when), type=tx_type,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0, **kw,
    )
    db.add(tx)
    return tx


@pytest.fixture
def account(db_session):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    return acc


@pytest.mark.parametrize("bad", ["foo", "Solde Initial", ""])
def test_rule_rejects_invalid_transaction_type(client, db_session, bad):
    r = client.post("/categorization-rules/", json={"pattern": "kfc", "transaction_type": bad})
    assert r.status_code == 422
    assert db_session.query(CategorizationRule).count() == 0


@pytest.mark.parametrize("pattern", ["", "   "])
def test_rule_rejects_empty_pattern(client, db_session, pattern):
    assert client.post("/categorization-rules/", json={"pattern": pattern}).status_code == 422
    assert db_session.query(CategorizationRule).count() == 0


def test_rule_type_is_normalized(client, db_session):
    r = client.post("/categorization-rules/", json={"pattern": "kfc", "transaction_type": "entrée"})
    assert r.status_code == 201
    assert r.json()["transaction_type"] == "Entree"


def test_patch_rule_validates_type_and_pattern(client, db_session):
    rule_id = client.post("/categorization-rules/", json={"pattern": "kfc"}).json()["id"]
    assert client.patch(f"/categorization-rules/{rule_id}", json={"transaction_type": "foo"}).status_code == 422
    assert client.patch(f"/categorization-rules/{rule_id}", json={"pattern": ""}).status_code == 422


def test_apply_all_never_touches_initial_balance_or_transfers(client, db_session, account):
    cat = Category(name="Divers", type="depense")
    db_session.add(cat)
    db_session.commit()
    initial = _tx(db_session, account, "Solde Initial", "Solde initial", 1000.0)
    transfer = _tx(db_session, account, "Sortie", "Virement initial livret", 200.0, is_transfer=True)
    db_session.add(CategorizationRule(pattern="init", category_id=cat.id, transaction_type="Sortie"))
    db_session.commit()

    r = client.post("/categorization-rules/apply-all")
    assert r.status_code == 200
    db_session.refresh(initial)
    db_session.refresh(transfer)
    assert initial.type == "Solde Initial" and initial.category_id is None
    assert transfer.category_id is None


def test_apply_all_keeps_categories_already_set(client, db_session, account):
    food = Category(name="Courses", type="depense")
    other = Category(name="Divers", type="depense")
    db_session.add_all([food, other])
    db_session.commit()
    kept = _tx(db_session, account, "Sortie", "Carrefour", category_id=food.id)
    empty = _tx(db_session, account, "Sortie", "Carrefour Express")
    db_session.add(CategorizationRule(pattern="carrefour", category_id=other.id))
    db_session.commit()

    assert client.post("/categorization-rules/apply-all").json()["modified_count"] == 1
    db_session.refresh(kept)
    db_session.refresh(empty)
    assert kept.category_id == food.id
    assert empty.category_id == other.id
