from datetime import datetime

import pytest

from app.core.finance import month_label_from_date
from app.core.month_review import differs
from app.models.account import Account
from app.models.category import Category
from app.models.month_closure import MonthClosure
from app.models.transaction import Transaction


def _tx(db, account, type_, amount, date, merchant="x", category=None, exceptional=False):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
        category_id=category.id if category else None, is_exceptional=exceptional,
    )
    db.add(t)
    db.commit()
    return t


def _courant(db, **kwargs):
    acc = Account(name="Principal", type="courant", currency="EUR", active=True, **kwargs)
    db.add(acc)
    db.commit()
    return acc


def test_monthly_report_exposes_figures_without_exceptional(client, db_session):
    acc = _courant(db_session)
    courses = Category(name="Courses", type="depense")
    db_session.add(courses)
    db_session.commit()
    _tx(db_session, acc, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 300.0, datetime(2025, 10, 8), "MARCHE", courses)
    _tx(db_session, acc, "Sortie", 200.0, datetime(2025, 10, 20), "CANAPE", courses, exceptional=True)

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2025}).json()

    assert report["real_expenses"] == 500.0
    assert report["exceptional_expenses"] == 200.0
    assert report["real_expenses_excl_exceptional"] == 300.0
    assert report["savings"] == 1500.0
    assert report["savings_excl_exceptional"] == 1700.0
    assert report["savings_rate"] == 75.0
    assert report["savings_rate_excl_exceptional"] == 85.0
    assert report["burn_rate_excl_exceptional"] == pytest.approx(300.0 / 31, abs=0.02)


def test_exceptional_investment_category_not_double_counted(client, db_session):
    acc = _courant(db_session)
    invest = Category(name="Investissement", type="depense")
    db_session.add(invest)
    db_session.commit()
    _tx(db_session, acc, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 500.0, datetime(2025, 10, 3), "PEA", invest, exceptional=True)
    _tx(db_session, acc, "Sortie", 100.0, datetime(2025, 10, 4), "BOULANGERIE")

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2025}).json()

    assert report["real_expenses"] == 100.0  # 600 de dépenses − 500 d'investissement
    assert report["exceptional_expenses"] == 0.0
    assert report["real_expenses_excl_exceptional"] == 100.0


def test_differs_tolerates_small_drift():
    assert differs(1000.0, 1002.0) is False  # 0,2 % : dérive de taux de change
    assert differs(1000.0, 1010.0) is True
    assert differs(0.0, 0.005) is False
    assert differs(0.0, 0.02) is True


PARAMS = {"year": 2025, "month": 10}


@pytest.fixture()
def october(db_session):
    acc = _courant(db_session, last_verified_at=datetime(2025, 10, 15))
    courses = Category(name="Courses", type="depense")
    db_session.add(courses)
    db_session.commit()
    _tx(db_session, acc, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 300.0, datetime(2025, 10, 8), "MARCHE", courses)
    nocat = _tx(db_session, acc, "Sortie", 80.0, datetime(2025, 10, 12), "NOCAT")
    exc = _tx(db_session, acc, "Sortie", 200.0, datetime(2025, 10, 20), "CANAPE", courses, exceptional=True)
    _tx(db_session, acc, "Sortie", 100.0, datetime(2025, 9, 10), "AUTREMOIS")  # autre mois, sans catégorie
    return acc, courses, nocat, exc


def test_review_step1_is_bounded_to_month(client, october):
    data = client.get("/month-review", params=PARAMS).json()
    assert data["categorize"]["count"] == 1
    assert [i["merchant"] for i in data["categorize"]["items"]] == ["NOCAT"]
    assert data["categorize"]["total"] == 80.0
    assert data["closed"] is False
    assert data["closure"] is None
    assert data["modified_since_close"] is False


