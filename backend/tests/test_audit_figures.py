"""Lot 2 de l'audit : un seul périmètre de « revenu » et de « patrimoine » dans tous les écrans.

Définitions (décidées avec l'utilisateur) :
- revenu = ce qui arrive sur un compte courant ; une entrée sur un autre compte (livret…) n'en est un que
  si sa catégorie est de type « revenu » (marquage explicite) ; les intérêts (type Interets) comptent aussi ;
- Solde Initial et virements internes ne sont jamais des revenus ni des dépenses ;
- patrimoine = tous les comptes actifs, quel que soit leur type (y compris l'ancien type « bank »).
"""
from datetime import datetime

import pytest

from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction

MARCH = datetime(2026, 3, 10)


def _tx(db, account, when, tx_type, amount, merchant, **kw):
    tx = Transaction(
        account_id=account.id, date=when, month_label=month_label_from_date(when), type=tx_type,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0, **kw,
    )
    db.add(tx)
    return tx


@pytest.fixture
def world(db_session):
    db = db_session
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    livret = Account(name="Livret A", type="epargne", currency="EUR", active=True)
    bank = Account(name="Vieux compte", type="bank", currency="EUR", active=True)
    revenu_cat = Category(name="Revenus supplementaires", type="revenu")
    food = Category(name="Courses", type="depense")
    db.add_all([courant, livret, bank, revenu_cat, food])
    db.commit()

    _tx(db, courant, datetime(2026, 3, 1), "Solde Initial", 1000.0, "Solde initial")
    _tx(db, courant, MARCH, "Entree", 2000.0, "Employeur")
    _tx(db, courant, MARCH, "Sortie", 300.0, "Carrefour", category_id=food.id)
    # virement interne : ni revenu ni dépense, des deux côtés
    _tx(db, courant, MARCH, "Sortie", 200.0, "Vers livret", is_transfer=True)
    _tx(db, livret, MARCH, "Entree", 200.0, "Depuis courant", is_transfer=True)
    # dépôt non lié sur le livret : pas un revenu
    _tx(db, livret, MARCH, "Entree", 500.0, "Depot espece")
    # entrée explicitement marquée revenu sur le livret
    _tx(db, livret, MARCH, "Entree", 40.0, "Prime", category_id=revenu_cat.id)
    _tx(db, livret, MARCH, "Interets", 2.0, "Interets")
    # compte « bank » : hors flux, mais dans le patrimoine
    _tx(db, bank, MARCH, "Entree", 500.0, "Entree bank")
    _tx(db, bank, MARCH, "Sortie", 500.0, "Sortie bank")
    db.commit()
    return {"courant": courant, "livret": livret, "bank": bank}


EXPECTED_INCOME = 2000.0 + 40.0 + 2.0


def test_budget_month_income_follows_definition(client, world):
    data = client.get("/analytics/budget", params={"month": 3, "year": 2026}).json()
    assert data["revenus_totaux"] == EXPECTED_INCOME
    assert data["depenses_totales"] == 300.0


def test_budget_all_time_never_counts_solde_initial(client, world):
    data = client.get("/analytics/budget").json()
    assert data["revenus_totaux"] == EXPECTED_INCOME


def test_budget_requires_month_and_year_together(client, world):
    assert client.get("/analytics/budget", params={"month": 3}).status_code == 422
    assert client.get("/analytics/budget", params={"year": 2026}).status_code == 422


def test_account_view_ignores_solde_initial(client, world):
    data = client.get("/analytics/budget", params={"month": 3, "year": 2026, "account_id": world["courant"].id}).json()
    assert data["revenus_totaux"] == 2000.0
    assert data["taux_epargne"] == round((2000.0 - 500.0) / 2000.0 * 100, 2) or data["taux_epargne"] < 100


def test_money_flow_income_matches_budget(client, world):
    flow = client.get("/analytics/money-flow", params={"month": 3, "year": 2026}).json()
    assert flow["income"] == EXPECTED_INCOME


def test_sankey_income_matches_budget_without_reliquat(client, world):
    data = client.get("/analytics/sankey", params={"month": 3, "year": 2026}).json()
    names = {n["name"] for n in data["nodes"]}
    assert "Reliquat / Ajustement" not in names
    inflow = sum(link["value"] for link in data["links"] if data["nodes"][link["target"]]["name"] == "Budget")
    assert round(inflow, 2) == EXPECTED_INCOME


def test_timeseries_matches_budget_and_skips_transfers(client, world):
    flows = client.get("/analytics/timeseries", params={"year": 2026}).json()["monthly_flows"]
    march = next(m for m in flows if m["month"] == 3)
    assert march["income"] == EXPECTED_INCOME
    assert march["expense"] == 300.0


