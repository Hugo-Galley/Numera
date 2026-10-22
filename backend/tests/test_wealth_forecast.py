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


def test_forecast_weighted_return_and_growth(client, db_session):
    _account_with_value(db_session, "Livret", "epargne", 5000)
    _account_with_value(db_session, "PEA", "investissement", 5000)

    data = client.get("/analytics/wealth-forecast", params={"years": 10}).json()

    assert data["current_wealth"] == 10000
    assert data["annual_return_pct"] == pytest.approx(4.75)
    assert data["final_base"] == pytest.approx(10000 * 1.0475 ** 10, rel=1e-3)
    assert data["points"][0]["base"] == 10000
    assert data["gain_from_extra"] == 0


def test_forecast_extra_monthly_adds_gain(client, db_session):
    _account_with_value(db_session, "Livret", "epargne", 1000)

    data = client.get("/analytics/wealth-forecast", params={"years": 5, "extra_monthly": 100}).json()

    assert data["final_boosted"] > data["final_base"]
    # 100 €/mois pendant 60 mois, plus les intérêts à 3 %
    assert data["gain_from_extra"] >= 6000
    assert data["points"][-1]["boosted"] == data["final_boosted"]


def test_forecast_uses_average_savings_of_completed_months(client, db_session):
    from app.core.finance import month_label_from_date
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
