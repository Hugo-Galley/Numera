"""Import idempotent (règle 4) et libellé bancaire intact (règle 7), même quand les règles changent."""
from app.models.categorization_rule import CategorizationRule
from app.models.merchant import Merchant
from app.models.transaction import Transaction
from app.models.transaction_split import TransactionSplit

CSV = "\n".join([
    "Date;Type;Commercant;Categorie;Montant;Note",
    "05/01/2026;Sortie;CB AMAZON 123;;42,50;",
    "06/01/2026;Sortie;CB FNAC;;10;",
])


def _account(client):
    return client.post("/accounts", json={"name": "Courant", "type": "courant", "currency": "EUR"}).json()["id"]


def _post(client, account_id, csv=CSV):
    files = {"file": ("releve.csv", csv.encode("utf-8"), "text/csv")}
    return client.post("/import/commit", data={"account_id": str(account_id)}, files=files).json()


def test_reimport_after_merchant_rule_created_imports_nothing(client, db_session):
    account_id = _account(client)
    assert _post(client, account_id)["imported"] == 2
    db_session.add(CategorizationRule(pattern="amazon", merchant_name="Amazon"))
    db_session.commit()

    again = _post(client, account_id)

    assert (again["imported"], again["skipped"]) == (0, 2)
    assert db_session.query(Transaction).count() == 2


def test_reimport_after_type_rule_created_imports_nothing(client, db_session):
    account_id = _account(client)
    _post(client, account_id)
    db_session.add(CategorizationRule(pattern="fnac", transaction_type="Entree"))
    db_session.commit()

    assert _post(client, account_id)["imported"] == 0
    # même après que la règle a retypé la ligne importée en base
    client.post("/categorization-rules/apply-all")
    assert _post(client, account_id)["imported"] == 0
    assert db_session.query(Transaction).count() == 2


def test_import_with_rules_keeps_bank_label_and_links_canonical_merchant(client, db_session):
    account_id = _account(client)
    db_session.add(CategorizationRule(pattern="amazon", merchant_name="Amazon"))
    db_session.commit()

    assert _post(client, account_id)["imported"] == 2
    db_session.expire_all()

    tx = db_session.query(Transaction).filter(Transaction.merchant.like("%AMAZON%")).one()
    assert tx.merchant == "CB AMAZON 123"
    assert tx.merchant_obj.name == "Amazon"
    # ré-import avec la même règle : rien de nouveau, et un seul marchand « Amazon »
    assert _post(client, account_id)["imported"] == 0
    assert db_session.query(Merchant).filter(Merchant.name == "Amazon").count() == 1


def test_reimport_after_manual_rename_and_retype_imports_nothing(client, db_session):
    account_id = _account(client)
    _post(client, account_id)
    tx = db_session.query(Transaction).filter(Transaction.merchant == "CB AMAZON 123").one()
    assert client.patch(f"/transactions/{tx.id}", json={"merchant": "Amazon", "type": "Entree"}).status_code == 200

    assert _post(client, account_id)["imported"] == 0
    assert db_session.query(Transaction).count() == 2


def test_apply_all_keeps_bank_label_and_reuses_merchant(client, db_session):
    account_id = _account(client)
    _post(client, account_id)
    db_session.add(CategorizationRule(pattern="amazon", merchant_name="Amazon"))
    db_session.commit()

    assert client.post("/categorization-rules/apply-all").json()["modified_count"] == 1
    assert client.post("/categorization-rules/apply-all").json()["modified_count"] == 0
    db_session.expire_all()
    tx = db_session.query(Transaction).filter(Transaction.merchant == "CB AMAZON 123").one()
    assert tx.merchant_obj.name == "Amazon"
    assert db_session.query(Merchant).filter(Merchant.name == "Amazon").count() == 1


def test_apply_all_skips_type_change_on_split_expense(client, db_session):
    account_id = _account(client)
    _post(client, account_id)
    tx = db_session.query(Transaction).filter(Transaction.merchant == "CB FNAC").one()
    db_session.add_all([TransactionSplit(transaction_id=tx.id, amount=6, category_id=None),
                        TransactionSplit(transaction_id=tx.id, amount=4, category_id=None)])
    db_session.commit()
    db_session.add(CategorizationRule(pattern="fnac", transaction_type="Entree"))
    db_session.commit()

    client.post("/categorization-rules/apply-all")

    db_session.expire_all()
    tx = db_session.get(Transaction, tx.id)
    assert tx.type == "Sortie" and len(tx.splits) == 2
