from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.salary_config import SalaryConfig
from app.models.system_setting import SystemSetting


def _salary(db: Session, net: float = 2180.0) -> None:
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db.add(account)
    db.commit()
    db.add(SalaryConfig(salary_account_id=account.id, net_salary=net))
    db.commit()


def test_without_salary_no_rate(client: TestClient):
    data = client.get("/salary/work-time").json()
    assert data["configured"] is False
    assert data["hourly_rate"] is None
    assert data["work_days_per_year"] == 218
    assert data["work_hours_per_day"] == 7.0


def test_rate_from_net_salary_and_worked_days(client: TestClient, db_session: Session):
    _salary(db_session)
    data = client.get("/salary/work-time").json()
    # 2180 × 12 / (218 × 7) = 17,14 €/h
    assert data["configured"] is True
    assert data["hourly_rate"] == 17.14
    assert data["hours_per_month"] == 127.2


def test_update_settings_persists_and_changes_rate(client: TestClient, db_session: Session):
    _salary(db_session)
    res = client.patch("/salary/work-time", json={"work_days_per_year": 200, "work_hours_per_day": 8})
    assert res.status_code == 200
    assert res.json()["hourly_rate"] == round(2180 * 12 / 1600, 2)
    stored = {s.key: s.value for s in db_session.query(SystemSetting).all()}
    assert stored["work_days_per_year"] == "200"
    assert stored["work_hours_per_day"] == "8.0"


def test_invalid_settings_rejected(client: TestClient):
    assert client.patch("/salary/work-time", json={"work_hours_per_day": 0}).status_code == 422
    assert client.patch("/salary/work-time", json={"work_days_per_year": 400}).status_code == 422