def test_review_accounts_step_flags_stale_accounts(client, october):
    acc = october[0]
    data = client.get("/month-review", params=PARAMS).json()
    assert data["accounts"]["unverified_count"] == 1
    assert data["accounts"]["accounts"][0]["verified_since_month_end"] is False

    assert client.post(f"/accounts/{acc.id}/verify").status_code == 200
    data = client.get("/month-review", params=PARAMS).json()
    assert data["accounts"]["unverified_count"] == 0
    assert data["accounts"]["accounts"][0]["verified_since_month_end"] is True


def test_review_budget_shows_figures_without_exceptional(client, october):
    b = client.get("/month-review", params=PARAMS).json()["budget"]
    assert b["income"] == 2000.0
    assert b["real_expenses"] == 580.0
    assert b["exceptional_expenses"] == 200.0
    assert b["real_expenses_excl_exceptional"] == 380.0
    assert b["savings"] == 1420.0
    assert b["savings_excl_exceptional"] == 1620.0
    assert b["savings_rate_excl_exceptional"] == 81.0
    assert b["burn_rate_excl_exceptional"] == pytest.approx(380.0 / 31, abs=0.02)
    assert b["previous_real_expenses"] == 100.0
    assert [t["merchant"] for t in b["top_expenses"]] == ["MARCHE", "CANAPE", "NOCAT"]
    assert b["top_expenses"][1]["is_exceptional"] is True


def test_empty_month_returns_200(client, db_session):
    res = client.get("/month-review", params={"year": 2024, "month": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["categorize"]["count"] == 0
    assert data["budget"]["income"] == 0.0
    assert data["budget"]["top_expenses"] == []


def test_invalid_month_is_422(client):
    assert client.get("/month-review", params={"year": 2025, "month": 13}).status_code == 422


def _close(client, highlight=None, **period):
    return client.post("/month-review/close", json={**(period or PARAMS), "highlight": highlight})


def test_close_stores_snapshot(client, october):
    res = _close(client, "Canapé acheté")
    assert res.status_code == 200
    body = res.json()
    assert body["closed"] is True
    assert body["modified_since_close"] is False
    closure = body["closure"]
    assert closure["highlight"] == "Canapé acheté"
    assert closure["tx_count"] == 4
    assert closure["income"] == 2000.0
    assert closure["expenses"] == 580.0
    assert closure["unresolved_count"] == 2  # 1 dépense sans catégorie + 1 compte non vérifié


def test_close_twice_keeps_one_row(client, october, db_session):
    _close(client, "a")
    _close(client, "b")
    rows = db_session.query(MonthClosure).all()
    assert len(rows) == 1
    assert rows[0].highlight == "b"


def test_reopen_deletes_closure_and_is_idempotent(client, october):
    _close(client)
    assert client.delete("/month-review", params=PARAMS).status_code == 204
    assert client.get("/month-review", params=PARAMS).json()["closed"] is False
    assert client.delete("/month-review", params=PARAMS).status_code == 204


def test_modified_since_close_after_new_transaction(client, october, db_session):
    _close(client)
    _tx(db_session, october[0], "Sortie", 15.0, datetime(2025, 10, 25), "NEW")
    data = client.get("/month-review", params=PARAMS).json()
    assert data["closed"] is True
    assert data["modified_since_close"] is True


def test_recategorizing_does_not_flag_modification(client, october):
    _, courses, nocat, _ = october
    _close(client)
    client.patch(f"/transactions/{nocat.id}", json={"category_id": courses.id})
    data = client.get("/month-review", params=PARAMS).json()
    assert data["closed"] is True
    assert data["modified_since_close"] is False


def test_empty_month_can_be_closed(client, db_session):
    res = _close(client, year=2024, month=2)
    assert res.status_code == 200
    assert res.json()["closed"] is True
    assert res.json()["closure"]["tx_count"] == 0


def test_closures_list_most_recent_first(client, october):
    _close(client, year=2025, month=9)
    _close(client)
    closures = client.get("/month-review/closures").json()
    assert [(c["year"], c["month"]) for c in closures] == [(2025, 10), (2025, 9)]
