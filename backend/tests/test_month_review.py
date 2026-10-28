from datetime import datetime

import pytest

from app.core.finance import month_label_from_date
from app.core.month_review import without_exceptional
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


def test_monthly_report_top_categories_carry_previous_month_total(client, db_session):
    acc = _courant(db_session)
    courses = Category(name="Courses", type="depense")
    db_session.add(courses)
    db_session.commit()
    _tx(db_session, acc, "Sortie", 120.0, datetime(2025, 9, 12), "MARCHE", courses)
    _tx(db_session, acc, "Sortie", 300.0, datetime(2025, 10, 8), "MARCHE", courses)

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2025}).json()

    top = {c["name"]: c for c in report["top_categories"]}
    assert top["Courses"]["total"] == 300.0
    assert top["Courses"]["prev_total"] == 120.0


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


# --- Passe de correction après la revue finale ---


def test_create_transaction_keeps_exceptional_flag(client, db_session):
    acc = _courant(db_session)
    base = {"account_id": acc.id, "date": "2025-10-05T00:00:00", "merchant": "CANAPE", "amount": 300.0}

    res = client.post("/transactions", json={**base, "type": "Sortie", "is_exceptional": True})
    assert res.status_code in (200, 201)
    assert res.json()["is_exceptional"] is True

    res = client.post("/transactions", json={**base, "type": "Entree", "merchant": "VIR", "is_exceptional": True})
    assert res.json()["is_exceptional"] is False  # seul une Sortie peut être exceptionnelle


def test_capped_savings_rate_stays_exact_without_exceptional(client, db_session):
    acc = _courant(db_session)
    _tx(db_session, acc, "Entree", 1000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 1500.0, datetime(2025, 10, 5), "LOYER")
    _tx(db_session, acc, "Sortie", 1000.0, datetime(2025, 10, 6), "VOYAGE", exceptional=True)

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2025}).json()

    assert report["savings_rate"] == -100.0  # plafonné
    assert report["savings_rate_excl_exceptional"] == -50.0


def test_without_exceptional_account_scope_uses_remaining():
    budget = {
        "depenses_reelles": 700.0, "revenus_totaux": 1000.0, "taux_epargne": 25.0,
        "burn_rate": 10.0, "revenus_apres_depenses": 250.0,
    }
    scoped = without_exceptional(budget, 100.0, account_scope=True)
    assert scoped["savings_rate_excl_exceptional"] == 35.0  # (250 + 100) / 1000
    assert without_exceptional(budget, 100.0)["savings_rate_excl_exceptional"] == 40.0  # (1000 − 600) / 1000


def test_top_expenses_ignore_non_budget_accounts(client, db_session):
    cur = _courant(db_session)
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(pea)
    db_session.commit()
    _tx(db_session, cur, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, cur, "Sortie", 50.0, datetime(2025, 10, 2), "CAFE")
    _tx(db_session, pea, "Sortie", 900.0, datetime(2025, 10, 3), "FRAIS")

    top = client.get("/month-review", params=PARAMS).json()["budget"]["top_expenses"]

    assert [t["merchant"] for t in top] == ["CAFE"]


def test_small_correction_is_detected_as_modification(client, october):
    _, _, nocat, _ = october
    _close(client)
    client.patch(f"/transactions/{nocat.id}", json={"amount": 81.0})  # +1 € sur un mois à 580 €
    assert client.get("/month-review", params=PARAMS).json()["modified_since_close"] is True


def test_exchange_rate_drift_does_not_flag_modification(client, db_session, monkeypatch):
    import app.services.analytics.budget as budget_mod
    import app.api.month_review as router_mod

    eur = _courant(db_session)
    usd = Account(name="USD", type="courant", currency="USD", active=True)
    db_session.add(usd)
    db_session.commit()
    _tx(db_session, eur, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, eur, "Sortie", 1000.0, datetime(2025, 10, 5), "LOYER")
    _tx(db_session, usd, "Sortie", 500.0, datetime(2025, 10, 6), "SAAS")

    def fixed_rates(usd_rate):
        async def _rates(base="EUR"):
            return {"EUR": 1.0, "USD": usd_rate}
        return _rates

    for module in (budget_mod, router_mod):
        monkeypatch.setattr(module, "get_exchange_rates", fixed_rates(1.08))
    assert _close(client).json()["closed"] is True

    for module in (budget_mod, router_mod):
        monkeypatch.setattr(module, "get_exchange_rates", fixed_rates(1.12))
    assert client.get("/month-review", params=PARAMS).json()["modified_since_close"] is False


def test_savings_amount_matches_savings_rate_when_money_is_invested(client, db_session):
    """Septembre affichait 1 618 € d'épargne pour un taux de 77 % : l'investi était retiré du montant, pas du taux."""
    acc = _courant(db_session)
    courses = Category(name="Courses", type="depense")
    invest = Category(name="Investissement", type="depense")
    db_session.add_all([courses, invest])
    db_session.commit()
    _tx(db_session, acc, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 300.0, datetime(2025, 10, 8), "MARCHE", courses)
    _tx(db_session, acc, "Sortie", 500.0, datetime(2025, 10, 29), "Alimentation PEA", invest)

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2025}).json()
    assert report["expenses"] == 800.0
    assert report["real_expenses"] == 300.0
    assert report["savings"] == 1700.0
    assert report["savings_rate"] == pytest.approx(report["savings"] / report["income"] * 100)

    budget = client.get("/month-review", params={"month": 10, "year": 2025}).json()["budget"]
    assert budget["savings"] == 1700.0
    assert budget["savings_rate"] == pytest.approx(budget["savings"] / budget["income"] * 100)
