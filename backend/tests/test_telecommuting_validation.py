"""Audit B9 : jours de télétravail dédoublonnés, du bon mois, sans salaire négatif."""
from app.models.account import Account
from app.models.salary_config import SalaryConfig
from app.models.telecommuting_day import TelecommutingDay


def _config(db, net=2000.0, share=4.2):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db.add(acc)
    db.commit()
    cfg = SalaryConfig(salary_account_id=acc.id, net_salary=net, ticket_employee_share=share, is_active=True)
    db.add(cfg)
    db.commit()
    return cfg


def _days(db):
    return sorted(d.date.isoformat() for d in db.query(TelecommutingDay).all())


def test_duplicate_dates_count_once(client, db_session):
    _config(db_session)
    r = client.put("/salary/telecommuting/2026/3", json={"dates": ["2026-03-02", "2026-03-02", "2026-03-03"]})
    assert r.status_code == 200
    assert _days(db_session) == ["2026-03-02", "2026-03-03"]


def test_dates_outside_the_month_are_rejected_and_nothing_is_replaced(client, db_session):
    _config(db_session)
    assert client.put("/salary/telecommuting/2026/3", json={"dates": ["2026-03-02"]}).status_code == 200
    r = client.put("/salary/telecommuting/2026/3", json={"dates": ["2026-03-03", "2026-04-01"]})
    assert r.status_code == 422
    db_session.expire_all()
    assert _days(db_session) == ["2026-03-02"]  # l'état précédent est conservé


def test_weekend_rejected_without_losing_existing_days(client, db_session):
    _config(db_session)
    client.put("/salary/telecommuting/2026/3", json={"dates": ["2026-03-02"]})
    assert client.put("/salary/telecommuting/2026/3", json={"dates": ["2026-03-07"]}).status_code == 400
    db_session.expire_all()
    assert _days(db_session) == ["2026-03-02"]


def test_deduction_cannot_exceed_net_salary(client, db_session):
    _config(db_session, net=10.0, share=4.2)  # 3 jours × 4,20 > 10
    r = client.put(
        "/salary/telecommuting/2026/3", json={"dates": ["2026-03-02", "2026-03-03", "2026-03-04"]}
    )
    assert r.status_code == 422
    assert _days(db_session) == []
