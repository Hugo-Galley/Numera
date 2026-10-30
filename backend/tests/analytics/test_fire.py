from datetime import datetime

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot


def _wealth(db, value):
    acc = Account(name="AV", type="assurance_vie", currency="EUR", active=True)
    db.add(acc)
    db.commit()
    db.add(BalanceSnapshot(account_id=acc.id, date=datetime.now(), current_value=value))
    db.commit()


def test_fire_target_and_progress_with_overrides(client, db_session):
    _wealth(db_session, 100_000.0)

    res = client.get("/analytics/fire", params={
        "annual_expenses": 24_000, "monthly_savings": 1_000, "return_pct": 2.0, "inflation_pct": 2.0,
    })

    assert res.status_code == 200
    body = res.json()
    assert body["target"] == 600_000.0  # 24 000 ÷ 4 %
    assert body["progress_pct"] == round(100_000 / 600_000 * 100, 1)
    assert body["real_return_pct"] == 0.0
    # Rendement réel nul : (600 000 − 100 000) ÷ 12 000 €/an ≈ 41,7 ans
    assert body["years_to_fi"] == 41.7
    scenarios = {s["label"]: s["years_to_fi"] for s in body["scenarios"]}
    assert scenarios["+500 €/mois"] < scenarios["Actuel"]
    assert scenarios["Dépenses −10 %"] < scenarios["Actuel"]


def test_fire_already_reached_and_unreachable(client, db_session):
    _wealth(db_session, 1_000_000.0)
    reached = client.get("/analytics/fire", params={"annual_expenses": 20_000, "monthly_savings": 0, "return_pct": 0, "inflation_pct": 0}).json()
    assert reached["years_to_fi"] == 0.0 and reached["progress_pct"] == 100.0

    never = client.get("/analytics/fire", params={"annual_expenses": 200_000, "monthly_savings": 0, "return_pct": 0, "inflation_pct": 0}).json()
    assert never["years_to_fi"] is None and never["fi_year"] is None
