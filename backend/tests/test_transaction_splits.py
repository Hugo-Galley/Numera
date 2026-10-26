from datetime import datetime

from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.transaction_split import TransactionSplit


def _setup(db):
    acc = Account(name="Principal", type="courant", currency="EUR", active=True)
    courses = Category(name="Courses", type="depense")
    maison = Category(name="Maison", type="depense")
    epargne = Category(name="Epargne", type="epargne")
    db.add_all([acc, courses, maison, epargne])
    db.commit()
    return acc, courses, maison, epargne


def _tx(db, account, type_, amount, date, merchant="CARREFOUR", category=None):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
        category_id=category.id if category else None,
    )
    db.add(t)
    db.commit()
    return t


def _split(client, tx_id, *parts):
    return client.put(
        f"/transactions/{tx_id}/splits",
        json={"items": [{"category_id": c.id, "amount": a} for c, a in parts]},
    )


def test_split_sets_parts_and_main_category(client, db_session):
    acc, courses, maison, _ = _setup(db_session)
    tx = _tx(db_session, acc, "Sortie", 85.0, datetime(2025, 10, 5), category=courses)

    res = _split(client, tx.id, (courses, 25.0), (maison, 60.0))

    assert res.status_code == 200
    body = res.json()
    assert [(s["category_id"], s["amount"]) for s in body["splits"]] == [(courses.id, 25.0), (maison.id, 60.0)]
    db_session.refresh(tx)
    assert tx.category_id == maison.id  # plus grosse part
    assert db_session.query(TransactionSplit).count() == 2


def test_split_sum_must_match_amount(client, db_session):
    acc, courses, maison, _ = _setup(db_session)
    tx = _tx(db_session, acc, "Sortie", 85.0, datetime(2025, 10, 5))

    res = _split(client, tx.id, (courses, 25.0), (maison, 50.0))

    assert res.status_code == 400
    assert db_session.query(TransactionSplit).count() == 0


def test_split_refuses_savings_category_and_income(client, db_session):
    acc, courses, _, epargne = _setup(db_session)
    sortie = _tx(db_session, acc, "Sortie", 100.0, datetime(2025, 10, 5))
    entree = _tx(db_session, acc, "Entree", 100.0, datetime(2025, 10, 6))

    assert _split(client, sortie.id, (courses, 40.0), (epargne, 60.0)).status_code == 400
    assert _split(client, entree.id, (courses, 40.0), (courses, 60.0)).status_code == 400


def test_expenses_by_category_and_budget_alerts_use_parts(client, db_session):
    acc, courses, maison, _ = _setup(db_session)
    courses.monthly_limit = 20.0
    db_session.commit()
    _tx(db_session, acc, "Entree", 1000.0, datetime(2025, 10, 1), merchant="SALAIRE")
    tx = _tx(db_session, acc, "Sortie", 85.0, datetime(2025, 10, 5), category=courses)
    _split(client, tx.id, (courses, 25.0), (maison, 60.0))
    params = {"month": 10, "year": 2025}

    by_cat = client.get("/analytics/expenses-by-category", params=params).json()
    totals = {item["category"]["name"]: item["total"] for item in by_cat["items"]}
    assert totals == {"Courses": 25.0, "Maison": 60.0}
    assert by_cat["total"] == 85.0

    budget = client.get("/analytics/budget", params=params).json()
    assert budget["depenses_totales"] == 85.0

    alerts = client.get("/analytics/budget-alerts", params=params).json()
    courses_alert = next(a for a in alerts if a["category_name"] == "Courses")
    assert courses_alert["monthly_spent"] == 25.0


def test_category_filter_lists_split_transaction(client, db_session):
    acc, courses, maison, _ = _setup(db_session)
    tx = _tx(db_session, acc, "Sortie", 85.0, datetime(2025, 10, 5), category=courses)
    _split(client, tx.id, (courses, 25.0), (maison, 60.0))

    res = client.get("/transactions", params={"category_id": courses.id})

    assert [t["id"] for t in res.json()] == [tx.id]


def test_amount_change_refused_and_category_change_clears_split(client, db_session):
    acc, courses, maison, _ = _setup(db_session)
    tx = _tx(db_session, acc, "Sortie", 85.0, datetime(2025, 10, 5), category=courses)
    _split(client, tx.id, (courses, 25.0), (maison, 60.0))

    assert client.patch(f"/transactions/{tx.id}", json={"amount": 90.0}).status_code == 400

    res = client.patch(f"/transactions/{tx.id}", json={"category_id": courses.id})
    assert res.status_code == 200
    assert res.json()["splits"] == []
    assert db_session.query(TransactionSplit).count() == 0


def test_empty_list_cancels_split_and_delete_cascades(client, db_session):
    acc, courses, maison, _ = _setup(db_session)
    tx = _tx(db_session, acc, "Sortie", 85.0, datetime(2025, 10, 5), category=courses)
    _split(client, tx.id, (courses, 25.0), (maison, 60.0))

    assert client.put(f"/transactions/{tx.id}/splits", json={"items": []}).json()["splits"] == []

    _split(client, tx.id, (courses, 25.0), (maison, 60.0))
    assert client.delete(f"/transactions/{tx.id}").status_code == 204
    assert db_session.query(TransactionSplit).count() == 0
