from datetime import datetime, timedelta

import pytest

from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction


def _account(db, name, type_):
    acc = Account(name=name, type=type_, currency="EUR", active=True)
    db.add(acc)
    db.commit()
    return acc


def _tx(db, acc, type_, amount, date, merchant="X", category=None, balance=0.0, **extra):
    t = Transaction(
        account_id=acc.id, date=date, month_label=month_label_from_date(date), type=type_, merchant=merchant,
        amount=amount, original_amount=amount, currency="EUR", running_balance=balance,
        category_id=category.id if category else None, **extra,
    )
    db.add(t)
    db.commit()
    return t


def _month_start(months_ago: int) -> datetime:
    now = datetime.now()
    index = now.year * 12 + (now.month - 1) - months_ago
    return datetime(index // 12, index % 12 + 1, 1)


def _current_month_row(client):
    now = datetime.now()
    rows = client.get("/analytics/kpi-history", params={"months_count": 3}).json()
    return next(r for r in rows if r["month"] == now.month and r["year"] == now.year)


def test_kpi_history_ignores_internal_transfers_and_bounds_the_rate(client, db_session):
    """Les virements vers le Livret A comptaient comme revenus : taux d'épargne à 340 % sur la page Épargne."""
    courant = _account(db_session, "Courant", "courant")
    livret = _account(db_session, "Livret", "epargne")
    day = _month_start(0) + timedelta(hours=12)
    _tx(db_session, courant, "Entree", 2000.0, day, "SALAIRE")
    _tx(db_session, courant, "Sortie", 300.0, day, "COURSES")
    out = _tx(db_session, courant, "Sortie", 500.0, day, "VIR LIVRET", is_transfer=True)
    _tx(db_session, livret, "Entree", 500.0, day, "VIR COURANT", is_transfer=True, linked_transaction_id=out.id)

    row = _current_month_row(client)
    assert row["revenus"] == 2000.0
    assert row["depenses"] == 300.0
    assert row["taux_epargne"] == 85.0


def test_kpi_history_does_not_count_unfunded_versements_as_invested(client, db_session):
    """Un versement sans virement lié (rapatriement, solde initial) rendait les dépenses réelles négatives."""
    courant = _account(db_session, "Courant", "courant")
    pea = _account(db_session, "PEA", "investissement")
    day = _month_start(0) + timedelta(hours=12)
    _tx(db_session, courant, "Entree", 2000.0, day, "SALAIRE")
    _tx(db_session, courant, "Sortie", 300.0, day, "COURSES")
    db_session.add(InvestmentTransaction(account_id=pea.id, date=day, type="versement", amount=5000.0, currency="EUR", original_amount=5000.0))
    db_session.commit()

    row = _current_month_row(client)
    assert row["investissements"] == 0.0
    assert -100.0 <= row["taux_epargne"] <= 100.0
    assert row["taux_epargne"] == 85.0


def test_resilience_uses_complete_months_not_the_current_one(client, db_session):
    """47 mois d'autonomie en octobre : l'indice reposait sur les dépenses du mois en cours, incomplet."""
    courant = _account(db_session, "Courant", "courant")
    livret = _account(db_session, "Livret", "epargne")
    courses = Category(name="Courses", type="depense")
    db_session.add(courses)
    db_session.commit()
    _tx(db_session, livret, "Solde Initial", 6000.0, _month_start(5), "OUVERTURE", balance=6000.0)
    for months_ago in (1, 2, 3):
        _tx(db_session, courant, "Sortie", 1000.0, _month_start(months_ago) + timedelta(days=3), "LOYER", courses)
    _tx(db_session, courant, "Sortie", 10.0, _month_start(0), "CAFE", courses)  # mois en cours : ignoré

    now = datetime.now()
    data = client.get("/analytics/resilience", params={"month": now.month, "year": now.year}).json()
    assert data["avg_monthly_real_expenses"] == pytest.approx(1000.0)
    assert data["months_used"] == 3
    assert data["liquid_savings"] == pytest.approx(6000.0)
    assert data["months"] == pytest.approx(6.0)


def test_kpi_history_rate_ignores_a_versement_funded_the_previous_month(client, db_session):
    """Sortie le 29 du mois précédent, arrivée sur le PEA ce mois-ci : octobre affichait 100 % d'épargne."""
    from app.services.transfers import link_pair

    courant = _account(db_session, "Courant", "courant")
    pea = _account(db_session, "PEA", "investissement")
    invest = Category(name="Investissement", type="depense")
    db_session.add(invest)
    db_session.commit()
    day = _month_start(0) + timedelta(days=1)
    sortie = _tx(db_session, courant, "Sortie", 400.0, _month_start(0) - timedelta(days=2), "Alimentation PEA", invest)
    versement = InvestmentTransaction(account_id=pea.id, date=day, type="versement", amount=400.0, currency="EUR", original_amount=400.0)
    db_session.add(versement)
    db_session.commit()
    link_pair(db_session, sortie, versement, kind="investment", origin="manual")
    db_session.commit()
    _tx(db_session, courant, "Entree", 1000.0, day, "SALAIRE")
    _tx(db_session, courant, "Sortie", 300.0, day, "COURSES")

    row = _current_month_row(client)
    assert row["investissements"] == 400.0
    assert row["taux_epargne"] == 70.0  # (1000 − 300) / 1000, le versement n'est pas une « dépense négative »
