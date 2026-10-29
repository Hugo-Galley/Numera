import asyncio
from datetime import date, datetime

import pytest

from app.domain.loans import add_months
from app.services.comptes.wealth import account_values
from app.models.account import Account
from app.models.loan import Loan, LoanPrepayment
from app.models.transaction import Transaction


def _start_months_ago(months: int) -> date:
    return add_months(date.today().replace(day=1), -months)


def _create(client, **overrides):
    payload = {
        "name": "Prêt immo",
        "institution": "BRED",
        "kind": "immobilier",
        "principal": 200_000,
        "annual_rate_pct": 3.6,
        "duration_months": 300,
        "start_date": _start_months_ago(12).isoformat(),
        "insurance_monthly": 20,
    }
    payload.update(overrides)
    response = client.post("/loans", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_loan_creates_credit_account(client, db_session):
    loan = _create(client)
    account = db_session.get(Account, loan["account_id"])
    assert account.type == "credit"
    assert account.name == "Prêt immo"
    stored = db_session.query(Loan).one()
    assert stored.account_id == account.id and stored.principal == 200_000
    assert loan["monthly_payment"] == pytest.approx(1012.01, abs=0.01)
    assert 0 < loan["remaining_principal"] < 200_000
    assert loan["total_interest"] > 0


def test_credit_type_cannot_be_created_through_accounts(client):
    assert client.post("/accounts", json={"name": "X", "type": "credit", "currency": "EUR"}).status_code == 422


def test_account_balance_is_negative_remaining(client):
    loan = _create(client)
    account = client.get(f"/accounts/{loan['account_id']}").json()
    assert account["balance"] == pytest.approx(-loan["remaining_principal"], abs=0.01)
    listed = next(a for a in client.get("/accounts").json() if a["id"] == loan["account_id"])
    assert listed["balance"] == pytest.approx(-loan["remaining_principal"], abs=0.01)


def test_wealth_counts_loan_negatively(client, db_session):
    checking = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(checking)
    db_session.commit()
    db_session.add(Transaction(
        account_id=checking.id, date=datetime(2025, 1, 1), type="Solde Initial", amount=10_000,
        merchant="Solde", running_balance=10_000, month_label="Janvier 2025", original_amount=10_000,
    ))
    db_session.commit()
    loan = _create(client)

    values = asyncio.run(account_values(db_session, db_session.query(Account).all()))
    assert values[loan["account_id"]].value_eur == pytest.approx(-loan["remaining_principal"], abs=0.01)
    assert values[loan["account_id"]].source == "loan"

    allocation = client.get("/analytics/patrimoine-allocation").json()
    assert allocation["total_debts_eur"] == pytest.approx(loan["remaining_principal"], abs=0.01)
    assert allocation["net_patrimoine_eur"] == pytest.approx(10_000 - loan["remaining_principal"], abs=0.01)
    assert allocation["total_patrimoine"] == pytest.approx(10_000, abs=0.01)
    assert all(item["type"] != "credit" for item in allocation["items"])


def test_schedule_and_simulation_endpoints(client):
    loan = _create(client)
    schedule = client.get(f"/loans/{loan['id']}/schedule").json()
    assert len(schedule) == 300
    assert schedule[-1]["remaining"] == 0
    sim = client.post(
        f"/loans/{loan['id']}/simulate-prepayment",
        json={"amount": 20_000, "date": date.today().isoformat(), "mode": "reduce_duration"},
    ).json()
    assert sim["interest_saved"] > 0
    assert sim["months_saved"] > 0


def test_prepayment_persists_and_changes_summary(client, db_session):
    loan = _create(client)
    response = client.post(
        f"/loans/{loan['id']}/prepayments",
        json={"amount": 10_000, "date": date.today().isoformat(), "mode": "reduce_duration"},
    )
    assert response.status_code == 201
    assert db_session.query(LoanPrepayment).count() == 1
    after = client.get(f"/loans/{loan['id']}").json()
    assert after["remaining_principal"] == pytest.approx(loan["remaining_principal"] - 10_000, abs=0.01)
    assert len(after["prepayments"]) == 1

    pp_id = after["prepayments"][0]["id"]
    assert client.delete(f"/loans/{loan['id']}/prepayments/{pp_id}").status_code == 204
    assert db_session.query(LoanPrepayment).count() == 0


def test_update_loan_terms(client, db_session):
    loan = _create(client)
    response = client.patch(f"/loans/{loan['id']}", json={"annual_rate_pct": 2.0, "name": "Prêt maison"})
    assert response.status_code == 200
    assert response.json()["monthly_payment"] < loan["monthly_payment"]
    assert db_session.get(Account, loan["account_id"]).name == "Prêt maison"


def test_delete_loan_deletes_account(client, db_session):
    loan = _create(client)
    client.post(f"/loans/{loan['id']}/prepayments", json={"amount": 1_000, "date": date.today().isoformat(), "mode": "reduce_duration"})
    assert client.delete(f"/loans/{loan['id']}").status_code == 204
    assert db_session.query(Loan).count() == 0
    assert db_session.query(LoanPrepayment).count() == 0
    assert db_session.get(Account, loan["account_id"]) is None


def test_loan_by_account_and_list(client):
    loan = _create(client)
    assert client.get(f"/loans/by-account/{loan['account_id']}").json()["id"] == loan["id"]
    assert [l["id"] for l in client.get("/loans").json()] == [loan["id"]]
    assert client.get("/loans/by-account/999").status_code == 404


def test_invalid_loan_rejected(client):
    assert client.post("/loans", json={
        "name": "X", "kind": "auto", "principal": 0, "annual_rate_pct": 3, "duration_months": 12,
        "start_date": "2025-01-01",
    }).status_code == 422
    assert client.post("/loans", json={
        "name": "X", "kind": "auto", "principal": 1000, "annual_rate_pct": 3, "duration_months": 0,
        "start_date": "2025-01-01",
    }).status_code == 422


def test_no_debt_before_disbursement(client, db_session):
    """Les mois d'avant le crédit ne portent aucune dette (le CRD complet n'existe qu'à partir du déblocage)."""
    loan = _create(client, start_date="2026-06-05")
    account = db_session.get(Account, loan["account_id"])
    before = asyncio.run(account_values(db_session, [account], datetime(2025, 12, 31)))
    assert before[account.id].value_eur == 0
    disbursed = asyncio.run(account_values(db_session, [account], datetime(2026, 5, 10)))
    assert disbursed[account.id].value_eur == pytest.approx(-200_000)
