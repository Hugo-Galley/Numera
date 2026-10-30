"""Mêmes montants partout : budget, flux d'argent (bilan du mois) et Sankey.

Scénario : salaire 2 000, courses 300, alimentation PEA catégorisée 400 (sortie classique),
et versement PEA de 500 alimenté par un virement interne lié (sortie `is_transfer`).
"""
from datetime import datetime

import pytest

from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction

DAY = datetime(2025, 10, 10)
PARAMS = {"month": 10, "year": 2025}


def _tx(db, acc, type_, amount, merchant, category=None, date=DAY, balance=0.0, **extra):
    t = Transaction(
        account_id=acc.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR",
        running_balance=balance, category_id=category.id if category else None, **extra,
    )
    db.add(t)
    db.commit()
    return t


@pytest.fixture
def scenario(db_session):
    courant = Account(name="Principal", type="courant", currency="EUR", active=True)
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    salaire = Category(name="Salaire", type="revenu")
    food = Category(name="Nourriture", type="depense", group="Vie Courante")
    invest = Category(name="Investissement", type="depense")
    db_session.add_all([courant, pea, salaire, food, invest])
    db_session.commit()

    _tx(db_session, courant, "Entree", 2000.0, "SALAIRE", salaire)
    _tx(db_session, courant, "Sortie", 300.0, "MARCHE", food)
    _tx(db_session, courant, "Sortie", 400.0, "Alimentation PEA", invest)
    versement = InvestmentTransaction(
        account_id=pea.id, date=DAY, type="versement", amount=500.0, original_amount=500.0, currency="EUR",
    )
    db_session.add(versement)
    db_session.commit()
    _tx(db_session, courant, "Sortie", 500.0, "Virement PEA", is_transfer=True, linked_investment_transaction_id=versement.id)
    return courant


def test_budget_exposes_saved_and_remaining_cash(client, scenario):
    data = client.get("/analytics/budget", params=PARAMS).json()

    assert data["depenses_reelles"] == 300.0
    assert data["investissements_du_mois"] == 900.0
    # Épargné = revenus − dépenses réelles (numérateur du taux d'épargne), dont ce qui reste en trésorerie
    assert data["epargne_realisee"] == 1700.0
    assert data["reste_tresorerie"] == 800.0
    assert data["taux_epargne"] == pytest.approx(85.0)


def test_money_flow_counts_linked_versements(client, scenario):
    flow = client.get("/analytics/money-flow", params=PARAMS).json()

    assert flow["investments"]["amount"] == 900.0
    assert flow["remainder"]["amount"] == 800.0
    assert {i["name"] for i in flow["top_investments"]} == {"Alimentation PEA", "PEA"}


def test_sankey_budget_node_is_balanced(client, scenario):
    data = client.get("/analytics/sankey", params=PARAMS).json()
    names = [n["name"] for n in data["nodes"]]
    budget = names.index("Budget")

    inflow = sum(link["value"] for link in data["links"] if link["target"] == budget)
    outflow = sum(link["value"] for link in data["links"] if link["source"] == budget)
    assert inflow == pytest.approx(2000.0)
    assert outflow == pytest.approx(inflow)

    out = {names[link["target"]]: link["value"] for link in data["links"] if link["source"] == budget}
    assert out["Investissements"] == 900.0
    assert out["Épargne"] == 800.0


def test_kpi_history_exposes_real_expenses(client, db_session):
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    invest = Category(name="Investissement", type="depense")
    db_session.add_all([courant, invest])
    db_session.commit()
    last_month = datetime.now().replace(day=1)
    idx = last_month.year * 12 + last_month.month - 2
    day = datetime(idx // 12, idx % 12 + 1, 5)
    _tx(db_session, courant, "Entree", 2000.0, "SALAIRE", date=day)
    _tx(db_session, courant, "Sortie", 300.0, "MARCHE", date=day)
    _tx(db_session, courant, "Sortie", 400.0, "Alimentation PEA", invest, date=day)

    rows = client.get("/analytics/kpi-history", params={"months_count": 3}).json()
    row = next(r for r in rows if r["month"] == day.month and r["year"] == day.year)

    assert row["depenses"] == 700.0
    assert row["depenses_reelles"] == 300.0
    assert row["epargne_flow"] == 1700.0


def test_monthly_net_worth_change_ignores_opening_balances(client, db_session):
    """Ouvrir un compte n'est pas un gain de patrimoine."""
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    livret = Account(name="Dépôt", type="epargne", currency="EUR", active=True)
    db_session.add_all([courant, livret])
    db_session.commit()
    _tx(db_session, courant, "Solde Initial", 1000.0, "Solde Initial", date=datetime(2025, 9, 1), balance=1000.0)
    _tx(db_session, livret, "Solde Initial", 3000.0, "Solde Initial", balance=3000.0)

    report = client.get("/analytics/monthly-report", params=PARAMS).json()

    assert report["net_worth_change"] == pytest.approx(0.0, abs=0.01)
