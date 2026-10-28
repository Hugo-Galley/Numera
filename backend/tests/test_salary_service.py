"""Salaire : caractérisation de bout en bout (écrite avant le découpage) et règles pures."""
from datetime import date

from app.domain.salary import hourly_rate, salary_amount
from app.models.transaction import Transaction


def _setup(client):
    account_id = client.post("/accounts", json={"name": "Courant", "type": "courant", "currency": "EUR"}).json()["id"]
    response = client.post("/salary/config", json={"salary_account_id": account_id, "net_salary": 2500.0,
                                                  "ticket_employee_share": 4.5})
    assert response.status_code == 200, response.text
    assert client.put("/salary/months/2026/9", json={"salary_date": "2026-09-25"}).status_code == 200
    return account_id


def _salaries(db_session):
    db_session.expire_all()
    return db_session.query(Transaction).filter(Transaction.merchant == "Salaire").all()


def test_regenerating_salary_month_keeps_single_salary(client, db_session):
    _setup(client)
    assert client.post("/salary/generate/2026/9").json() == {"status": "ok"}
    again = client.post("/salary/generate/2026/9")
    assert again.status_code == 400 and again.json() == {"detail": "Already generated for this month"}
    [salary] = _salaries(db_session)
    assert salary.amount == 2500.0 and salary.running_balance == 2500.0


def test_telecommuting_update_adjusts_generated_salary(client, db_session):
    _setup(client)
    client.post("/salary/generate/2026/9")
    days = ["2026-09-01", "2026-09-02", "2026-09-02"]
    assert client.put("/salary/telecommuting/2026/9", json={"dates": days}).json() == {"status": "ok"}
    [salary] = _salaries(db_session)
    assert salary.amount == 2491.0 and salary.running_balance == 2491.0
    summary = client.get("/salary/summary/2026/9").json()
    assert (summary["tt_days_count"], summary["real_salary"], summary["is_generated"]) == (2, 2491.0, True)


def test_telecommuting_validation_errors(client):
    _setup(client)
    weekend = client.put("/salary/telecommuting/2026/9", json={"dates": ["2026-09-05"]})
    assert weekend.status_code == 400 and weekend.json() == {"detail": "Date 2026-09-05 is a weekend"}
    other_month = client.put("/salary/telecommuting/2026/9", json={"dates": ["2026-10-01"]})
    assert other_month.status_code == 422 and other_month.json() == {"detail": "Date 2026-10-01 hors du mois 2026-09"}


def test_reset_generation_deletes_salary_and_allows_regeneration(client, db_session):
    _setup(client)
    client.post("/salary/generate/2026/9")
    assert client.delete("/salary/generate/2026/9").json() == {"status": "ok"}
    assert _salaries(db_session) == []
    assert client.post("/salary/generate/2026/9").json() == {"status": "ok"}
    assert len(_salaries(db_session)) == 1


def test_missing_config_is_404(client):
    response = client.get("/salary/config")
    assert response.status_code == 404 and response.json() == {"detail": "Salary config not found"}


def test_salary_amount_subtracts_telework_tickets():
    assert salary_amount(2500, 10, 4.5) == 2455.0


def test_hourly_rate():
    assert hourly_rate(2180.0, 218, 7.0) == round(2180 * 12 / (218 * 7), 2)
    assert hourly_rate(0.0, 218, 7.0) is None
    assert hourly_rate(2000.0, 0, 7.0) is None
