"""N+1 de la valorisation (audit A10) : /tax/overview, Centre d'Actions, créances, provisions."""
from datetime import date, datetime, timedelta

from app.models.account import Account
from app.models.category import Category
from app.models.provision import Provision
from app.models.reimbursement import ReimbursementAllocation, ReimbursementClaim
from app.models.transaction import Transaction

NOW = datetime.now()


def _tx(account_id: int, when: datetime, kind: str, amount: float, balance: float = 0.0, category_id=None) -> Transaction:
    return Transaction(
        account_id=account_id, date=when, month_label=when.strftime("%Y-%m"), type=kind, merchant="M",
        amount=amount, original_amount=amount, currency="EUR", running_balance=balance, category_id=category_id,
    )


def _add_accounts(db, start: int, count: int) -> None:
    accounts = [Account(name=f"Compte {i}", type="courant", currency="EUR", active=True) for i in range(start, start + count)]
    db.add_all(accounts)
    db.flush()
    db.add_all([_tx(acc.id, NOW - timedelta(days=d + 1), "Entree", 10.0, balance=10.0 * (60 - d))
                for acc in accounts for d in range(60)])
    db.commit()


def test_tax_overview_queries_do_not_grow_with_accounts(client, db_session, measure_queries):
    _add_accounts(db_session, 0, 4)
    _, few = measure_queries(lambda: client.get("/tax/overview"))
    _add_accounts(db_session, 4, 20)  # 24 comptes, 1 440 lignes

    response, many = measure_queries(lambda: client.get("/tax/overview"))

    assert response.status_code == 200
    assert many - few <= 10, f"{few} requêtes à 4 comptes, {many} à 24 : une par compte"


def test_actions_unmatched_transfers_use_constant_queries(client, db_session, measure_queries):
    a = Account(name="Courant", type="courant", currency="EUR", active=True)
    b = Account(name="Livret", type="epargne", currency="EUR", active=True)
    db_session.add_all([a, b])
    db_session.flush()
    rows = []
    for i in range(100):
        day = NOW - timedelta(days=3 + i // 2)
        rows.append(_tx(a.id, day, "Sortie", 100.0 + i))
        rows.append(_tx(b.id, day + timedelta(days=1), "Entree", 100.0 + i))
    # bruit pour dépasser 1 000 lignes
    rows.extend(_tx(a.id, NOW - timedelta(days=200 + i % 100), "Entree", 5000.0 + i) for i in range(1000))
    db_session.add_all(rows)
    db_session.commit()

    response, queries = measure_queries(lambda: client.get("/analytics/actions"))

    assert response.status_code == 200
    item = next(i for i in response.json()["actions"] if i["id"] == "possible-transfers")
    assert "100 virements" in item["description"]
    assert queries < 60, f"{queries} requêtes SQL : une par sortie"


def test_list_claims_queries_do_not_grow_with_claims(client, db_session, measure_queries):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.flush()
    sorties, entrees = [], []
    for i in range(60):
        sorties.append(_tx(acc.id, NOW - timedelta(days=i + 1), "Sortie", 50.0))
        entrees.append(_tx(acc.id, NOW - timedelta(days=i), "Entree", 20.0))
    db_session.add_all(sorties + entrees)
    db_session.add_all([_tx(acc.id, NOW - timedelta(days=300 + i % 50), "Entree", 1.0 + i) for i in range(1000)])
    db_session.flush()
    for i in range(60):
        claim = ReimbursementClaim(transaction_id=sorties[i].id, debtor=f"D{i}", expected_amount=25.0)
        claim.allocations.append(ReimbursementAllocation(entree_transaction_id=entrees[i].id, amount=10.0))
        db_session.add(claim)
    db_session.commit()

    response, queries = measure_queries(lambda: client.get("/reimbursements/claims?status=all"))

    body = response.json()
    assert response.status_code == 200 and len(body) == 60
    assert body[0]["received"] == 10.0 and body[0]["remaining"] == 15.0
    assert body[0]["allocations"][0]["label"] == "M"
    assert queries < 15, f"{queries} requêtes SQL : plusieurs par créance"


def test_provisions_last_payment_uses_constant_queries(client, db_session, measure_queries):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.flush()
    cats = [Category(name=f"Cat {i}", type="depense") for i in range(30)]
    db_session.add_all(cats)
    db_session.flush()
    today = date.today()
    db_session.add_all([_tx(acc.id, datetime.combine(today - timedelta(days=20), datetime.min.time()), "Sortie", 100.0 + i, category_id=c.id)
                        for i, c in enumerate(cats)])
    db_session.add_all([_tx(acc.id, NOW - timedelta(days=400 + i % 100), "Entree", 1.0 + i) for i in range(1000)])
    db_session.add_all([Provision(name=f"P{i}", amount=1000.0, interval_months=12, due_date=today - timedelta(days=20), category_id=c.id)
                        for i, c in enumerate(cats)])
    db_session.commit()

    response, queries = measure_queries(lambda: client.get("/provisions"))

    assert response.status_code == 200
    assert all(p["last_payment"] is not None for p in response.json())
    assert queries < 15, f"{queries} requêtes SQL : une par provision"