def test_kpi_history_matches_budget(client, world):
    history = client.get("/analytics/kpi-history", params={"months_count": 24}).json()
    march = next(h for h in history if h["month"] == 3 and h["year"] == 2026)
    assert march["revenus"] == EXPECTED_INCOME
    assert march["depenses"] == 300.0


def test_expenses_by_category_total_matches_budget_with_uncategorized_bucket(client, db_session, world):
    _tx(db_session, world["courant"], MARCH, "Sortie", 30.0, "Inconnu")  # sans catégorie
    _tx(db_session, world["bank"], MARCH, "Sortie", 77.0, "Hors périmètre")  # compte hors flux
    db_session.commit()
    budget = client.get("/analytics/budget", params={"month": 3, "year": 2026}).json()
    data = client.get("/analytics/expenses-by-category", params={"month": 3, "year": 2026}).json()
    assert data["total"] == budget["depenses_totales"] == 330.0
    names = {item["category"]["name"] for item in data["items"]}
    assert "Sans catégorie" in names


def test_top_merchants_excludes_savings_and_out_of_scope_accounts(client, db_session, world):
    epargne = Category(name="Epargne", type="depense")
    db_session.add(epargne)
    db_session.commit()
    _tx(db_session, world["courant"], MARCH, "Sortie", 500.0, "VIR INST MOI", category_id=epargne.id)
    _tx(db_session, world["bank"], MARCH, "Sortie", 900.0, "Hors périmètre")
    db_session.commit()
    items = client.get("/analytics/top-merchants", params={"month": 3, "year": 2026, "limit": 50}).json()["items"]
    names = {i["merchant"] for i in items}
    assert names == {"Carrefour"}


def test_monthly_report_top_categories_exclude_investment_and_savings(client, db_session, world):
    invest = Category(name="Investissement", type="depense")
    db_session.add(invest)
    db_session.commit()
    _tx(db_session, world["courant"], MARCH, "Sortie", 512.0, "Versement PEA", category_id=invest.id)
    db_session.commit()
    report = client.get("/analytics/monthly-report", params={"month": 3, "year": 2026}).json()
    assert "Investissement" not in {c["name"] for c in report["top_categories"]}


# --- A9 : abonnements ---------------------------------------------------------------------

def _recurring(db, account, name, amount, frequency="monthly", **kw):
    from app.models.recurring_transaction import RecurringTransaction

    rd = RecurringTransaction(
        account_id=account.id, name=name, type="Sortie", amount=amount, currency=kw.pop("currency", "EUR"),
        frequency=frequency, day_of_month=5, start_date=datetime(2026, 1, 1), is_active=kw.pop("is_active", True),
        **kw,
    )
    db.add(rd)
    return rd


def test_subscription_totals_only_count_real_active_subscriptions(client, db_session, world):
    invest = Category(name="Investissement", type="depense")
    db_session.add(invest)
    db_session.commit()
    c = world["courant"]
    _recurring(db_session, c, "Netflix", 10.0)
    _recurring(db_session, c, "Assurance", 120.0, frequency="yearly")  # 10 €/mois
    _recurring(db_session, c, "Salle", 20.0, is_active=False)  # en pause
    _recurring(db_session, c, "Alimentation PEA", 400.0, category_id=invest.id)
    _recurring(db_session, c, "Vers livret", 150.0, transfer_to_account_id=world["livret"].id)
    db_session.commit()

    data = client.get("/analytics/subscriptions").json()
    assert data["total_monthly"] == 20.0
    assert data["total_annual"] == 240.0
    by_name = {s["name"]: s for s in data["subscriptions"]}
    assert by_name["Assurance"]["monthly_cost"] == 10.0
    assert by_name["Assurance"]["annual_cost"] == 120.0
    assert by_name["Salle"]["counts_in_total"] is False
    assert by_name["Alimentation PEA"]["counts_in_total"] is False
    assert by_name["Vers livret"]["counts_in_total"] is False


def test_subscription_costs_are_converted_to_eur(client, db_session, world, monkeypatch):
    async def fake_rates(base="EUR"):
        return {"EUR": 1.0, "USD": 1.08}

    monkeypatch.setattr("app.api.analytics.subscriptions.get_exchange_rates", fake_rates)
    usd = 1.08
    _recurring(db_session, world["courant"], "Service US", 10.8, currency="USD")
    db_session.commit()
    sub = next(s for s in client.get("/analytics/subscriptions").json()["subscriptions"] if s["name"] == "Service US")
    assert sub["monthly_cost"] == round(10.8 / usd, 2)
