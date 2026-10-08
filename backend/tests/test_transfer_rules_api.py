from datetime import datetime

from sqlalchemy.orm import Session

from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.transaction import Transaction


def two_accounts(db: Session):
    a = Account(name="Principal", type="courant", currency="EUR", active=True)
    b = Account(name="Livret A", type="epargne", currency="EUR", active=True)
    db.add_all([a, b])
    db.commit()
    return a, b


def add_tx(db, acc, type_, amount, date, merchant="x"):
    t = Transaction(account_id=acc.id, date=date, month_label=month_label_from_date(date), type=type_,
                    merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0)
    db.add(t)
    db.commit()
    return t


def test_rule_crud_and_validation(client, db_session: Session):
    a, b = two_accounts(db_session)
    r = client.post("/transfer-rules", json={"source_account_id": a.id, "dest_account_id": b.id, "pattern": "livret"})
    assert r.status_code == 201
    rid = r.json()["id"]
    assert r.json()["day_tolerance"] == 5 and r.json()["amount_tolerance_pct"] == 1.0

    assert client.post("/transfer-rules", json={"source_account_id": a.id, "dest_account_id": a.id}).status_code == 422
    assert client.post("/transfer-rules", json={"source_account_id": a.id, "dest_account_id": 999}).status_code == 404

    assert client.patch(f"/transfer-rules/{rid}", json={"is_active": False}).json()["is_active"] is False
    assert len(client.get("/transfer-rules").json()) == 1
    assert client.delete(f"/transfer-rules/{rid}").status_code == 204
    assert client.get("/transfer-rules").json() == []


def test_apply_dry_run_then_apply(client, db_session: Session):
    a, b = two_accounts(db_session)
    d = datetime(2024, 1, 5)
    s = add_tx(db_session, a, "Sortie", 200, d)
    add_tx(db_session, b, "Entree", 200, d)
    client.post("/transfer-rules", json={"source_account_id": a.id, "dest_account_id": b.id})

    preview = client.post("/transfer-rules/apply", params={"dry_run": True}).json()
    assert preview["count"] == 1 and preview["dry_run"] is True
    assert preview["pairs"][0]["sortie"]["id"] == s.id
    db_session.refresh(s)
    assert s.is_transfer is False

    done = client.post("/transfer-rules/apply").json()
    assert done["count"] == 1
    db_session.refresh(s)
    assert s.is_transfer is True and s.link_origin == "rule"


def test_new_transaction_triggers_auto_link(client, db_session: Session):
    a, b = two_accounts(db_session)
    client.post("/transfer-rules", json={"source_account_id": a.id, "dest_account_id": b.id})
    now = datetime.now().replace(microsecond=0)
    s = add_tx(db_session, a, "Sortie", 150, now)
    resp = client.post("/transactions", json={
        "account_id": b.id, "date": now.isoformat(), "type": "Entree", "merchant": "Virement", "amount": 150,
    })
    assert resp.status_code == 201
    db_session.refresh(s)
    assert s.is_transfer is True and s.link_origin == "rule"
    assert resp.json()["id"] == s.linked_transaction_id


def test_import_triggers_auto_link(client, db_session: Session):
    a, b = two_accounts(db_session)
    client.post("/transfer-rules", json={"source_account_id": a.id, "dest_account_id": b.id})
    now = datetime.now().replace(microsecond=0)
    s = add_tx(db_session, a, "Sortie", 80, now)
    csv = "\n".join([
        "Date;Mois;Type;Commercant;Categorie;Montant",
        f"{now.strftime('%d/%m/%Y %H:%M')};Mois;Entrée;Virement;Divers;80,00",
    ])
    resp = client.post(
        "/import/commit",
        data={"account_id": str(b.id), "create_missing_categories": "true"},
        files={"file": ("x.csv", csv.encode(), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["imported"] == 1
    db_session.refresh(s)
    assert s.is_transfer is True
