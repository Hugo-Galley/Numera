from datetime import datetime

import pytest

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot


def _account_with_value(db, name, type_, value):
    acc = Account(name=name, type=type_, currency="EUR", active=True)
    db.add(acc)
    db.commit()
    db.add(BalanceSnapshot(account_id=acc.id, date=datetime.now(), current_value=value))
    db.commit()
    return acc


def test_forecast_empty_database(client):
    data = client.get("/analytics/wealth-forecast").json()
    assert data["current_wealth"] == 0
    assert data["final_base"] == 0
    assert len(data["points"]) == 11


def test_forecast_manual_rates_and_growth(client, db_session):
    _account_with_value(db_session, "Livret", "epargne", 5000)
    _account_with_value(db_session, "PEA", "investissement", 5000)

    data = client.get(
        "/analytics/wealth-forecast", params={"years": 10, "investment_return_pct": 6, "savings_return_pct": 2}
    ).json()

    assert data["current_wealth"] == 10000
    assert data["annual_return_pct"] == pytest.approx(4.0)
    assert data["final_base"] == pytest.approx(10000 * 1.04 ** 10, rel=1e-3)
    assert data["gain_from_extra"] == 0
    assert {i["type"]: i["source"] for i in data["return_breakdown"]} == {"investissement": "manual", "autres": "manual"}


def test_forecast_no_hardcoded_rate_without_history(client, db_session):
    _account_with_value(db_session, "PEA", "investissement", 5000)

    data = client.get("/analytics/wealth-forecast").json()

    assert data["annual_return_pct"] == 0
    assert data["observed_investment_return_pct"] is None
    assert data["return_breakdown"][0]["source"] == "none"


def test_forecast_extra_monthly_adds_gain(client, db_session):
    _account_with_value(db_session, "Livret", "epargne", 1000)

    data = client.get(
        "/analytics/wealth-forecast", params={"years": 5, "extra_monthly": 100, "savings_return_pct": 3}
    ).json()

    assert data["final_boosted"] > data["final_base"]
    # 100 €/mois pendant 60 mois, plus les intérêts à 3 %
    assert data["gain_from_extra"] >= 6000
    assert data["points"][-1]["boosted"] == data["final_boosted"]


def test_forecast_uses_average_savings_of_completed_months(client, db_session):
    from app.domain.finance import month_label_from_date
    from app.models.transaction import Transaction

    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    now = datetime.now()
    for back in (1, 2, 3):
        idx = now.year * 12 + (now.month - 1) - back
        d = datetime(idx // 12, idx % 12 + 1, 5)
        for t, amount in (("Entree", 2000.0), ("Sortie", 1500.0)):
            db_session.add(Transaction(
                account_id=acc.id, date=d, month_label=month_label_from_date(d), type=t,
                merchant="X", amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
            ))
    db_session.commit()

    data = client.get("/analytics/wealth-forecast").json()

    assert data["months_used"] == 3
    assert data["avg_monthly_savings"] == pytest.approx(500.0)


def test_forecast_overrides_and_breakdown(client, db_session):
    _account_with_value(db_session, "Livret", "epargne", 5000)
    _account_with_value(db_session, "PEA", "investissement", 5000)

    data = client.get(
        "/analytics/wealth-forecast",
        params={"years": 1, "monthly_savings": 1000, "investment_return_pct": 0, "savings_return_pct": 0},
    ).json()
    assert data["avg_monthly_savings"] == 1000
    assert data["savings_overridden"] is True
    assert data["annual_return_pct"] == 0
    assert data["final_base"] == pytest.approx(22000, abs=1)
    assert {i["type"]: i["balance"] for i in data["return_breakdown"]} == {"investissement": 5000, "autres": 5000}


def test_forecast_ignores_leading_months_without_expenses(client, db_session):
    """Les mois avant le début du suivi (seulement des intérêts) ne tirent pas la moyenne vers zéro."""
    from app.domain.finance import month_label_from_date
    from app.models.transaction import Transaction

    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    now = datetime.now()

    def add(back, type_, amount):
        idx = now.year * 12 + (now.month - 1) - back
        d = datetime(idx // 12, idx % 12 + 1, 5)
        db_session.add(Transaction(
            account_id=acc.id, date=d, month_label=month_label_from_date(d), type=type_,
            merchant="X", amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
        ))

    add(5, "Interets", 2.0)
    add(4, "Interets", 1.0)
    for back in (1, 2, 3):
        add(back, "Entree", 2000.0)
        add(back, "Sortie", 1500.0)
    db_session.commit()

    data = client.get("/analytics/wealth-forecast").json()

    assert data["months_used"] == 3
    assert data["avg_monthly_savings"] == pytest.approx(500.0)


def test_forecast_observed_return_only_applies_to_measured_accounts(client, db_session, monkeypatch):
    """Le XIRR mesuré sur les comptes à positions n'est pas étendu aux comptes suivis par relevé."""
    from types import SimpleNamespace

    from app.services.analytics import portfolio

    measured = _account_with_value(db_session, "CTO", "investissement", 2000)
    _account_with_value(db_session, "PEA", "investissement", 8000)
    _account_with_value(db_session, "Livret", "epargne", 10000)

    async def fake_overview(db):
        return SimpleNamespace(xirr_pct=20.0, accounts=[SimpleNamespace(account_id=measured.id)])

    monkeypatch.setattr(portfolio, "portfolio_overview", fake_overview)

    data = client.get("/analytics/wealth-forecast").json()

    breakdown = {i["type"]: (i["balance"], i["rate_pct"], i["source"]) for i in data["return_breakdown"]}
    assert breakdown == {
        "investissement": (2000, 20.0, "observed"),
        "investissement_non_mesure": (8000, 0.0, "none"),
        "autres": (10000, 0.0, "none"),
    }
    assert data["annual_return_pct"] == pytest.approx(2.0)

    manual = client.get("/analytics/wealth-forecast", params={"investment_return_pct": 5}).json()
    assert {i["type"]: i["balance"] for i in manual["return_breakdown"]} == {"investissement": 10000, "autres": 10000}
